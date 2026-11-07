"""Native and headless projections of the deterministic P/PPI pack installer."""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from .pippi_global import BOUNDARY, default_data_root
from .pippi_packs import (PackStore, build_install_plan, pack_registry,
                          verify_bundled_optional_pack_manifests)


def _native() -> tuple[Any, Any, Any, Any]:
    source_root = Path(__file__).resolve().parents[2]
    vendor = source_root / "vendor" / "mosaic-native"
    if vendor.is_dir() and str(vendor) not in sys.path: sys.path.insert(0, str(vendor))
    from mosaic_ui import win32
    from mosaic_ui.win32_image import NativeImage
    from mosaic_ui.branding import verified_logo_path
    from mosaic_ui_std.signature import resolve_signature_theme
    return win32, NativeImage, verified_logo_path, resolve_signature_theme


def probe_installer(data_root: Path | None = None) -> dict[str, Any]:
    source_root = Path(__file__).resolve().parents[2]
    registry = pack_registry(); inventory = PackStore(data_root or default_data_root()).inventory()
    manifests = verify_bundled_optional_pack_manifests(source_root)
    plan = build_install_plan(profile="RECOMMENDED_LOCAL", inventory=inventory)
    return {
        "schema": "mosaic.ucm.pippi-installer-probe.v0.1",
        "status": "PASS", "native_ui": "MOSAIC_WIN32",
        "headless_projection": "AVAILABLE", "rainbow_sun": "VERIFIED_ASSET",
        "registry_root": registry["registry_root"], "inventory_root": inventory["inventory_root"],
        "manifest_verification_root": manifests["verification_root"],
        "recommended_plan_root": plan["install_plan_root"],
        "installer_performs_downloads": False,
        "download_effect_boundary": "EXPLICIT_USER_AUTHORIZATION_AND_EXTERNAL_GATEWAY_REQUIRED",
        **BOUNDARY,
    }


