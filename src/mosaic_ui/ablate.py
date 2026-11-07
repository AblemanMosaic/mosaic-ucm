"""Build deterministic application-bound Mosaic UI runtime slices.

The slicer accepts only a verified Foundry output. It narrows the catalog to the
component kinds reachable from that subject and physically omits unrequested
runtime pathways. Shared realizer modules remain whole and are disclosed.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from mosaic_ui_std.catalog import (
    DEFAULT_CATALOG,
    PROFILE_CATALOG_SCHEMA,
    RUNTIME_CATALOG_SCHEMA,
    RUNTIME_PROFILE_CATALOG_SCHEMA,
    check_realizable,
    load_catalog,
    load_runtime_catalog,
    require_realized,
    validate_catalog,
)

from .canonical import atomic_write, canonical_bytes, commitment
from .model import ALL_COMPONENT_KINDS, COMPONENT_KINDS, validate_tree, walk
from .probe import load_subject


ABLATION_SCHEMA = "mosaic.ui.ablation-manifest.v0.1"
RECEIPT_SCHEMA = "mosaic.ui.ablation-receipt.v0.1"
RETENTION_PROFILE_SCHEMA = "mosaic.ui.retention-profile.v0.2"
VERSION = "0.1.0"
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
ROOT = Path(__file__).resolve().parent.parent
DEPENDENCY_GRAPH_PATH = ROOT / "mosaic_ui" / "components" / "dependencies.json"
SHARED_SUBSTRATE = {
    "HEADLESS": ["mosaic_ui/headless.py"],
    "BROWSER": ["mosaic_ui/headless.py", "mosaic_ui/browser_realizer.py", "mosaic_ui/browser_host.py",
                "mosaic_ui/web_distribution.py"],
    "WIN32": ["mosaic_ui/headless.py", "mosaic_ui/win32.py"],
}


class AblationRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}:{detail}")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_dependency_graph(path: Path = DEPENDENCY_GRAPH_PATH) -> dict[str, Any]:
    graph = json.loads(path.read_text(encoding="utf-8"))
    if graph.get("schema") != "mosaic.ui.component-dependency-graph.v0.2":
        raise AblationRefusal("DEPENDENCY_GRAPH_SCHEMA_REFUSED")
    components, pathways = graph.get("components"), graph.get("pathways")
    if not isinstance(components, dict) or set(components) != set(ALL_COMPONENT_KINDS):
        raise AblationRefusal("DEPENDENCY_GRAPH_COMPONENT_SET_REFUSED")
    if not isinstance(pathways, dict) or set(pathways) != {"HEADLESS", "BROWSER", "WIN32"}:
        raise AblationRefusal("DEPENDENCY_GRAPH_PATHWAY_SET_REFUSED")
    optional = graph.get("optional_pathways")
    if not isinstance(optional, dict) or not optional:
        raise AblationRefusal("DEPENDENCY_GRAPH_OPTIONAL_PATHWAYS_REFUSED")
    for name, spec in optional.items():
        if not isinstance(name, str) or not isinstance(spec, dict) or set(spec) != {"modules", "requires"}:
            raise AblationRefusal("DEPENDENCY_GRAPH_OPTIONAL_PATHWAY_SHAPE_REFUSED", str(name))
        if not isinstance(spec["modules"], list) or not isinstance(spec["requires"], list) \
                or not set(spec["requires"]) <= set(optional):
            raise AblationRefusal("DEPENDENCY_GRAPH_OPTIONAL_PATHWAY_VALUE_REFUSED", name)
    paths = list(components.values()) + [item for values in pathways.values() for item in values]
    paths += [item for spec in optional.values() for item in spec["modules"]]
    if not all(isinstance(item, str) and item and "\\" not in item and ".." not in Path(item).parts for item in paths):
        raise AblationRefusal("DEPENDENCY_GRAPH_PATH_REFUSED")
    if graph.get("authority_effect") != "NONE":
        raise AblationRefusal("DEPENDENCY_GRAPH_AUTHORITY_REFUSED")
    return graph


def validate_retention_profile(value: Any) -> dict[str, Any]:
    keys = {"schema", "retain_kinds", "realizers", "pathways", "themes", "standing", "authority_effect"}
    if not isinstance(value, dict) or set(value) != keys or value.get("schema") != RETENTION_PROFILE_SCHEMA:
        raise AblationRefusal("RETENTION_PROFILE_SCHEMA_REFUSED")
    kinds, realizers, pathways, themes = value["retain_kinds"], value["realizers"], value["pathways"], value["themes"]
    if not isinstance(kinds, list) or kinds != sorted(set(kinds)) or not set(kinds) <= set(ALL_COMPONENT_KINDS):
        raise AblationRefusal("RETENTION_PROFILE_KIND_SET_REFUSED")
    if not isinstance(realizers, list) or realizers != sorted(set(realizers)) or not set(realizers) <= {"HEADLESS", "BROWSER", "WIN32"}:
        raise AblationRefusal("RETENTION_PROFILE_REALIZER_SET_REFUSED")
    allowed_pathways = set(load_dependency_graph()["optional_pathways"])
    if not isinstance(pathways, list) or pathways != sorted(set(pathways)) or not set(pathways) <= allowed_pathways:
        raise AblationRefusal("RETENTION_PROFILE_PATHWAY_SET_REFUSED")
    if not isinstance(themes, list) or themes != sorted(set(themes)) or not all(isinstance(item, str) and item for item in themes):
        raise AblationRefusal("RETENTION_PROFILE_THEME_SET_REFUSED")
    if value.get("authority_effect") != "NONE":
        raise AblationRefusal("RETENTION_PROFILE_AUTHORITY_REFUSED")
    return value


def load_retention_profile(path: Path) -> dict[str, Any]:
    return validate_retention_profile(json.loads(path.read_text(encoding="utf-8")))


def _resolve_optional_pathways(graph: dict[str, Any], requested: set[str]) -> list[str]:
    resolved: set[str] = set()

    def include(name: str) -> None:
        if name in resolved:
            return
        if name not in graph["optional_pathways"]:
            raise AblationRefusal("UNKNOWN_OPTIONAL_PATHWAY", name)
        for dependency in graph["optional_pathways"][name]["requires"]:
            include(dependency)
        resolved.add(name)

    for name in requested:
        include(name)
    return sorted(resolved)


def _source_payloads() -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}
    for name in ("LICENSE", "NOTICE"):
        candidate = ROOT / name
        if not candidate.is_file():
            matches = sorted(ROOT.glob(f"mosaic_ui-*.dist-info/licenses/{name}"),
                             key=lambda path: path.relative_to(ROOT).as_posix())
            candidate = matches[0] if matches else candidate
        if not candidate.is_file():
            raise AblationRefusal("DISTRIBUTION_LEGAL_FILE_ABSENT", name)
        payloads[name] = candidate.read_bytes()
    project = ROOT / "pyproject.toml"
    payloads["pyproject.toml"] = project.read_bytes() if project.is_file() else _slice_pyproject()
    for package in ("mosaic_ui", "mosaic_ui_std"):
        package_root = ROOT / package
        for path in sorted(package_root.rglob("*"),
                           key=lambda item: item.relative_to(package_root).as_posix()):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix in {
                ".py", ".json", ".js", ".ts", ".html", ".css", ".woff2", ".txt",
            }:
                payloads[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    return payloads


def _stdlib_init(
    include_theme: bool, include_signature: bool = False, include_theme_v02: bool = False,
) -> bytes:
    lines = [
        '"""Application-bound Mosaic UI standard library."""',
        "from .catalog import (",
        "    DECLARED_ONLY, DEFAULT_CATALOG, REALIZERS, check_realizable, load_catalog,",
        "    load_runtime_catalog, require_realized, tiers, validate_catalog,",
        ")",
        "from .lifecycle import LIFECYCLE_SCHEMA, render, validate_lifecycle",
    ]
    exports = [
        "DECLARED_ONLY", "DEFAULT_CATALOG", "LIFECYCLE_SCHEMA", "REALIZERS", "check_realizable",
        "load_catalog", "load_runtime_catalog", "render", "require_realized", "tiers", "validate_catalog", "validate_lifecycle",
    ]
    if include_theme:
        lines.append("from .theme import THEMES_DIR, load_theme, validate_theme, validate_tokens")
        exports.extend(["THEMES_DIR", "load_theme", "validate_theme", "validate_tokens"])
    if include_signature:
        lines.append("from .signature import (DENSITIES_DIR, PROFILES_DIR, load_density, load_signature_profile, resolve_signature_theme, validate_density, validate_signature_profile)")
        exports.extend(["DENSITIES_DIR", "PROFILES_DIR", "load_density", "load_signature_profile",
                        "resolve_signature_theme", "validate_density", "validate_signature_profile"])
    if include_theme_v02:
        lines.append("from .theme_v02 import (FONTS_DIR, THEMES_V02_DIR, list_themes_v02, load_font_registry, load_theme_v02, project_to_v01, theme_v02_commitment, validate_theme_v02, verify_font_assets)")
        exports.extend(["FONTS_DIR", "THEMES_V02_DIR", "list_themes_v02", "load_font_registry", "load_theme_v02",
                        "project_to_v01", "theme_v02_commitment", "validate_theme_v02", "verify_font_assets"])
    lines.extend([f"__all__ = {exports!r}", f'__version__ = "{VERSION}"', ""])
    return "\n".join(lines).encode("ascii")


def _slice_pyproject() -> bytes:
    return f"""[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "mosaic-ui"
version = "{VERSION}"
description = "Application-bound Mosaic UI runtime slice"
requires-python = ">=3.12"
license = {{text = "Apache-2.0"}}
dependencies = []

[tool.setuptools]
packages = ["mosaic_ui", "mosaic_ui.components", "mosaic_ui_std"]

[tool.setuptools.package-data]
"mosaic_ui" = ["web/*", "contrib/web_adapters/*", "source/*.json", "evidence_gates.json", "review_binding.json", "packs/*/*.html", "packs/*/*.css", "packs/*/*.json"]
"mosaic_ui_std" = ["catalog.json", "themes/*.json", "themes_v02/*.json", "fonts/*", "profiles/*.json", "densities/*.json"]
"mosaic_ui.components" = ["dependencies.json"]
""".encode("ascii")


def _reduced_catalog(
    source_catalog: dict[str, Any], retained_kinds: list[str], subject_root: str
) -> dict[str, Any]:
    source_root = commitment("MOSAIC.UI.STD.CATALOG.v0.1", source_catalog)
    retained = set(retained_kinds)
    runtime = source_catalog.get("schema") == RUNTIME_CATALOG_SCHEMA
    all_kinds = set(ALL_COMPONENT_KINDS if runtime else COMPONENT_KINDS)
    catalog = {
        **source_catalog,
        "schema": RUNTIME_PROFILE_CATALOG_SCHEMA if runtime else PROFILE_CATALOG_SCHEMA,
        "catalog_id": f'{source_catalog["catalog_id"]}-APP-{subject_root[:12]}',
        "components": [component for component in source_catalog["components"] if component["kind"] in retained],
        "tier_basis": source_catalog["tier_basis"] + "; APPLICATION_BOUND_EXACT_KIND_SCOPE",
        "profile": {
            "mode": "APPLICATION_BOUND",
            "source_catalog_root": source_root,
            "subject_root": subject_root,
            "retained_kinds": retained_kinds,
            "removed_kinds": sorted(all_kinds - retained),
        },
    }
    validate_catalog(catalog)
    return catalog


def _write_zip(path: Path, entries: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, entries[name])


def _sbom(entries: dict[str, bytes], profile_root: str, profile: dict[str, Any]) -> dict[str, Any]:
    serial = f"{profile_root[:8]}-{profile_root[8:12]}-{profile_root[12:16]}-{profile_root[16:20]}-{profile_root[20:32]}"
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "component": {"type": "library", "name": "mosaic-ui", "version": VERSION,
                          "bom-ref": f"pkg:pypi/mosaic-ui@{VERSION}?profile={profile_root[:12]}"},
            "properties": [
                {"name": "mosaic:profile_root", "value": profile_root},
                {"name": "mosaic:authority_effect", "value": "NONE"},
                {"name": "mosaic:realizers", "value": ",".join(profile["requested_realizers"])},
            ],
        },
        "components": [
            {"type": "file", "name": name, "hashes": [{"alg": "SHA-256", "content": _sha256(data)}]}
            for name, data in sorted(entries.items())
        ],
    }


def _signing_request(entries: dict[str, bytes], profile_root: str, status: str = "UNSIGNED") -> dict[str, Any]:
    payload = {name: _sha256(data) for name, data in sorted(entries.items())}
    return {
        "schema": "mosaic.ui.signing-request.v0.1",
        "profile_root": profile_root,
        "payload_root": commitment("MOSAIC.UI.SIGNING_PAYLOAD.v0.1", payload),
        "digest_algorithm": "SHA-256",
        "signature_status": status,
        "external_signature_format": "DSSE_OR_PLATFORM_DETACHED_SIGNATURE",
        "claim_boundary": "SIGNING_REQUEST_IS_NOT_A_SIGNATURE_OR_TRUST_ASSERTION",
        "authority_effect": "NONE",
    }


def _load_signature_envelope(path: Path, payload_root: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    keys = {"schema", "payload_root", "signer_id", "algorithm", "signature", "authority_effect"}
    if not isinstance(value, dict) or set(value) != keys or value.get("schema") != "mosaic.ui.detached-signature-envelope.v0.1":
        raise AblationRefusal("SIGNATURE_ENVELOPE_SCHEMA_REFUSED")
    if value.get("payload_root") != payload_root:
        raise AblationRefusal("SIGNATURE_PAYLOAD_ROOT_REFUSED")
    if not all(isinstance(value.get(field), str) and value[field] for field in ("signer_id", "algorithm", "signature")):
        raise AblationRefusal("SIGNATURE_ENVELOPE_VALUE_REFUSED")
    if value.get("authority_effect") != "NONE":
        raise AblationRefusal("SIGNATURE_ENVELOPE_AUTHORITY_REFUSED")
    return value


def _wheel_entries(
    entries: dict[str, bytes], *, version: str = VERSION, scripts: dict[str, str] | None = None,
) -> dict[str, bytes]:
    wheel = {
        name: data for name, data in entries.items()
        if name.startswith("mosaic_ui/") or name.startswith("mosaic_ui_std/") or name.startswith("MOSAIC-")
    }
    dist_info = f"mosaic_ui-{version}.dist-info"
    wheel[f"{dist_info}/METADATA"] = (
        "Metadata-Version: 2.3\n"
        "Name: mosaic-ui\n"
        f"Version: {version}\n"
        "Summary: Application-bound Mosaic UI runtime slice\n"
        "Requires-Python: >=3.12\n"
        "License-Expression: Apache-2.0\n\n"
    ).encode("ascii")
    wheel[f"{dist_info}/WHEEL"] = (
        "Wheel-Version: 1.0\nGenerator: mosaic-ui-ablate\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    ).encode("ascii")
    if scripts:
        lines = ["[console_scripts]\n"]
        lines.extend(f"{name} = {target}\n" for name, target in sorted(scripts.items()))
        wheel[f"{dist_info}/entry_points.txt"] = "".join(lines).encode("utf-8")
    wheel[f"{dist_info}/licenses/LICENSE"] = entries["LICENSE"]
    wheel[f"{dist_info}/licenses/NOTICE"] = entries["NOTICE"]
    record_path = f"{dist_info}/RECORD"
    rows = []
    for name, data in sorted(wheel.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode("ascii").rstrip("=")
        rows.append(f"{name},sha256={digest},{len(data)}\n")
    rows.append(f"{record_path},,\n")
    wheel[record_path] = "".join(rows).encode("ascii")
    return wheel


def _measure_cold_import(archive_path: Path, include_native: bool) -> dict[str, Any]:
    script = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from mosaic_ui.headless import HeadlessUI
from mosaic_ui.components import load_handlers
from mosaic_ui_std.catalog import load_catalog
if sys.argv[2] == "1":
    import mosaic_ui.native_realizer
load_handlers(load_catalog())
print(json.dumps(sorted(name for name in sys.modules if name == "mosaic_ui" or name.startswith("mosaic_ui.") or name == "mosaic_ui_std" or name.startswith("mosaic_ui_std."))))
'''
    with tempfile.TemporaryDirectory(prefix="mosaic-ui-import-") as raw:
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(raw)
        run = subprocess.run(
            [sys.executable, "-I", "-c", script, raw, "1" if include_native else "0"],
            capture_output=True, text=True, timeout=30,
        )
    if run.returncode != 0:
        raise AblationRefusal("COLD_IMPORT_MEASUREMENT_REFUSED", run.stderr[-1000:])
    modules = json.loads(run.stdout)
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        paths = []
        for module in modules:
            package_path = module.replace(".", "/")
            candidates = (f"{package_path}.py", f"{package_path}/__init__.py")
            paths.extend(candidate for candidate in candidates if candidate in names)
        paths = sorted(set(paths))
        byte_count = sum(len(archive.read(path)) for path in paths)
    return {"module_count": len(paths), "source_bytes": byte_count, "modules": modules}


def verify_slice(archive_path: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    archive_path = archive_path.resolve()
    receipt_path = (receipt_path or archive_path.with_suffix(".receipt.json")).resolve()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise AblationRefusal("RECEIPT_SCHEMA_REFUSED")
    body = dict(receipt)
    observed_commitment = body.pop("receipt_commitment", None)
    if observed_commitment != commitment("MOSAIC.UI.ABLATION_RECEIPT.v0.1", body):
        raise AblationRefusal("RECEIPT_COMMITMENT_REFUSED")
    if _sha256(archive_path.read_bytes()) != receipt.get("archive_sha256"):
        raise AblationRefusal("ARCHIVE_HASH_REFUSED")
    wheel_path = archive_path.parent / str(receipt.get("wheel", ""))
    if not wheel_path.is_file() or _sha256(wheel_path.read_bytes()) != receipt.get("wheel_sha256"):
        raise AblationRefusal("WHEEL_HASH_REFUSED")
    if receipt.get("authority_effect") != "NONE" or receipt.get("disposition") != "PASS_LOCAL_CANDIDATE":
        raise AblationRefusal("RECEIPT_DISPOSITION_REFUSED")

    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise AblationRefusal("ARCHIVE_STRUCTURE_REFUSED")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} or ":" in part or "\\" in part for part in path.parts):
                raise AblationRefusal("ARCHIVE_PATH_REFUSED", name)
        manifest = json.loads(archive.read("MOSAIC-UI-ABLATION-MANIFEST.json"))
        if manifest.get("schema") != ABLATION_SCHEMA:
            raise AblationRefusal("MANIFEST_SCHEMA_REFUSED")
        if commitment("MOSAIC.UI.ABLATION.MANIFEST.v0.1", manifest) != receipt.get("manifest_root"):
            raise AblationRefusal("MANIFEST_COMMITMENT_REFUSED")
        inventory = manifest.get("inventory")
        if not isinstance(inventory, dict) or set(inventory) != set(names) - {"MOSAIC-UI-ABLATION-MANIFEST.json"}:
            raise AblationRefusal("INVENTORY_SET_REFUSED")
        for name, expected in inventory.items():
            if _sha256(archive.read(name)) != expected:
                raise AblationRefusal("INVENTORY_HASH_REFUSED", name)
        catalog = json.loads(archive.read("mosaic_ui_std/catalog.json"))
        validate_catalog(catalog)
        if catalog["profile"]["retained_kinds"] != receipt.get("retained_kinds"):
            raise AblationRefusal("CATALOG_RECEIPT_SCOPE_REFUSED")
        if manifest.get("profile_root") != receipt.get("profile_root"):
            raise AblationRefusal("PROFILE_ROOT_REFUSED")
        sbom = json.loads(archive.read("MOSAIC-UI-SBOM.cdx.json"))
        if sbom.get("bomFormat") != "CycloneDX" or sbom.get("specVersion") != "1.5":
            raise AblationRefusal("SBOM_REFUSED")
        signing = json.loads(archive.read("MOSAIC-UI-SIGNING-REQUEST.json"))
        if signing.get("signature_status") not in {"UNSIGNED", "EXTERNAL_ENVELOPE_PRESENT_UNVERIFIED"} \
                or signing.get("profile_root") != receipt.get("profile_root"):
            raise AblationRefusal("SIGNING_REQUEST_REFUSED")
        if signing["signature_status"] == "EXTERNAL_ENVELOPE_PRESENT_UNVERIFIED":
            envelope = json.loads(archive.read("MOSAIC-UI-DETACHED-SIGNATURE.json"))
            if envelope.get("payload_root") != signing.get("payload_root"):
                raise AblationRefusal("SIGNATURE_PAYLOAD_ROOT_REFUSED")
    with zipfile.ZipFile(wheel_path) as wheel:
        record_name = f"mosaic_ui-{VERSION}.dist-info/RECORD"
        if wheel.testzip() is not None or record_name not in wheel.namelist():
            raise AblationRefusal("WHEEL_STRUCTURE_REFUSED")
        rows = wheel.read(record_name).decode("ascii").splitlines()
        recorded = set()
        for row in rows:
            name, digest, size = row.rsplit(",", 2)
            recorded.add(name)
            if name == record_name:
                if digest or size:
                    raise AblationRefusal("WHEEL_RECORD_SELF_REFUSED")
                continue
            data = wheel.read(name)
            expected = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode("ascii").rstrip("=")
            if digest != f"sha256={expected}" or size != str(len(data)):
                raise AblationRefusal("WHEEL_RECORD_HASH_REFUSED", name)
        if recorded != set(wheel.namelist()):
            raise AblationRefusal("WHEEL_RECORD_SET_REFUSED")
    return {
        "schema": "mosaic.ui.ablation-verification.v0.1",
        "status": "PASS",
        "archive_sha256": receipt["archive_sha256"],
        "wheel_sha256": receipt["wheel_sha256"],
        "profile_root": receipt["profile_root"],
        "retained_kinds": receipt["retained_kinds"],
        "authority_effect": "NONE",
    }


def build_slice(
    generated_dir: Path,
    output_dir: Path,
    realizers: tuple[str, ...] = ("HEADLESS",),
    themes: tuple[str, ...] = (),
    retain_kinds: tuple[str, ...] = (),
    retention_profile: dict[str, Any] | None = None,
    signature_envelope: Path | None = None,
    include_pathways: tuple[str, ...] = (),
    signature_profile: str | None = None,
    densities: tuple[str, ...] = (),
    v02_themes: tuple[str, ...] = (),
) -> dict[str, Any]:
    retention_profile = retention_profile or {
        "schema": RETENTION_PROFILE_SCHEMA, "retain_kinds": [], "realizers": [], "pathways": [], "themes": [],
        "standing": "LOCAL_CANDIDATE", "authority_effect": "NONE",
    }
    validate_retention_profile(retention_profile)
    requested_realizers = sorted(set(realizers))
    if not requested_realizers or not set(requested_realizers) <= {"HEADLESS", "BROWSER", "WIN32"}:
        raise AblationRefusal("REALIZER_SET_REFUSED", ",".join(requested_realizers))
    graph = load_dependency_graph()
    requested_pathways = _resolve_optional_pathways(
        graph, set(include_pathways) | set(retention_profile.get("pathways", ())),
    )

    payload, subject = load_subject(generated_dir.resolve())
    application = payload.get("application")
    if not isinstance(application, dict) or not isinstance(application.get("tree"), dict):
        raise AblationRefusal("APPLICATION_SUBJECT_REFUSED")
    operations = set(application.get("declared_operation_ids", ()))
    tree_validation = validate_tree(application["tree"], operations)
    required_kinds = sorted({str(item.get("kind")) for item in walk(application["tree"])})
    declared_kinds = set(retain_kinds) | set(retention_profile.get("retain_kinds", ()))
    retained_kinds = sorted(set(required_kinds) | declared_kinds)
    if "ACCESSIBILITY" in requested_pathways:
        retained_kinds = sorted(ALL_COMPONENT_KINDS)
    elif "FUNCTIONAL_REVIEW" in requested_pathways:
        from mosaic_ui_std.signature import load_signature_profile

        signature_kinds = set(load_signature_profile()["component_kinds"])
        retained_kinds = sorted(set(retained_kinds) | signature_kinds | {"LABEL", "PANEL", "WINDOW"})
    unknown = sorted(set(retained_kinds) - set(ALL_COMPONENT_KINDS))
    if unknown:
        raise AblationRefusal("UNKNOWN_COMPONENT_KIND", ",".join(unknown))

    source_catalog = load_runtime_catalog(DEFAULT_CATALOG)
    for realizer in requested_realizers:
        check_realizable(source_catalog, application["tree"], realizer)
        require_realized(source_catalog, retained_kinds, realizer)
    reduced_catalog = _reduced_catalog(source_catalog, retained_kinds, subject["commitment"])

    source_payloads = _source_payloads()
    native_pathways = {"CAPTURE", "CONFORMANCE", "PILOT_NATIVE", "REVIEW", "SEMANTIC_DEMO"}
    if set(requested_pathways) & native_pathways and "WIN32" not in requested_realizers:
        raise AblationRefusal("OPTIONAL_PATHWAY_REQUIRES_WIN32", ",".join(sorted(set(requested_pathways) & native_pathways)))
    retained_modules = set(graph["pathways"]["HEADLESS"])
    if "BROWSER" in requested_realizers:
        retained_modules.update(graph["pathways"]["BROWSER"])
    if "WIN32" in requested_realizers:
        retained_modules.update(graph["pathways"]["WIN32"])
    retained_modules.update(graph["components"][kind] for kind in retained_kinds)
    for pathway in requested_pathways:
        retained_modules.update(graph["optional_pathways"][pathway]["modules"])

    signature_value: dict[str, Any] | None = None
    selected_densities: list[str] = []
    requested_themes = tuple(themes)
    if signature_profile is not None:
        from mosaic_ui_std.signature import load_signature_profile

        signature_value = load_signature_profile()
        if signature_profile != signature_value["profile_id"]:
            raise AblationRefusal("SIGNATURE_PROFILE_NOT_FOUND", signature_profile)
        requested_themes = requested_themes or (signature_value["default_theme"],)
        requested_densities = tuple(densities) or (signature_value["default_density"],)
        if not set(requested_themes) <= set(signature_value["themes"]):
            raise AblationRefusal("SIGNATURE_THEME_SCOPE_REFUSED", ",".join(sorted(set(requested_themes))))
        if not set(requested_densities) <= set(signature_value["densities"]):
            raise AblationRefusal("SIGNATURE_DENSITY_SCOPE_REFUSED", ",".join(sorted(set(requested_densities))))
        retained_modules.update({"mosaic_ui_std/theme.py", "mosaic_ui_std/signature.py"})
        selected_densities = sorted(set(requested_densities))
    elif densities:
        raise AblationRefusal("DENSITY_REQUIRES_SIGNATURE_PROFILE", ",".join(densities))

    selected_v02_themes: list[str] = []
    if "VISUAL_SYSTEM_V02" in requested_pathways:
        requested_v02 = sorted(set(v02_themes or ("signature-dark",)))
        available_v02 = {
            path.removeprefix("mosaic_ui_std/themes_v02/").removesuffix(".json")
            for path in source_payloads if path.startswith("mosaic_ui_std/themes_v02/")
        }
        unknown_v02 = sorted(set(requested_v02) - available_v02)
        if unknown_v02:
            raise AblationRefusal("THEME_V02_NOT_FOUND", ",".join(unknown_v02))
        for theme_id in requested_v02:
            retained_modules.add(f"mosaic_ui_std/themes_v02/{theme_id}.json")
        selected_v02_themes = requested_v02
    elif v02_themes:
        raise AblationRefusal("THEME_V02_PATHWAY_NOT_RETAINED", ",".join(v02_themes))

    entries = {name: source_payloads[name] for name in sorted(retained_modules)}
    entries["mosaic_ui_std/__init__.py"] = _stdlib_init(
        "WIN32" in requested_realizers or signature_value is not None, signature_value is not None,
        "VISUAL_SYSTEM_V02" in requested_pathways,
    )
    entries["mosaic_ui_std/catalog.json"] = canonical_bytes(reduced_catalog) + b"\n"
    retained_modules.add("mosaic_ui_std/catalog.json")
    for legal in ("LICENSE", "NOTICE"):
        entries[legal] = source_payloads[legal]
        retained_modules.add(legal)
    entries["pyproject.toml"] = _slice_pyproject()
    retained_modules.add("pyproject.toml")

    selected_themes: list[str] = []
    for theme in sorted(set(requested_themes)):
        name = theme if theme.endswith(".json") else f"{theme}.json"
        relative = f"mosaic_ui_std/themes/{name}"
        if relative not in source_payloads:
            raise AblationRefusal("THEME_NOT_FOUND", name)
        if signature_value is None and not set(requested_realizers) & {"BROWSER", "WIN32"}:
            raise AblationRefusal("THEME_PATHWAY_NOT_RETAINED", name)
        entries[relative] = source_payloads[relative]
        retained_modules.add(relative)
        selected_themes.append(name.removesuffix(".json"))

    if signature_value is not None:
        reduced_signature = copy.deepcopy(signature_value)
        reduced_signature["themes"] = selected_themes
        reduced_signature["densities"] = selected_densities
        reduced_signature["default_theme"] = selected_themes[0]
        reduced_signature["default_density"] = selected_densities[0]
        profile_path = "mosaic_ui_std/profiles/mosaic-signature.json"
        entries[profile_path] = canonical_bytes(reduced_signature) + b"\n"
        retained_modules.add(profile_path)
        for density_id in selected_densities:
            relative = f"mosaic_ui_std/densities/{density_id}.json"
            if relative not in source_payloads:
                raise AblationRefusal("DENSITY_NOT_FOUND", density_id)
            entries[relative] = source_payloads[relative]
            retained_modules.add(relative)

    candidate_paths = sorted(source_payloads)
    omitted_modules = sorted(set(candidate_paths) - retained_modules)
    source_bytes = sum(len(source_payloads[name]) for name in candidate_paths)
    runtime_bytes = sum(len(entries[name]) for name in entries)
    profile = {
        "mode": "APPLICATION_BOUND",
        "subject_root": subject["commitment"],
        "generated_root": subject["generated_root"],
        "requested_realizers": requested_realizers,
        "requested_pathways": requested_pathways,
        "required_kinds": required_kinds,
        "explicitly_retained_kinds": sorted(declared_kinds),
        "retained_kinds": retained_kinds,
        "removed_kinds": sorted(set(ALL_COMPONENT_KINDS) - set(retained_kinds)),
        "themes": selected_themes,
        "signature_profile": signature_profile,
        "densities": selected_densities,
        "themes_v02": selected_v02_themes,
        "retention_profile_root": commitment("MOSAIC.UI.RETENTION_PROFILE.v0.1", retention_profile),
    }
    profile_root = commitment("MOSAIC.UI.ABLATION.PROFILE.v0.1", profile)
    entries["MOSAIC-UI-SBOM.cdx.json"] = canonical_bytes(_sbom(entries, profile_root, profile)) + b"\n"
    signing = _signing_request(entries, profile_root)
    envelope = None
    if signature_envelope is not None:
        envelope = _load_signature_envelope(signature_envelope.resolve(), signing["payload_root"])
        signing["signature_status"] = "EXTERNAL_ENVELOPE_PRESENT_UNVERIFIED"
        entries["MOSAIC-UI-DETACHED-SIGNATURE.json"] = canonical_bytes(envelope) + b"\n"
    entries["MOSAIC-UI-SIGNING-REQUEST.json"] = canonical_bytes(signing) + b"\n"
    inventory = {name: _sha256(data) for name, data in sorted(entries.items())}
    manifest = {
        "schema": ABLATION_SCHEMA,
        "profile_root": profile_root,
        "profile": profile,
        "subject": subject,
        "tree_validation": tree_validation,
        "catalog_root": commitment("MOSAIC.UI.STD.CATALOG-PROFILE.v0.1", reduced_catalog),
        "dependency_graph_root": commitment("MOSAIC.UI.COMPONENT_DEPENDENCY_GRAPH.v0.2", graph),
        "dependency_reasons": {
            kind: [graph["components"][kind], *requested_realizers] for kind in retained_kinds
        },
        "retained_modules": sorted(retained_modules),
        "omitted_modules": omitted_modules,
        "shared_substrate": sorted({path for realizer in requested_realizers for path in SHARED_SUBSTRATE[realizer]}),
        "inventory": inventory,
        "size": {
            "source_package_bytes": source_bytes,
            "runtime_source_bytes": runtime_bytes,
            "removed_runtime_source_bytes": source_bytes - runtime_bytes,
            "inventory_payload_bytes": sum(len(data) for data in entries.values()),
        },
        "boundaries": [
            "CATALOG_SCOPE_IS_EXACT_AND_FAILS_CLOSED_FOR_OMITTED_KINDS",
            "SHARED_REALIZER_MODULES_ARE_RETAINED_WHOLE_NOT_KIND_LEVEL_TREE_SHAKEN",
            *(["ACCESSIBILITY_REFERENCE_AUDIT_RETAINS_FULL_RUNTIME_KIND_SET"]
              if "ACCESSIBILITY" in requested_pathways else []),
            *(["FUNCTIONAL_REVIEW_RETAINS_SIGNATURE_APPLICATION_KIND_CLOSURE"]
              if "FUNCTIONAL_REVIEW" in requested_pathways else []),
            *(["PLAY_2D_IS_AN_ENGINE_NEUTRAL_EXPERIMENTAL_PATHWAY"]
              if "PLAY_2D" in requested_pathways else []),
            *(["PLAY_ADAPTERS_ARE_BOUNDED_REALIZATION_EXPERIMENTS"]
              if "PLAY_ADAPTERS" in requested_pathways else []),
            *(["PLAY_RUNTIME_QUALIFICATION_REQUIRES_AN_EXPLICIT_INSTALLED_EXECUTABLE_AND_HAS_NO_ADMISSION_EFFECT"]
              if "PLAY_RUNTIME_QUALIFICATION" in requested_pathways else []),
            *(["SPATIAL_3D_IS_AN_ENGINE_NEUTRAL_EXPERIMENTAL_PATHWAY"]
              if "SPATIAL_3D" in requested_pathways else []),
            *(["SIGNATURE_PROFILE_THEME_DENSITY_CLOSURE_IS_EXACT"]
              if signature_value is not None else []),
            *(["VISUAL_SYSTEM_V02_THEME_CLOSURE_IS_EXACT"]
              if "VISUAL_SYSTEM_V02" in requested_pathways else []),
            "SLICE_EVIDENCE_DOES_NOT_ESTABLISH_AUTHORITY_OR_HOST_BEHAVIOR",
        ],
        "standing": "LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }
    manifest_bytes = canonical_bytes(manifest) + b"\n"
    entries["MOSAIC-UI-ABLATION-MANIFEST.json"] = manifest_bytes
    manifest_root = commitment("MOSAIC.UI.ABLATION.MANIFEST.v0.1", manifest)
    installed_bytes = sum(len(data) for name, data in entries.items() if name != "pyproject.toml")

    archive_path = output_dir.resolve() / f"mosaic-ui-slice-{profile_root[:12]}.zip"
    _write_zip(archive_path, entries)
    archive_bytes = archive_path.read_bytes()
    archive_sha = _sha256(archive_bytes)
    wheel_path = output_dir.resolve() / f"mosaic_ui-{VERSION}-py3-none-any.whl"
    _write_zip(wheel_path, _wheel_entries(entries))
    wheel_bytes = wheel_path.read_bytes()
    wheel_sha = _sha256(wheel_bytes)
    cold_import = _measure_cold_import(archive_path, "WIN32" in requested_realizers)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "profile_root": profile_root,
        "manifest_root": manifest_root,
        "archive": archive_path.name,
        "archive_sha256": archive_sha,
        "archive_bytes": len(archive_bytes),
        "wheel": wheel_path.name,
        "wheel_sha256": wheel_sha,
        "wheel_bytes": len(wheel_bytes),
        "source_package_bytes": source_bytes,
        "runtime_source_bytes": runtime_bytes,
        "retained_package_bytes": runtime_bytes,
        "installed_payload_bytes": installed_bytes,
        "cold_import": cold_import,
        "removed_runtime_source_bytes": source_bytes - runtime_bytes,
        "removed_package_bytes": source_bytes - runtime_bytes,
        "retained_fraction_ppm": (runtime_bytes * 1_000_000) // source_bytes,
        "retained_kinds": profile["retained_kinds"],
        "removed_kinds": profile["removed_kinds"],
        "requested_realizers": requested_realizers,
        "themes": selected_themes,
        "signature_profile": signature_profile,
        "densities": selected_densities,
        "themes_v02": selected_v02_themes,
        "signature_status": signing["signature_status"],
        "signer_id": envelope["signer_id"] if envelope else None,
        "standing": "LOCAL_CANDIDATE",
        "authority_effect": "NONE",
    }
    receipt["disposition"] = "PASS_LOCAL_CANDIDATE"
    receipt["receipt_commitment"] = commitment("MOSAIC.UI.ABLATION_RECEIPT.v0.1", receipt)
    receipt_path = output_dir.resolve() / f"{archive_path.stem}.receipt.json"
    atomic_write(receipt_path, canonical_bytes(receipt) + b"\n")
    atomic_write(archive_path.with_suffix(".zip.sha256"), f"{archive_sha}  {archive_path.name}\n".encode("ascii"))
    return {
        **receipt, "archive_path": str(archive_path), "wheel_path": str(wheel_path),
        "receipt_path": str(receipt_path),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build a deterministic application-bound Mosaic UI slice")
    parser.add_argument("generated", type=Path, nargs="?", help="Verified Foundry output directory")
    parser.add_argument("output", type=Path, nargs="?", help="Output directory")
    parser.add_argument("--realizer", action="append", choices=("HEADLESS", "BROWSER", "WIN32"))
    parser.add_argument("--theme", action="append", default=[])
    parser.add_argument("--signature-profile")
    parser.add_argument("--density", action="append", default=[])
    parser.add_argument("--v02-theme", action="append", default=[])
    parser.add_argument("--retain-kind", action="append", default=[])
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--signature-envelope", type=Path)
    parser.add_argument("--include-pathway", action="append", default=[], choices=sorted(load_dependency_graph()["optional_pathways"]))
    parser.add_argument("--verify", type=Path, metavar="ARCHIVE")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    if args.verify:
        print(json.dumps(verify_slice(args.verify, args.receipt), indent=2, sort_keys=True))
        return
    if args.generated is None or args.output is None:
        parser.error("generated and output are required when not using --verify")
    profile = load_retention_profile(args.profile.resolve()) if args.profile else None
    profile_realizers = tuple(profile["realizers"]) if profile else ()
    profile_themes = tuple(profile["themes"]) if profile else ()
    realizers = tuple(args.realizer or profile_realizers or ["HEADLESS"])
    print(json.dumps(build_slice(
        args.generated, args.output, realizers, tuple(args.theme) + profile_themes,
        tuple(args.retain_kind), profile, args.signature_envelope, tuple(args.include_pathway),
        args.signature_profile, tuple(args.density), tuple(args.v02_theme),
    ), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
