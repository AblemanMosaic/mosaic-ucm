"""Visual evidence for v0.2 themes in the general realizers (library L2b, ruling L2b-R3).

Same compositions, densities, viewports and states as the v0.1 baseline, over the 11 v0.2 themes. The matrix
(1,320 cases) is sampled with the L3 policy. Unlike v0.1, each BROWSER row also hashes the rendered document,
because v0.2 rendering (fonts, elevation, motion) lives in its CSS. Owning tool: tools/gen_visual_baseline_v02.py.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .realizer import create_realizer
from .sampling import build_plan
from .theme_payload import attach_theme_v02
from .visual_certification import COMPOSITIONS, DENSITIES, REALIZERS, STATES, VIEWPORTS, _case_payload

BASELINE_V02_PATH = Path(__file__).resolve().parent / "source" / "visual-baseline-v02.json"
V01_BASE_THEME = "signature-dark"  # composition payloads are built once, then given the v0.2 theme


def _factors() -> dict[str, list[Any]]:
    from mosaic_ui_std.theme_v02 import list_themes_v02
    return {"realizer": list(REALIZERS), "composition": list(COMPOSITIONS), "theme": list_themes_v02(),
            "density": list(DENSITIES), "viewport": [f"{w}x{h}" for w, h in VIEWPORTS], "state": list(STATES)}


def build_matrix_v02(mode: str = "auto") -> dict[str, Any]:
    plan = build_plan(_factors(), mode)
    rows = []
    for case in plan["cases"]:
        payload, target_id, selected = _case_payload(case["composition"], V01_BASE_THEME, case["density"], case["state"])
        payload = attach_theme_v02(payload, case["theme"])
        width, height = (int(x) for x in case["viewport"].split("x"))
        realizer = create_realizer(case["realizer"], payload)
        try:
            if case["state"] == "FOCUSED":
                realizer.apply({"intent": "FOCUS", "node_id": target_id})
            elif case["state"] == "SELECTED":
                realizer.apply({"intent": "SELECT", "node_id": target_id, "value": selected})
            projection = realizer.project(width, height)
            if projection["gates"]["disposition"] != "PASS":
                raise ValueError("VISUAL_V02_GATE_REFUSED:" + ":".join(str(case[k]) for k in case))
            row = {**case, "sha256": hashlib.sha256(canonical_bytes(projection)).hexdigest(),
                   "gate_commitment": projection["gates"]["commitment"]}
            if case["realizer"] == "BROWSER":
                row["document_sha256"] = hashlib.sha256(realizer.document(width, height).encode("utf-8")).hexdigest()
            rows.append(row)
        finally:
            realizer.close()
    value = {"schema": "mosaic.ui.visual-matrix-v02.v0.1", "plan_commitment": plan["commitment"], "mode": plan["mode"],
             "strength": plan["strength"], "full_product": plan["full_product"], "case_count": len(rows), "cases": rows,
             "claim_boundary": "SAMPLED_SEMANTIC_PROJECTION_AND_DOCUMENT_GOLDENS; NOT_PIXEL_OR_ASSISTIVE_TECHNOLOGY_EQUIVALENCE",
             "standing": "LOCAL_CANDIDATE_EVIDENCE", "authority_effect": "NONE"}
    value["matrix_root"] = commitment("MOSAIC.UI.VISUAL_MATRIX_V02.v0.1", value)
    return value


def record_baseline_v02(path: Path = BASELINE_V02_PATH) -> dict[str, Any]:
    value = build_matrix_v02()
    atomic_write(path, canonical_bytes(value) + b"\n")
    return value


def verify_baseline_v02(path: Path = BASELINE_V02_PATH) -> dict[str, Any]:
    committed, current = read_json(path), build_matrix_v02(read_json(path)["mode"])
    mismatches = [a.get("theme") + ":" + a.get("realizer") for a, b in zip(committed["cases"], current["cases"]) if a != b]
    if len(committed["cases"]) != len(current["cases"]):
        mismatches.append("CASE_COUNT")
    return {"schema": "mosaic.ui.visual-baseline-v02-verification.v0.1", "case_count": len(current["cases"]),
            "mismatches": mismatches, "matrix_root_equal": committed["matrix_root"] == current["matrix_root"],
            "disposition": "PASS_LOCAL_CANDIDATE" if not mismatches and committed["matrix_root"] == current["matrix_root"] else "FAIL",
            "authority_effect": "NONE"}