class InstallerWindow:
    def __init__(self, data_root: Path) -> None:
        win32, NativeImage, verified_logo_path, resolve = _native()
        self.win32 = win32; self.logo = NativeImage(verified_logo_path())
        self.store = PackStore(data_root); self.inventory = self.store.inventory()
        self.registry = pack_registry(); self.profile = "RECOMMENDED_LOCAL"; self.allow_remote = False
        self.plan = build_install_plan(profile=self.profile, inventory=self.inventory)
        tokens = resolve("signature-dark", "comfortable")["tokens"]
        self.window = win32.NativeWindow("P/PPI Setup — Mosaic capability packs", tokens=tokens,
                                         width=1180, height=760)
        self.window.set_minimum_client_size(980, 650); self.window.set_icon(self.logo)
        self.window.image("brand_logo", self.logo, (24, 14, 62, 62), name="About P/PPI Setup",
                          command=self.show_about)
        self.window.label("brand", "P/PPI Setup", (100, 18, 260, 38), style="title")
        self.window.label("subtitle", "Choose capabilities without weakening the constitutional core",
                          (100, 56, 720, 25), style="quiet")
        self.window.badge("posture", (894, 24, 250, 30))
        self.window.label("profile_heading", "INSTALLATION PROFILE", (24, 108, 330, 24), style="quiet")
        self.window.table("profiles", ["Profile", "Purpose"], (24, 140, 420, 300), command=self.select_profile)
        self.window.label("pack_heading", "CAPABILITY PLAN", (468, 108, 680, 24), style="quiet")
        self.window.table("packs", ["Pack", "Current", "Plan"], (468, 140, 680, 390))
        self.window.label("summary", "", (24, 470, 1124, 56), style="heading")
        self.window.label("boundary", "", (24, 532, 1124, 54), style="quiet")
        self.window.button("local", "Plan local only", (24, 620, 180, 42), self.plan_local)
        self.window.button("remote", "Include downloads…", (216, 620, 190, 42), self.plan_remote)
        self.window.button("refresh", "Refresh inventory", (418, 620, 180, 42), self.refresh)
        self.window.button("close", "Close", (994, 620, 154, 42), self.window.close)
        self.window.style_button("local", primary=True)
        self.window.label("status", "Planning performs no downloads or installation effects.",
                          (24, 686, 1124, 30), style="accent")
        self.show()

    def show_about(self) -> None:
        win32, NativeImage, verified_logo_path, resolve = _native()
        logo = NativeImage(verified_logo_path())
        about = win32.NativeWindow("About P/PPI Setup", tokens=resolve("signature-dark", "comfortable")["tokens"],
                                   width=720, height=500, presentation="dialog")
        about.set_icon(logo); about.image("logo", logo, (30, 28, 120, 120), name="Mosaic rainbow sun")
        about.label("title", "P/PPI modular installation", (178, 38, 500, 44), style="title")
        about.label("body",
                    "The constitutional core works on its own. UGK standards are recommended.\n"
                    "SemCrys, Memory Vault, Courthouse, and native host adapters are optional.\n\n"
                    "P/PPI first creates an exact rooted plan. Downloads, bindings, credentials,\n"
                    "and service changes remain explicit external effects. Missing optional packs\n"
                    "never weaken a project contract or silently broaden authority.",
                    (30, 176, 650, 180))
        about.label("posture", "INFORMATION_ONLY · authority effect NONE · real A5 false · G0 closed",
                    (30, 390, 540, 30), style="accent")
        about.button("close", "Close", (566, 386, 120, 40), about.close)
        try: about.run_modal("close")
        finally: logo.close()

    def select_profile(self, value: str) -> None:
        if value in self.registry["profiles"]: self.profile = value
        self._replan()

    def plan_local(self) -> None:
        self.allow_remote = False; self._replan()

    def plan_remote(self) -> None:
        self.allow_remote = True; self._replan()
        if self.plan["holds"]:
            self.window.message("Authorization still required",
                "Remote-capable planning only identifies exact downloads and bindings. "
                "Nothing was fetched, installed, or bound.")

    def refresh(self) -> None:
        self.inventory = self.store.inventory(); self._replan()

    def _replan(self) -> None:
        self.plan = build_install_plan(profile=self.profile, inventory=self.inventory,
                                       allow_remote_downloads=self.allow_remote)
        self.show()

    def show(self) -> None:
        profile_purpose = {
            "MINIMAL_CORE": "Core, UCM, and native UI",
            "RECOMMENDED_LOCAL": "Core plus UGK standards",
            "PORTABLE_AGENT": "Portable adaptive orchestration",
            "TRANSTEMPORAL_PROJECT": "SemCrys and Memory Vault",
            "COURTHOUSE_CONNECTED": "Governed remote correspondence",
            "FULL_MOSAIC": "Every declared optional capability",
        }
        self.window.set_rows("profiles", [(key, profile_purpose[key]) for key in self.registry["profiles"]])
        self.window.set_table_selection("profiles", self.profile)
        self.window.set_rows("packs", [(row["pack_id"], row["current_state"], row["action"])
                                       for row in self.plan["actions"]])
        self.window.set_table_column_widths("profiles", (190, 218))
        self.window.set_table_column_widths("packs", (220, 160, 280))
        held = len(self.plan["holds"])
        self.window.set_badge("posture", "READY" if not held else f"{held} DECISIONS", "accent" if not held else "pending")
        self.window.set_text("summary", f"{self.profile.replace('_', ' ').title()} · {len(self.plan['selected_packs'])} packs")
        self.window.set_text("boundary", "Ready from existing verified components." if not held else
            "Optional capabilities need a verified artifact, explicit download authorization, or an external binding.\n"
            "The installed core remains usable and no requirement is silently removed.")
        self.window.set_text("status", "Rooted plan only · no effects performed · " + self.plan["install_plan_root"][:16] + "…")

    def run(self) -> int:
        try: return self.window.run()
        finally: self.logo.close()


def launch_installer(data_root: Path | None = None) -> int:
    return InstallerWindow(Path(data_root or default_data_root())).run()
