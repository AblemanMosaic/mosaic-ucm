from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUT_DIR = DIST / "UCM-AMCAS-BASELINE-PARITY-C1-COURTHOUSE-HANDOFF"
OUT_ZIP = DIST / "UCM-AMCAS-BASELINE-PARITY-C1-COURTHOUSE-HANDOFF.zip"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
BOUNDARY = {
    "standing": "INFORMATION_ONLY",
    "authority_effect": "NONE",
    "real_a5": False,
    "g0": "CLOSED",
}


INPUTS = {
    "artifacts/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1.zip": (
        "dist/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1.zip",
        "a146ceeac25465c17471dafbb491cd7e32c468d87e669d0c6438fde7f3968748",
        "courthouse subject",
    ),
    "artifacts/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1-RECEIPT.json": (
        "dist/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1-RECEIPT.json",
        "65d6ba5451838cb5b4c3d2159056e1bfe22fa7067a4cabba2d0f0da055f7849b",
        "program receipt",
    ),
    "evidence/UCM-AMCAS-BASELINE-PARITY-POSITIVE-QUALIFICATION.json": (
        "dist/UCM-AMCAS-BASELINE-PARITY-POSITIVE-QUALIFICATION.json",
        "5888e90da0c0221ca4fee1e5767d869b21c47f89c01e54db770bc5805a8f8928",
        "positive qualification",
    ),
    "evidence/UCM-AMCAS-PARITY-C1-TIER1-EVIDENCE.zip": (
        "dist/UCM-AMCAS-PARITY-C1-OPERATOR-REVIEW/UCM-AMCAS-PARITY-C1-TIER1-EVIDENCE-cdadb5fd08460f0e.zip",
        "cdadb5fd08460f0e6ef5de5c4756fa206525b3f76993d2ffd6787ea23568263f",
        "operator-run Tier 1 evidence",
    ),
    "evidence/UCM-AMCAS-PARITY-C1-TIER1-OPERATOR-KIT.zip": (
        "dist/UCM-AMCAS-PARITY-C1-OPERATOR-REVIEW/UCM-AMCAS-PARITY-C1-TIER1-OPERATOR-KIT.zip",
        "c1952f4d0cd8c5b269c19008c6b3e45afa266c2980156d49de814e547c2aef54",
        "operator court reproduction input",
    ),
    "docs/AMCAS-UCM-BASELINE-ARCHITECTURE.md": (
        "docs/AMCAS-UCM-BASELINE-ARCHITECTURE.md", None, "subject orientation"
    ),
    "docs/AMCAS-UCM-PARITY-COURT.md": (
        "docs/AMCAS-UCM-PARITY-COURT.md", None, "court semantics"
    ),
    "docs/AMCAS-UCM-JOINT-REVIEW-WORK-ORDER.md": (
        "docs/AMCAS-UCM-JOINT-REVIEW-WORK-ORDER.md", None, "review boundary"
    ),
    "docs/COURTHOUSE-VNEXT-WORKFLOW-IR.md": (
        "docs/COURTHOUSE-VNEXT-WORKFLOW-IR.md", None, "courthouse adapter boundary"
    ),
    "spec/UCM-AOK-VNEXT-WORKFLOW-IR-CONTRACT.json": (
        "spec/UCM-AOK-VNEXT-WORKFLOW-IR-CONTRACT.json", None, "Workflow IR protocol"
    ),
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def rooted(body: dict, field: str) -> dict:
    return {**body, field: sha256(canonical_bytes(body))}


def read_json(raw: bytes) -> dict:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key}")
            out[key] = value
        return out
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    if type(value) is not dict:
        raise ValueError("JSON root must be an object")
    return value


def zip_members(raw: bytes) -> dict[str, bytes]:
    from io import BytesIO
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        names = zf.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate ZIP member")
        return {name: zf.read(name) for name in names}


