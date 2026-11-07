from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ucm.capabilities import invoke
from ucm.system import capability_registry
from ucm.pippi_global import HubRefusal
from ucm.pippi_installer import probe_installer
from ucm.pippi_packs import (MEMORY_VAULT_RELEASE_CONTRACT_SHA256,
    SEMCRYS_RELEASE_MANIFEST_SHA256, PackStore, build_install_plan,
    default_pack_inventory, explain_project_portability, pack_registry,
    transition_pack_inventory, validate_pack_inventory,
    verify_bundled_optional_pack_manifests)


ROOT = Path(__file__).resolve().parents[1]


class PippiPackTests(unittest.TestCase):
    def test_registry_separates_core_standards_and_optional_realizations(self):
        registry = pack_registry(); index = {row["pack_id"]: row for row in registry["packs"]}
        self.assertTrue(index["PIPPI_CORE"]["required"])
        self.assertTrue(index["UGK_STANDARDS"]["default_selected"])
        self.assertEqual(index["UGK_RUNTIME"]["distribution"], "EXTERNAL_BINDING")
        self.assertEqual(index["SEMCRYS_CORE"]["manifest_sha256"], SEMCRYS_RELEASE_MANIFEST_SHA256)
        self.assertEqual(index["MEMORY_VAULT_ADAPTER"]["manifest_sha256"],
                         MEMORY_VAULT_RELEASE_CONTRACT_SHA256)
        self.assertTrue(registry["downloads_require_explicit_user_authorization"])

    def test_recommended_profile_is_ready_and_transtemporal_profile_is_honestly_held(self):
        inventory = default_pack_inventory()
        recommended = build_install_plan(profile="RECOMMENDED_LOCAL", inventory=inventory)
        self.assertEqual(recommended["status"], "READY")
        self.assertFalse(recommended["plan_performs_effects"])
        temporal = build_install_plan(profile="TRANSTEMPORAL_PROJECT", inventory=inventory)
        self.assertEqual(temporal["status"], "HELD")
        self.assertIn("SEMCRYS_CORE", [row["pack_id"] for row in temporal["holds"]])
        self.assertIn("MEMORY_VAULT_ADAPTER", [row["pack_id"] for row in temporal["holds"]])

    def test_remote_download_selection_only_names_authorization_hold(self):
        plan = build_install_plan(profile="TRANSTEMPORAL_PROJECT",
            inventory=default_pack_inventory(), allow_remote_downloads=True)
        semcrys = next(row for row in plan["actions"] if row["pack_id"] == "SEMCRYS_CORE")
        self.assertEqual(semcrys["action"], "DOWNLOAD_REQUIRES_USER_AUTHORIZATION")
        self.assertFalse(plan["plan_performs_effects"])

    def test_offline_semcrys_does_not_launder_memory_vault_binding(self):
        plan = build_install_plan(profile="TRANSTEMPORAL_PROJECT",
            inventory=default_pack_inventory(), offline_artifact_roots=[SEMCRYS_RELEASE_MANIFEST_SHA256])
        semcrys = next(row for row in plan["actions"] if row["pack_id"] == "SEMCRYS_CORE")
        vault = next(row for row in plan["actions"] if row["pack_id"] == "MEMORY_VAULT_ADAPTER")
        self.assertEqual(semcrys["action"], "VERIFY_OFFLINE_ARTIFACT")
        self.assertEqual(vault["action"], "BIND_EXTERNAL")

    def test_inventory_transition_requires_verification_evidence(self):
        inventory = default_pack_inventory()
        with self.assertRaises(HubRefusal):
            transition_pack_inventory(inventory=inventory, pack_id="SEMCRYS_CORE",
                state="INSTALLED_UNBOUND", installed_root="1"*64, binding_root=None,
                evidence_roots=[])
        successor = transition_pack_inventory(inventory=inventory, pack_id="SEMCRYS_CORE",
            state="INSTALLED_UNBOUND", installed_root="1"*64, binding_root=None,
            evidence_roots=["2"*64])
        self.assertEqual(validate_pack_inventory(successor), successor)
        status = explain_project_portability(required_packs=["SEMCRYS_CORE"], inventory=successor)
        self.assertEqual(status["status"], "READY")
        vault = explain_project_portability(required_packs=["MEMORY_VAULT_ADAPTER"],
                                            inventory=successor)
        self.assertEqual(vault["status"], "NEEDS_PACKS")

    def test_installed_state_requires_an_exact_installed_root(self):
        inventory = default_pack_inventory()
        with self.assertRaises(HubRefusal):
            transition_pack_inventory(inventory=inventory, pack_id="SEMCRYS_CORE",
                state="INSTALLED_UNBOUND", installed_root=None, binding_root=None,
                evidence_roots=["2"*64])

    def test_pack_store_uses_exact_inventory_head(self):
        with tempfile.TemporaryDirectory() as raw:
            store = PackStore(Path(raw)); first = store.initialize()
            with self.assertRaises(HubRefusal):
                store.record(expected_inventory_root="0"*64, pack_id="SEMCRYS_CORE",
                    state="INSTALLED_UNBOUND", installed_root="1"*64,
                    binding_root=None, evidence_roots=["2"*64])
            second = store.record(expected_inventory_root=first["inventory_root"],
                pack_id="SEMCRYS_CORE", state="INSTALLED_UNBOUND", installed_root="1"*64,
                binding_root=None, evidence_roots=["2"*64])
            self.assertNotEqual(first["inventory_root"], second["inventory_root"])

    def test_read_only_pack_commands_do_not_initialize_inventory(self):
        with tempfile.TemporaryDirectory() as raw:
            data_root = Path(raw) / "data"
            commands = (
                ["pack-inventory"],
                ["install-plan", "RECOMMENDED_LOCAL"],
                ["project-portability", "--required-pack", "PIPPI_CORE"],
                ["installer-probe"],
            )
            env = dict(__import__("os").environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            for command in commands:
                result = subprocess.run(
                    [sys.executable, "-m", "ucm.pippi_cli", "--data-root", str(data_root), *command],
                    cwd=ROOT, env=env, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((data_root / "packs" / "INVENTORY.json").exists(), command)

    def test_pack_record_is_the_explicit_inventory_write_surface(self):
        with tempfile.TemporaryDirectory() as raw:
            store = PackStore(Path(raw)); initial = store.inventory()
            self.assertFalse(store.inventory_path.exists())
            store.record(expected_inventory_root=initial["inventory_root"],
                pack_id="SEMCRYS_CORE", state="INSTALLED_UNBOUND",
                installed_root="1"*64, binding_root=None, evidence_roots=["2"*64])
            self.assertTrue(store.inventory_path.is_file())

    def test_bundled_external_contracts_are_exact(self):
        result = verify_bundled_optional_pack_manifests(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual({row["pack_id"] for row in result["checked"]},
                         {"SEMCRYS_CORE", "MEMORY_VAULT_ADAPTER"})

    def test_public_abi_matches_direct_planner(self):
        inventory = default_pack_inventory()
        direct = build_install_plan(profile="RECOMMENDED_LOCAL", inventory=inventory,
                                    requested_packs=[], offline_artifact_roots=[],
                                    allow_remote_downloads=False)
        registry = capability_registry()
        request = {"schema":"mosaic.ucm.request.v0.2", "surface":"BUILD_PIPPI_INSTALL_PLAN",
            "payload":{"profile": "RECOMMENDED_LOCAL", "inventory": inventory,
                       "requested_packs": [], "offline_artifact_roots": [],
                       "allow_remote_downloads": False},
            "request_id":"test:packs", "profile_selection":{
                "schema":"mosaic.ucm.product-profile-selection.v0.1", "profile_id":"AUTHORING",
                "capability_registry_root":registry["root"]}}
        via_abi = invoke(request)
        self.assertEqual(via_abi["result"], direct)

    def test_installer_probe_and_no_console_launchers(self):
        with tempfile.TemporaryDirectory() as raw:
            probe = probe_installer(Path(raw))
        self.assertEqual(probe["status"], "PASS")
        self.assertEqual(probe["rainbow_sun"], "VERIFIED_ASSET")
        for name in ("PIPPI-INSTALLER.vbs", "PIPPI-HEADLESS.vbs",
                     "PIPPI-DASHBOARD.vbs", "PIPPI-SERVICE.vbs"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("shell.Run", text)
            self.assertIn(", 0, False", text)


if __name__ == "__main__": unittest.main()