def verify_nested_manifest(raw: bytes) -> dict:
    members = zip_members(raw)
    manifest = read_json(members["MANIFEST.json"])
    rows = manifest["files"]
    expected = {row["path"] for row in rows} | {"MANIFEST.json"}
    if set(members) != expected:
        raise ValueError("nested archive member set mismatch")
    for row in rows:
        item = members[row["path"]]
        if len(item) != row["bytes"] or sha256(item) != row["sha256"]:
            raise ValueError(f"nested archive drift: {row['path']}")
    body = {key: value for key, value in manifest.items() if key != "manifest_root"}
    if manifest["manifest_root"] != sha256(canonical_bytes(body)):
        raise ValueError("nested manifest root mismatch")
    return manifest


VERIFY_SOURCE = r'''from __future__ import annotations
import hashlib,json,sys,zipfile
from io import BytesIO
from pathlib import Path

def cb(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def h(b): return hashlib.sha256(b).hexdigest()
def loads(b):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d: raise ValueError("duplicate JSON key: "+k)
            d[k]=v
        return d
    v=json.loads(b,object_pairs_hook=pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    if type(v) is not dict: raise ValueError("JSON root must be an object")
    return v
def archive(raw):
    with zipfile.ZipFile(BytesIO(raw)) as z:
        ns=z.namelist()
        if len(ns)!=len(set(ns)): raise ValueError("duplicate ZIP member")
        return {n:z.read(n) for n in ns}
def source(path):
    p=Path(path)
    if p.is_dir(): return {q.relative_to(p).as_posix():q.read_bytes() for q in p.rglob("*") if q.is_file()}
    return archive(p.read_bytes())
def root_ok(o,key):
    body={k:v for k,v in o.items() if k!=key}
    return o.get(key)==h(cb(body))
def nested(raw):
    m=archive(raw); j=loads(m["MANIFEST.json"]); rows=j["files"]
    if set(m)!={r["path"] for r in rows}|{"MANIFEST.json"}: raise ValueError("nested member set mismatch")
    for r in rows:
        b=m[r["path"]]
        if len(b)!=r["bytes"] or h(b)!=r["sha256"]: raise ValueError("nested drift: "+r["path"])
    if not root_ok(j,"manifest_root"): raise ValueError("nested manifest root mismatch")
    return j,m
def main():
    target=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
    m=source(target); j=loads(m["MANIFEST.json"]); rows=j["files"]
    if set(m)!={r["path"] for r in rows}|{"MANIFEST.json"}: raise ValueError("handoff member set mismatch")
    for r in rows:
        b=m[r["path"]]
        if len(b)!=r["bytes"] or h(b)!=r["sha256"]: raise ValueError("handoff drift: "+r["path"])
    if not root_ok(j,"manifest_root"): raise ValueError("handoff manifest root mismatch")
    for key,value in {"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}.items():
        if j.get(key)!=value: raise ValueError("authority ceiling mismatch: "+key)
    intake=loads(m["COURTHOUSE-INTAKE.json"])
    if not root_ok(intake,"intake_root"): raise ValueError("intake root mismatch")
    notes=loads(m["EVIDENCE-CORRESPONDENCE.json"])
    if not root_ok(notes,"correspondence_root"): raise ValueError("correspondence root mismatch")
    paths=intake["artifacts"]
    for name,record in paths.items():
        if h(m[name])!=record["sha256"]: raise ValueError("intake artifact mismatch: "+name)
    receipt=loads(m["artifacts/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1-RECEIPT.json"])
    if not root_ok(receipt,"receipt_root"): raise ValueError("program receipt root mismatch")
    if receipt["archive_sha256"]!=h(m["artifacts/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1.zip"]): raise ValueError("program archive mismatch")
    nested(m["artifacts/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1.zip"])
    q=loads(m["evidence/UCM-AMCAS-BASELINE-PARITY-POSITIVE-QUALIFICATION.json"])
    if not root_ok(q,"qualification_root") or q["status"]!="PASS" or q["failures"] or q["errors"] or q["skips"]: raise ValueError("qualification invalid")
    evj,evm=nested(m["evidence/UCM-AMCAS-PARITY-C1-TIER1-EVIDENCE.zip"])
    result=loads(evm["TIER1-RESULT.json"])
    if result["status"]!="PASS" or result["failed"]!=0 or len(result["cases"])!=18: raise ValueError("Tier 1 result invalid")
    if result["court_root"]!="657fbfbaecddbab61128c198bd981c7fa0ca3ac276b169130544adfb6c759ecb": raise ValueError("Tier 1 court root mismatch")
    nested(m["evidence/UCM-AMCAS-PARITY-C1-TIER1-OPERATOR-KIT.zip"])
    print(json.dumps({"status":"PASS","handoff_root":j["manifest_root"],"program_sha256":receipt["archive_sha256"],"qualification_root":q["qualification_root"],"tier1_court_root":result["court_root"],"standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"},sort_keys=True))
    return 0
if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status":"REFUSED","reason":str(exc)},sort_keys=True),file=sys.stderr)
        raise SystemExit(2)
'''.replace("\n", "\r\n").encode()


RUN_VERIFY = b'''@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\nset "PYTHON="\r\nfor %%P in ("%LocalAppData%\\Programs\\Python\\Python313\\python.exe" "%LocalAppData%\\Programs\\Python\\Python312\\python.exe") do if not defined PYTHON if exist "%%~P" set "PYTHON=%%~P"\r\nif not defined PYTHON where python >nul 2>nul && set "PYTHON=python"\r\nif not defined PYTHON (echo REFUSED: Python 3.12 or 3.13 is required.& exit /b 2)\r\n"%PYTHON%" VERIFY.py\r\nset "RC=%ERRORLEVEL%"\r\nif "%RC%"=="0" (echo PASS - exact courthouse handoff verified.) else (echo REFUSED - handoff verification failed.)\r\nexit /b %RC%\r\n'''


START_HERE = b'''# UCM AMCAS Baseline and Parity Program C1 - Courthouse Handoff\n\n1. Extract this archive without changing its layout.\n2. Run `python VERIFY.py` or double-click `RUN-VERIFY.cmd` on Windows.\n3. Read `COURTHOUSE-INTAKE.json` and `docs/COURTHOUSE-VNEXT-WORKFLOW-IR.md`.\n4. Treat the nested program ZIP as the exact subject and the two evidence records as bounded evidence.\n5. Orient through the installed courthouse and current lattice before any filing, execution, admission, or authority decision.\n\nThis package is intake material only. It is INFORMATION_ONLY, has authority effect NONE, keeps real A5 false, and keeps G0 closed. It does not prove that a Courthouse vNext adapter is installed and does not grant permission to execute applications.\n'''


def make_zip(path: Path, payloads: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            zf.writestr(info, payloads[name])


def build_payloads() -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}
    artifacts = {}
    boundary_artifacts = []
    for destination, (source, expected, required_by) in INPUTS.items():
        raw = (ROOT / source).read_bytes()
        actual = sha256(raw)
        if expected is not None and actual != expected:
            raise ValueError(f"input drift: {source}: {actual}")
        payloads[destination] = raw
        artifacts[destination] = {"sha256": actual, "bytes": len(raw), "role": required_by}
        boundary_artifacts.append({
            "source_path": source,
            "destination_path": destination,
            "sha256": actual,
            "required_by": required_by,
        })

    program = payloads["artifacts/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1.zip"]
    program_manifest = verify_nested_manifest(program)
    receipt = read_json(payloads["artifacts/UCM-AMCAS-BASELINE-PARITY-PROGRAM-C1-RECEIPT.json"])
    if receipt["archive_sha256"] != sha256(program):
        raise ValueError("receipt does not bind program archive")
    if receipt["receipt_root"] != sha256(canonical_bytes({k: v for k, v in receipt.items() if k != "receipt_root"})):
        raise ValueError("receipt root mismatch")
    qualification = read_json(payloads["evidence/UCM-AMCAS-BASELINE-PARITY-POSITIVE-QUALIFICATION.json"])
    if qualification["qualification_root"] != sha256(canonical_bytes({k: v for k, v in qualification.items() if k != "qualification_root"})):
        raise ValueError("qualification root mismatch")
    evidence_members = zip_members(payloads["evidence/UCM-AMCAS-PARITY-C1-TIER1-EVIDENCE.zip"])
    tier1 = read_json(evidence_members["TIER1-RESULT.json"])
    if tier1["status"] != "PASS" or tier1["failed"] != 0 or len(tier1["cases"]) != 18:
        raise ValueError("Tier 1 evidence is not a clean 18-case PASS")
    if tier1["court_root"] != "657fbfbaecddbab61128c198bd981c7fa0ca3ac276b169130544adfb6c759ecb":
        raise ValueError("Tier 1 court root drift")
    verify_nested_manifest(payloads["evidence/UCM-AMCAS-PARITY-C1-TIER1-EVIDENCE.zip"])
    verify_nested_manifest(payloads["evidence/UCM-AMCAS-PARITY-C1-TIER1-OPERATOR-KIT.zip"])

    intake_body = {
        "schema": "mosaic.ucm.amcas-parity-courthouse-intake.v0.1",
        "purpose": "COURTHOUSE_VNEXT_WORKFLOW_IR_INTAKE",
        "subject": {
            "program_sha256": sha256(program),
            "program_manifest_root": program_manifest["manifest_root"],
            "program_receipt_root": receipt["receipt_root"],
            "amcas_registry_root": receipt["amcas_registry_root"],
            "coverage_root": receipt["coverage_root"],
            "parity_court_root": receipt["parity_court_root"],
            "fixed_denominator": receipt["fixed_denominator"],
        },
        "evidence": {
            "positive_qualification_root": qualification["qualification_root"],
            "positive_tests": qualification["tests_run"],
            "operator_tier1_evidence_sha256": artifacts["evidence/UCM-AMCAS-PARITY-C1-TIER1-EVIDENCE.zip"]["sha256"],
            "operator_tier1_court_root": tier1["court_root"],
            "operator_tier1_cases": len(tier1["cases"]),
            "operator_tier1_status": tier1["status"],
            "independent_verdict": "NOT_INCLUDED",
        },
        "workflow_ir": {
            "adapter_status": "INSTALLATION_NOT_ASSERTED",
            "orientation_required": True,
            "execution_requested": False,
            "filing_requested": False,
        },
        "artifacts": artifacts,
        **BOUNDARY,
    }
    payloads["COURTHOUSE-INTAKE.json"] = canonical_bytes(rooted(intake_body, "intake_root"))

    correspondence_body = {
        "schema": "mosaic.ucm.amcas-parity-evidence-correspondence.v0.1",
        "program_receipt_predates_operator_tier1": True,
        "program_receipt_operator_tier1_executed": receipt["operator_tier1_executed"],
        "later_operator_tier1_evidence_status": tier1["status"],
        "later_operator_tier1_evidence_sha256": artifacts["evidence/UCM-AMCAS-PARITY-C1-TIER1-EVIDENCE.zip"]["sha256"],
        "observatory_projection_difference": {
            "program_observatory_root": receipt["portfolio_observatory_root"],
            "positive_qualification_observatory_root": qualification["portfolio_observatory_root"],
            "reason": "The packaged observatory includes the existing semantic-consolidation root; the positive qualification's observatory projection used an empty consolidation-root set.",
            "shared_amcas_registry_root": receipt["amcas_registry_root"],
            "shared_coverage_root": receipt["coverage_root"],
            "shared_parity_court_root": receipt["parity_court_root"],
        },
        "claim": "DISCLOSURE_ONLY_NO_AUTHORITY_EFFECT",
        **BOUNDARY,
    }
    payloads["EVIDENCE-CORRESPONDENCE.json"] = canonical_bytes(rooted(correspondence_body, "correspondence_root"))
    payloads["START-HERE.md"] = START_HERE
    payloads["VERIFY.py"] = VERIFY_SOURCE
    payloads["RUN-VERIFY.cmd"] = RUN_VERIFY
    payloads["provenance/HANDOFF-BUILDER.py"] = Path(__file__).read_bytes()

    for destination, required_by in {
        "START-HERE.md": "operator orientation",
        "COURTHOUSE-INTAKE.json": "courthouse intake",
        "EVIDENCE-CORRESPONDENCE.json": "cross-record disclosure",
        "VERIFY.py": "portable verifier",
        "RUN-VERIFY.cmd": "Windows verification entrypoint",
        "provenance/HANDOFF-BUILDER.py": "reproducibility",
    }.items():
        boundary_artifacts.append({
            "source_path": "generated:" + destination,
            "destination_path": destination,
            "sha256": sha256(payloads[destination]),
            "required_by": required_by,
        })
    boundary = {
        "schema": "codex.exact-artifact-boundary.v1",
        "boundary_id": "ucm-amcas-parity-c1-to-courthouse-vnext",
        "artifacts": sorted(boundary_artifacts, key=lambda row: row["destination_path"]),
        "runner_required_paths": sorted([row["destination_path"] for row in boundary_artifacts] + ["MANIFEST.json", "EXACT-ARTIFACT-BOUNDARY.json"]),
        "allow_extra_artifacts": False,
        "policy": {
            "maximum_transfers": 1,
            "maximum_invocations": 1,
            "maximum_retries": 0,
            "preserve_prior_custody": True,
            "terminal_capture": ["stdout", "stderr", "exit_code", "terminal_receipt"],
            "excluded_effects": ["COURTHOUSE_FILING", "APPLICATION_EXECUTION", "ADMISSION", "AUTHORITY_GRANT"],
        },
        **BOUNDARY,
    }
    payloads["EXACT-ARTIFACT-BOUNDARY.json"] = canonical_bytes(boundary)

    rows = [
        {"path": path, "bytes": len(raw), "sha256": sha256(raw)}
        for path, raw in sorted(payloads.items())
    ]
    manifest_body = {
        "schema": "mosaic.ucm.amcas-parity-courthouse-handoff.v0.1",
        "artifact_role": "UCM_AMCAS_BASELINE_PARITY_COURTHOUSE_HANDOFF",
        "files": rows,
        "file_count": len(rows),
        **BOUNDARY,
    }
    payloads["MANIFEST.json"] = canonical_bytes(rooted(manifest_body, "manifest_root"))
    return payloads


def main() -> int:
    payloads = build_payloads()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.rglob("*"):
        if old.is_file():
            old.unlink()
    for name, raw in payloads.items():
        path = OUT_DIR / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    with tempfile.TemporaryDirectory(prefix="ucm-amcas-courthouse-") as tmp:
        first = Path(tmp) / "first.zip"
        second = Path(tmp) / "second.zip"
        make_zip(first, payloads)
        make_zip(second, payloads)
        if first.read_bytes() != second.read_bytes():
            raise ValueError("deterministic rebuild mismatch")
        shutil.copyfile(first, OUT_ZIP)
    print(json.dumps({
        "status": "PASS",
        "archive": str(OUT_ZIP),
        "archive_sha256": sha256(OUT_ZIP.read_bytes()),
        "archive_bytes": OUT_ZIP.stat().st_size,
        "manifest_root": read_json(payloads["MANIFEST.json"])["manifest_root"],
        **BOUNDARY,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
