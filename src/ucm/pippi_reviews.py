"""Deterministic P/PPI review envelopes and local review custody.

P/PPI owns exact delivery, deterministic reconstruction, return binding, and
publication holds.  The subject application continues to own its courts and
the meaning of its verdicts.  Running a bundled reviewer is an explicit local
effect and is never represented as an OS sandbox or independent verdict.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from typing import Any, Callable
import zipfile

from uclop.canonical import canonical_bytes, root, strict_loads

from .pippi_global import BOUNDARY, HubRefusal, PippiHub, validate_project
from .pippi_integrations import archive_local, build_courthouse_work_order, build_publication_plan


SPEC_SCHEMA = "mosaic.ucm.pippi-review-envelope-spec.v0.1"
ENVELOPE_SCHEMA = "mosaic.ucm.pippi-review-envelope.v0.1"
CONTENTS_SCHEMA = "mosaic.ucm.pippi-review-envelope-contents.v0.1"
RECORD_SCHEMA = "mosaic.ucm.pippi-review-record.v0.1"
RETURN_SCHEMA = "mosaic.ucm.pippi-review-return.v0.1"
RETURN_CONTENTS_SCHEMA = "mosaic.ucm.pippi-review-return-contents.v0.1"
RUN_SCHEMA = "mosaic.ucm.pippi-review-local-run.v0.1"
OPERATOR_KIT_SCHEMA = "mosaic.ucm.pippi-operator-review-kit.v0.1"
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)
RESERVED = {"REVIEW-ENVELOPE.json", "REVIEW-CONTENTS.json", "VERIFY.py",
            "REVIEW-RETURN.json", "REVIEW-RETURN-CONTENTS.json", "RUN-RESULT.json"}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_sha(value: Any, code: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise HubRefusal(code)
    return value


def _relative(value: Any, code: str, *, allow_reserved: bool = False) -> str:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        raise HubRefusal(code)
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise HubRefusal(code)
    normalized = path.as_posix()
    if not allow_reserved and normalized in RESERVED:
        raise HubRefusal(code)
    return normalized


def _identifier(value: Any, code: str) -> str:
    if (not isinstance(value, str) or not value or value != value.strip() or len(value) > 192 or
            not all(ch.isalnum() or ch in "._:-/@+" for ch in value)):
        raise HubRefusal(code)
    return value


def build_operator_kit_contract(*, subject_id: str, revision: str,
                                members: list[dict[str, Any]],
                                runtime_sha256: str,
                                qualification_sha256: str,
                                cold_boot_sha256: str,
                                runner_path: str,
                                evidence_glob: str) -> dict[str, Any]:
    """Compile the reusable, non-executing P/PPI operator-kit envelope.

    Subject-specific cases remain in the runner.  This contract governs the
    recurring custody, authorship, live-progress, evidence, and cleanup shape.
    """
    _identifier(subject_id, "PIPPI_OPERATOR_KIT_SUBJECT_INVALID")
    _identifier(revision, "PIPPI_OPERATOR_KIT_REVISION_INVALID")
    for value in (runtime_sha256, qualification_sha256, cold_boot_sha256):
        _require_sha(value, "PIPPI_OPERATOR_KIT_PIN_INVALID")
    runner_path = _relative(runner_path, "PIPPI_OPERATOR_KIT_RUNNER_INVALID")
    if not isinstance(evidence_glob, str) or not evidence_glob or "/" in evidence_glob or "\\" in evidence_glob:
        raise HubRefusal("PIPPI_OPERATOR_KIT_EVIDENCE_GLOB_INVALID")
    normalized = []
    for row in members:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "bytes", "role"}:
            raise HubRefusal("PIPPI_OPERATOR_KIT_MEMBERS_INVALID")
        normalized.append({"path": _relative(row["path"], "PIPPI_OPERATOR_KIT_MEMBER_PATH_INVALID"),
                           "sha256": _require_sha(row["sha256"], "PIPPI_OPERATOR_KIT_MEMBER_HASH_INVALID"),
                           "bytes": row["bytes"],
                           "role": _identifier(row["role"], "PIPPI_OPERATOR_KIT_MEMBER_ROLE_INVALID")})
        if not isinstance(row["bytes"], int) or row["bytes"] < 0:
            raise HubRefusal("PIPPI_OPERATOR_KIT_MEMBER_BYTES_INVALID")
    if normalized != sorted(normalized, key=lambda row: row["path"]) or len({row["path"] for row in normalized}) != len(normalized):
        raise HubRefusal("PIPPI_OPERATOR_KIT_MEMBERS_INVALID")
    if runner_path not in {row["path"] for row in normalized}:
        raise HubRefusal("PIPPI_OPERATOR_KIT_RUNNER_MISSING")
    body = {
        "schema": OPERATOR_KIT_SCHEMA,
        "subject_id": subject_id,
        "revision": revision,
        "runtime_sha256": runtime_sha256,
        "qualification_sha256": qualification_sha256,
        "cold_boot_sha256": cold_boot_sha256,
        "members": normalized,
        "member_count": len(normalized),
        "runner_path": runner_path,
        "evidence_glob": evidence_glob,
        "launcher_contract": {
            "phases": ["VERIFY_KIT", "EXTRACT_DISPOSABLE", "RUN_WITH_LIVE_PROGRESS",
                       "PRESERVE_EVIDENCE", "REPORT_STATUS", "REMOVE_DISPOSABLE"],
            "live_progress_required": True,
            "evidence_preserved_before_status": True,
            "disposable_workspace_required": True,
            "cleanup_required": True,
            "interactive_pause_after_terminal_status": True,
        },
        "builder_authored": True,
        "operator_executed": False,
        "tier1_executed": False,
        **BOUNDARY,
    }
    return {**body, "operator_kit_root": root(body)}


def validate_operator_kit_contract(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != OPERATOR_KIT_SCHEMA:
        raise HubRefusal("PIPPI_OPERATOR_KIT_CONTRACT_INVALID")
    expected = build_operator_kit_contract(
        subject_id=value.get("subject_id"), revision=value.get("revision"),
        members=value.get("members"), runtime_sha256=value.get("runtime_sha256"),
        qualification_sha256=value.get("qualification_sha256"),
        cold_boot_sha256=value.get("cold_boot_sha256"),
        runner_path=value.get("runner_path"), evidence_glob=value.get("evidence_glob"))
    if value != expected:
        raise HubRefusal("PIPPI_OPERATOR_KIT_CONTRACT_INVALID")
    return deepcopy(value)


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    if len(members) != len(set(members)):
        raise HubRefusal("PIPPI_REVIEW_MEMBER_DUPLICATE")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED, strict_timestamps=True) as archive:
        for name in sorted(members):
            _relative(name, "PIPPI_REVIEW_MEMBER_PATH_INVALID", allow_reserved=True)
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.flag_bits = 0x800
            archive.writestr(info, members[name])
    return output.getvalue()


def _closed_inventory(archive: zipfile.ZipFile, *, metadata: set[str], schema: str) -> dict[str, Any]:
    infos = archive.infolist()
    names = [row.filename for row in infos]
    if names != sorted(names) or len(names) != len(set(names)):
        raise HubRefusal("PIPPI_REVIEW_ARCHIVE_FORM_INVALID")
    for info in infos:
        if (info.date_time != FIXED_ZIP_TIME or info.compress_type != zipfile.ZIP_STORED or
                info.is_dir() or _relative(info.filename, "PIPPI_REVIEW_MEMBER_PATH_INVALID", allow_reserved=True) != info.filename):
            raise HubRefusal("PIPPI_REVIEW_ARCHIVE_FORM_INVALID")
    rows = []
    for name in names:
        if name not in metadata:
            raw = archive.read(name)
            rows.append({"path": name, "bytes": len(raw), "sha256": _sha(raw)})
    body = {"schema": schema, "files": rows}
    return {**body, "contents_root": root(body)}


# The envelope carries this verifier so custody can be checked without importing
# P/PPI or subject code.  It intentionally verifies delivery, not domain meaning.
STANDALONE_VERIFY_SOURCE = r'''from __future__ import annotations
import hashlib,json,sys,zipfile
from pathlib import PurePosixPath
FIXED=(2026,1,1,0,0,0)
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
def h(b):return hashlib.sha256(b).hexdigest()
def rooted(v):return h(canon(v))
def load(raw):
 def pairs(rows):
  out={}
  for k,v in rows:
   if k in out:raise ValueError("DUPLICATE_JSON_KEY")
   out[k]=v
  return out
 return json.loads(raw.decode("utf-8"),object_pairs_hook=pairs,parse_float=lambda x:(_ for _ in ()).throw(ValueError("FLOAT_NOT_ALLOWED")),parse_constant=lambda x:(_ for _ in ()).throw(ValueError("NON_FINITE")))
def main():
 if len(sys.argv)!=3:raise SystemExit("usage: VERIFY.py ENVELOPE.zip EXPECTED_SHA256")
 p=sys.argv[1];expected_sha=sys.argv[2]
 raw=open(p,"rb").read()
 if len(expected_sha)!=64 or h(raw)!=expected_sha:raise ValueError("ARCHIVE_HASH_MISMATCH")
 with zipfile.ZipFile(p,"r") as z:
  infos=z.infolist();names=[i.filename for i in infos]
  if names!=sorted(names) or len(names)!=len(set(names)):raise ValueError("ARCHIVE_FORM_INVALID")
  for i in infos:
   q=PurePosixPath(i.filename)
   if i.date_time!=FIXED or i.compress_type!=zipfile.ZIP_STORED or i.is_dir() or q.is_absolute() or ".." in q.parts or "\\" in i.filename:raise ValueError("ARCHIVE_FORM_INVALID")
  expected={"REVIEW-CONTENTS.json","REVIEW-ENVELOPE.json","VERIFY.py"}
  c=load(z.read("REVIEW-CONTENTS.json"));e=load(z.read("REVIEW-ENVELOPE.json"))
  body={k:v for k,v in c.items() if k!="contents_root"}
  if c.get("contents_root")!=rooted(body):raise ValueError("CONTENTS_ROOT_INVALID")
  for row in c["files"]:
   expected.add(row["path"]);raw=z.read(row["path"])
   if len(raw)!=row["bytes"] or h(raw)!=row["sha256"]:raise ValueError("MEMBER_INVALID")
  eb={k:v for k,v in e.items() if k!="envelope_root"}
  subjects=[row for row in c["files"] if row.get("role")=="SUBJECT"]
  sr=rooted({"schema":"mosaic.ucm.pippi-review-subject-manifest.v0.1","files":subjects})
  if e.get("envelope_root")!=rooted(eb) or e.get("contents_root")!=c["contents_root"] or e.get("subject_manifest_root")!=sr or set(names)!=expected:raise ValueError("ENVELOPE_INVALID")
 print(json.dumps({"status":"PASS","envelope_root":e["envelope_root"],"archive_sha256":expected_sha,"external_pin_checked":True,"authority_effect":"NONE"},sort_keys=True,separators=(",",":")))
if __name__=="__main__":raise SystemExit(main())
'''.encode("utf-8")


def validate_review_spec(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != SPEC_SCHEMA:
        raise HubRefusal("PIPPI_REVIEW_SPEC_INVALID")
    required = {"schema", "review_id", "review_class", "subject_role", "declared_subject_root",
                "members", "runner", "limitations", "independent_review_required"}
    if set(value) != required:
        raise HubRefusal("PIPPI_REVIEW_SPEC_INVALID")
    _identifier(value["review_id"], "PIPPI_REVIEW_ID_INVALID")
    _identifier(value["review_class"], "PIPPI_REVIEW_CLASS_INVALID")
    _identifier(value["subject_role"], "PIPPI_REVIEW_SUBJECT_ROLE_INVALID")
    if value["declared_subject_root"] is not None:
        _require_sha(value["declared_subject_root"], "PIPPI_REVIEW_SUBJECT_ROOT_INVALID")
    if not isinstance(value["members"], list) or not value["members"]:
        raise HubRefusal("PIPPI_REVIEW_MEMBERS_INVALID")
    paths = []
    for row in value["members"]:
        if not isinstance(row, dict) or set(row) != {"source", "path", "role"}:
            raise HubRefusal("PIPPI_REVIEW_MEMBERS_INVALID")
        paths.append(_relative(row["path"], "PIPPI_REVIEW_MEMBER_PATH_INVALID"))
        _identifier(row["role"], "PIPPI_REVIEW_MEMBER_ROLE_INVALID")
        if not isinstance(row["source"], str) or not row["source"]:
            raise HubRefusal("PIPPI_REVIEW_MEMBER_SOURCE_INVALID")
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise HubRefusal("PIPPI_REVIEW_MEMBERS_INVALID")
    runner = value["runner"]
    if (not isinstance(runner, dict) or set(runner) != {"command", "required_paths", "expected_outputs", "timeout_seconds"} or
            not isinstance(runner["command"], list) or not runner["command"] or runner["command"][0] != "{PYTHON}" or
            not all(isinstance(item, str) and item for item in runner["command"]) or
            not isinstance(runner["timeout_seconds"], int) or not 1 <= runner["timeout_seconds"] <= 86400):
        raise HubRefusal("PIPPI_REVIEW_RUNNER_INVALID")
    for key in ("required_paths", "expected_outputs"):
        rows = runner[key]
        if not isinstance(rows, list) or rows != sorted(set(rows)):
            raise HubRefusal("PIPPI_REVIEW_RUNNER_INVALID")
        for item in rows:
            _relative(item, "PIPPI_REVIEW_RUNNER_PATH_INVALID")
    if not isinstance(value["limitations"], list) or value["limitations"] != sorted(set(value["limitations"])):
        raise HubRefusal("PIPPI_REVIEW_LIMITATIONS_INVALID")
    if type(value["independent_review_required"]) is not bool:
        raise HubRefusal("PIPPI_REVIEW_SPEC_INVALID")
    return deepcopy(value)


def validate_review_envelope(value: Any) -> dict[str, Any]:
    fields = {"schema", "review_id", "review_class", "project_id", "project_root", "subject_role",
              "declared_subject_root", "subject_manifest_root", "contents_root", "runner", "limitations",
              "independent_review_required", "court_owner", "pippi_role", "execution_boundary",
              "publication_authorized", "standing", "authority_effect", "real_a5", "g0", "envelope_root"}
    if not isinstance(value, dict) or set(value) != fields or value.get("schema") != ENVELOPE_SCHEMA:
        raise HubRefusal("PIPPI_REVIEW_ENVELOPE_INVALID")
    for key, code in (("review_id", "PIPPI_REVIEW_ID_INVALID"),
                      ("review_class", "PIPPI_REVIEW_CLASS_INVALID"),
                      ("project_id", "PIPPI_PROJECT_ID_INVALID"),
                      ("subject_role", "PIPPI_REVIEW_SUBJECT_ROLE_INVALID")):
        _identifier(value[key], code)
    for key in ("project_root", "subject_manifest_root", "contents_root", "envelope_root"):
        _require_sha(value[key], "PIPPI_REVIEW_ENVELOPE_INVALID")
    if value["declared_subject_root"] is not None:
        _require_sha(value["declared_subject_root"], "PIPPI_REVIEW_SUBJECT_ROOT_INVALID")
    runner=value["runner"]
    if (not isinstance(runner,dict) or set(runner)!={"command","required_paths","expected_outputs","timeout_seconds"} or
            not isinstance(runner["command"],list) or not runner["command"] or runner["command"][0]!="{PYTHON}" or
            not all(isinstance(item,str) and item for item in runner["command"]) or
            runner["required_paths"]!=sorted(set(runner["required_paths"])) or
            runner["expected_outputs"]!=sorted(set(runner["expected_outputs"])) or
            not isinstance(runner["timeout_seconds"],int) or not 1<=runner["timeout_seconds"]<=86400):
        raise HubRefusal("PIPPI_REVIEW_ENVELOPE_INVALID")
    for item in runner["required_paths"]+runner["expected_outputs"]:
        _relative(item,"PIPPI_REVIEW_RUNNER_PATH_INVALID")
    body={key:deepcopy(row) for key,row in value.items() if key!="envelope_root"}
    if (value["envelope_root"]!=root(body) or value["limitations"]!=sorted(set(value["limitations"])) or
            type(value["independent_review_required"]) is not bool or value["court_owner"]!="SUBJECT_APPLICATION" or
            value["pippi_role"]!="EXACT_CUSTODY_REPLAY_AND_RETURN_BINDING" or
            value["execution_boundary"]!="DISPOSABLE_WORKSPACE_NOT_OS_SANDBOX" or
            value["publication_authorized"] is not False or
            any(value.get(key)!=row for key,row in BOUNDARY.items())):
        raise HubRefusal("PIPPI_REVIEW_ENVELOPE_INVALID")
    return deepcopy(value)


def build_review_envelope(*, project: dict[str, Any], spec: dict[str, Any], spec_dir: Path,
                          output_path: Path) -> dict[str, Any]:
    project = validate_project(project)
    spec = validate_review_spec(spec)
    base = Path(spec_dir).resolve()
    members: dict[str, bytes] = {"VERIFY.py": STANDALONE_VERIFY_SOURCE}
    roles: dict[str, str] = {"VERIFY.py": "STANDALONE_VERIFIER"}
    for row in spec["members"]:
        source = (base / row["source"]).resolve()
        if not source.is_relative_to(base) or not source.is_file():
            raise HubRefusal("PIPPI_REVIEW_MEMBER_SOURCE_INVALID", row["source"])
        members[row["path"]] = source.read_bytes()
        roles[row["path"]] = row["role"]
    missing = sorted(set(spec["runner"]["required_paths"]) - set(members))
    if missing:
        raise HubRefusal("PIPPI_REVIEW_RUNNER_REQUIRED_PATH_MISSING", ",".join(missing))
    rows = [{"path": path, "role": roles[path], "bytes": len(raw), "sha256": _sha(raw)}
            for path, raw in sorted(members.items())]
    contents_body = {"schema": CONTENTS_SCHEMA, "files": rows}
    contents = {**contents_body, "contents_root": root(contents_body)}
    subject_rows = [row for row in rows if row["role"] == "SUBJECT"]
    subject_manifest_root = root({"schema": "mosaic.ucm.pippi-review-subject-manifest.v0.1",
                                  "files": subject_rows})
    envelope_body = {
        "schema": ENVELOPE_SCHEMA,
        "review_id": spec["review_id"],
        "review_class": spec["review_class"],
        "project_id": project["project_id"],
        "project_root": project["project_root"],
        "subject_role": spec["subject_role"],
        "declared_subject_root": spec["declared_subject_root"],
        "subject_manifest_root": subject_manifest_root,
        "contents_root": contents["contents_root"],
        "runner": deepcopy(spec["runner"]),
        "limitations": deepcopy(spec["limitations"]),
        "independent_review_required": spec["independent_review_required"],
        "court_owner": "SUBJECT_APPLICATION",
        "pippi_role": "EXACT_CUSTODY_REPLAY_AND_RETURN_BINDING",
        "execution_boundary": "DISPOSABLE_WORKSPACE_NOT_OS_SANDBOX",
        "publication_authorized": False,
        **BOUNDARY,
    }
    envelope = {**envelope_body, "envelope_root": root(envelope_body)}
    members["REVIEW-CONTENTS.json"] = canonical_bytes(contents) + b"\n"
    members["REVIEW-ENVELOPE.json"] = canonical_bytes(envelope) + b"\n"
    first = _zip_bytes(members)
    second = _zip_bytes(members)
    if first != second:
        raise HubRefusal("PIPPI_REVIEW_BUILD_NONDETERMINISTIC")
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = output.with_name(output.name + ".pending")
    with pending.open("wb") as stream:
        stream.write(first); stream.flush(); os.fsync(stream.fileno())
    os.replace(pending, output)
    return {"status": "PASS", "review_id": spec["review_id"], "envelope_root": envelope["envelope_root"],
            "subject_manifest_root": subject_manifest_root, "archive_sha256": _sha(first),
            "archive_bytes": len(first), "archive_path": str(output), **BOUNDARY}


def verify_review_envelope(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    target = Path(path).resolve()
    raw = target.read_bytes()
    digest=_sha(raw)
    if expected_sha256 is not None:
        _require_sha(expected_sha256,"PIPPI_REVIEW_EXPECTED_HASH_INVALID")
        if digest!=expected_sha256:raise HubRefusal("PIPPI_REVIEW_ARCHIVE_HASH_MISMATCH")
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            contents = strict_loads(archive.read("REVIEW-CONTENTS.json"))
            envelope = validate_review_envelope(strict_loads(archive.read("REVIEW-ENVELOPE.json")))
            observed = _closed_inventory(archive, metadata={"REVIEW-CONTENTS.json", "REVIEW-ENVELOPE.json"},
                                         schema=CONTENTS_SCHEMA)
            # Inventory includes VERIFY.py and every payload member.
            observed_rows = [{**row, "role": next((item["role"] for item in contents.get("files", [])
                                                    if item.get("path") == row["path"]), None)}
                             for row in observed["files"]]
            observed_body = {"schema": CONTENTS_SCHEMA, "files": observed_rows}
            if contents != {**observed_body, "contents_root": root(observed_body)}:
                raise HubRefusal("PIPPI_REVIEW_CONTENTS_INVALID")
            subject_rows = [row for row in contents["files"] if row["role"] == "SUBJECT"]
            subject_manifest_root = root({"schema": "mosaic.ucm.pippi-review-subject-manifest.v0.1",
                                          "files": subject_rows})
            if (envelope.get("contents_root") != contents["contents_root"] or
                    envelope.get("subject_manifest_root") != subject_manifest_root or
                    not any(row["role"]=="SUBJECT" for row in contents["files"])):
                raise HubRefusal("PIPPI_REVIEW_ENVELOPE_INVALID")
    except (KeyError, zipfile.BadZipFile, OSError, ValueError) as exc:
        if isinstance(exc, HubRefusal):
            raise
        raise HubRefusal("PIPPI_REVIEW_ARCHIVE_INVALID", type(exc).__name__) from exc
    return {"status": "PASS", "review_id": envelope["review_id"], "project_id": envelope["project_id"],
            "envelope_root": envelope["envelope_root"], "subject_manifest_root": envelope["subject_manifest_root"],
            "archive_sha256": digest, "archive_bytes": len(raw), "archive_path": str(target),
            "external_pin_checked": expected_sha256 is not None, **BOUNDARY}


def _run_members(output: Path) -> list[dict[str, Any]]:
    if not output.exists():
        return []
    rows = []
    for path in sorted((item for item in output.rglob("*") if item.is_file()),
                       key=lambda item: item.relative_to(output).as_posix()):
        relative = path.relative_to(output).as_posix()
        raw = path.read_bytes()
        rows.append({"path": relative, "bytes": len(raw), "sha256": _sha(raw)})
    return rows


def run_review_envelope(path: Path, evidence_path: Path, *, expected_sha256: str | None = None,
                        progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    def emit(phase: str, status: str) -> None:
        if progress:
            progress({"phase": phase, "status": status, **BOUNDARY})
    emit("VERIFY", "START")
    verification = verify_review_envelope(path,expected_sha256=expected_sha256)
    emit("VERIFY", "PASS")
    with zipfile.ZipFile(path, "r") as source:
        envelope = strict_loads(source.read("REVIEW-ENVELOPE.json"))
        with tempfile.TemporaryDirectory(prefix="pippi-review-") as temporary:
            workspace = Path(temporary).resolve()
            emit("EXTRACT", "START")
            source.extractall(workspace)
            emit("EXTRACT", "PASS")
            output = workspace / "review-output"
            output.mkdir()
            command = []
            for index, item in enumerate(envelope["runner"]["command"]):
                if item == "{PYTHON}":
                    command.append(sys.executable)
                elif item == "{OUTPUT_DIR}":
                    command.append(str(output))
                else:
                    if index == 0 or Path(item).is_absolute() or ".." in Path(item).parts:
                        raise HubRefusal("PIPPI_REVIEW_RUNNER_COMMAND_REFUSED")
                    command.append(item)
            emit("RUN", "START")
            try:
                completed = subprocess.run(command, cwd=workspace, check=False, capture_output=True,
                                           timeout=envelope["runner"]["timeout_seconds"])
            except subprocess.TimeoutExpired as exc:
                raise HubRefusal("PIPPI_REVIEW_RUNNER_TIMEOUT") from exc
            if len(completed.stdout) > 4 * 1024 * 1024 or len(completed.stderr) > 4 * 1024 * 1024:
                raise HubRefusal("PIPPI_REVIEW_RUNNER_OUTPUT_TOO_LARGE")
            expected = envelope["runner"]["expected_outputs"]
            missing = [name for name in expected if not (output / name).is_file()]
            run_status = "PASS" if completed.returncode == 0 and not missing else "REFUSED"
            emit("RUN", run_status)
            output_rows = _run_members(output)
            run_body = {"schema": RUN_SCHEMA, "review_id": envelope["review_id"],
                        "envelope_root": envelope["envelope_root"],
                        "envelope_sha256": verification["archive_sha256"],
                        "returncode": completed.returncode, "missing_expected_outputs": missing,
                        "outputs": output_rows, "runner_status": run_status,
                        "domain_verdict": "NOT_INTERPRETED_BY_PIPPI",
                        "execution_boundary": envelope["execution_boundary"], **BOUNDARY}
            run_result = {**run_body, "run_root": root(run_body)}
            evidence_members = {"RUN-RESULT.json": canonical_bytes(run_result) + b"\n",
                                "stdout.txt": completed.stdout, "stderr.txt": completed.stderr}
            for row in output_rows:
                evidence_members[f"outputs/{row['path']}"] = (output / row["path"]).read_bytes()
            evidence_raw = _zip_bytes(evidence_members)
            evidence = Path(evidence_path).resolve(); evidence.parent.mkdir(parents=True, exist_ok=True)
            pending = evidence.with_name(evidence.name + ".pending")
            with pending.open("wb") as stream:
                stream.write(evidence_raw); stream.flush(); os.fsync(stream.fileno())
            os.replace(pending, evidence)
            emit("SEAL", "PASS")
            return {"status": run_status, "review_id": envelope["review_id"], "run_root": run_result["run_root"],
                    "evidence_sha256": _sha(evidence_raw), "evidence_path": str(evidence),
                    "domain_verdict": "NOT_INTERPRETED_BY_PIPPI", **BOUNDARY}


def build_review_return(*, review_id: str, envelope_sha256: str, reviewer_identity_root: str,
                        reported_outcome: str, findings: list[dict[str, Any]], limitations: list[str],
                        evidence_files: list[dict[str, Any]]) -> dict[str, Any]:
    _identifier(review_id, "PIPPI_REVIEW_ID_INVALID")
    _require_sha(envelope_sha256, "PIPPI_REVIEW_ARCHIVE_HASH_INVALID")
    _require_sha(reviewer_identity_root, "PIPPI_REVIEWER_IDENTITY_ROOT_INVALID")
    _identifier(reported_outcome, "PIPPI_REVIEW_OUTCOME_INVALID")
    if limitations != sorted(set(limitations)) or not all(isinstance(row, dict) for row in findings):
        raise HubRefusal("PIPPI_REVIEW_RETURN_INVALID")
    contents_body = {"schema": RETURN_CONTENTS_SCHEMA, "files": evidence_files}
    contents_root = root(contents_body)
    body = {"schema": RETURN_SCHEMA, "review_id": review_id, "envelope_sha256": envelope_sha256,
            "reviewer_identity_root": reviewer_identity_root, "reported_outcome": reported_outcome,
            "findings": deepcopy(findings), "limitations": limitations, "evidence_contents_root": contents_root,
            "pippi_interpretation": "CUSTODY_ONLY_NOT_AUTHORITY", **BOUNDARY}
    return {**body, "return_root": root(body)}


def validate_review_return(value: Any) -> dict[str, Any]:
    fields={"schema","review_id","envelope_sha256","reviewer_identity_root","reported_outcome",
            "findings","limitations","evidence_contents_root","pippi_interpretation",
            "standing","authority_effect","real_a5","g0","return_root"}
    if not isinstance(value,dict) or set(value)!=fields or value.get("schema")!=RETURN_SCHEMA:
        raise HubRefusal("PIPPI_REVIEW_RETURN_INVALID")
    _identifier(value["review_id"],"PIPPI_REVIEW_ID_INVALID")
    _identifier(value["reported_outcome"],"PIPPI_REVIEW_OUTCOME_INVALID")
    for key in ("envelope_sha256","reviewer_identity_root","evidence_contents_root","return_root"):
        _require_sha(value[key],"PIPPI_REVIEW_RETURN_INVALID")
    body={key:deepcopy(row) for key,row in value.items() if key!="return_root"}
    if (value["return_root"]!=root(body) or not isinstance(value["findings"],list) or
            not all(isinstance(row,dict) for row in value["findings"]) or
            value["limitations"]!=sorted(set(value["limitations"])) or
            value["pippi_interpretation"]!="CUSTODY_ONLY_NOT_AUTHORITY" or
            any(value.get(key)!=row for key,row in BOUNDARY.items())):
        raise HubRefusal("PIPPI_REVIEW_RETURN_INVALID")
    return deepcopy(value)


def build_review_return_archive(*, review_id: str, envelope_sha256: str,
                                reviewer_identity_root: str, reported_outcome: str,
                                findings: list[dict[str, Any]], limitations: list[str],
                                evidence_members: list[dict[str, str]], source_dir: Path,
                                output_path: Path) -> dict[str, Any]:
    """Build a closed deterministic reviewer return without interpreting its verdict."""
    base = Path(source_dir).resolve()
    payload: dict[str, bytes] = {}
    for row in evidence_members:
        if not isinstance(row, dict) or set(row) != {"source", "path"}:
            raise HubRefusal("PIPPI_REVIEW_RETURN_MEMBERS_INVALID")
        name = _relative(row["path"], "PIPPI_REVIEW_RETURN_MEMBER_PATH_INVALID")
        source = (base / row["source"]).resolve()
        if not source.is_relative_to(base) or not source.is_file() or name in payload:
            raise HubRefusal("PIPPI_REVIEW_RETURN_MEMBERS_INVALID")
        payload[name] = source.read_bytes()
    rows = [{"path": name, "bytes": len(raw), "sha256": _sha(raw)} for name, raw in sorted(payload.items())]
    contents_body = {"schema": RETURN_CONTENTS_SCHEMA, "files": rows}
    contents = {**contents_body, "contents_root": root(contents_body)}
    returned = build_review_return(review_id=review_id, envelope_sha256=envelope_sha256,
        reviewer_identity_root=reviewer_identity_root, reported_outcome=reported_outcome,
        findings=findings, limitations=limitations, evidence_files=rows)
    payload["REVIEW-RETURN-CONTENTS.json"] = canonical_bytes(contents) + b"\n"
    payload["REVIEW-RETURN.json"] = canonical_bytes(returned) + b"\n"
    first = _zip_bytes(payload); second = _zip_bytes(payload)
    if first != second:
        raise HubRefusal("PIPPI_REVIEW_RETURN_BUILD_NONDETERMINISTIC")
    output = Path(output_path).resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    pending = output.with_name(output.name + ".pending")
    with pending.open("wb") as stream:
        stream.write(first); stream.flush(); os.fsync(stream.fileno())
    os.replace(pending, output)
    return {"status": "PASS", "review_id": review_id, "return_root": returned["return_root"],
            "archive_sha256": _sha(first), "archive_path": str(output), **BOUNDARY}


class ReviewStore:
    """Local review state derived from exact envelopes and returned archives."""
    def __init__(self, hub: PippiHub) -> None:
        self.hub = hub
        self.root = hub.root / "reviews"

    def _path(self, project_id: str, review_id: str) -> Path:
        _identifier(project_id, "PIPPI_PROJECT_ID_INVALID")
        _identifier(review_id, "PIPPI_REVIEW_ID_INVALID")
        return self.root / project_id / f"{review_id}.json"

    @staticmethod
    def _atomic(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        pending = path.with_name(path.name + ".pending")
        with pending.open("wb") as stream:
            stream.write(canonical_bytes(value) + b"\n"); stream.flush(); os.fsync(stream.fileno())
        os.replace(pending, path)

    def register(self, *, project_id: str, envelope_path: Path) -> dict[str, Any]:
        project = self.hub.get_project(project_id)
        verified = verify_review_envelope(envelope_path)
        if verified["project_id"] != project_id:
            raise HubRefusal("PIPPI_REVIEW_PROJECT_MISMATCH")
        with zipfile.ZipFile(envelope_path, "r") as archive:
            envelope = strict_loads(archive.read("REVIEW-ENVELOPE.json"))
        archived_sha,archived_path=archive_local(data_root=self.hub.root,data=Path(envelope_path).read_bytes())
        if archived_sha!=verified["archive_sha256"]:raise HubRefusal("PIPPI_REVIEW_ARCHIVE_HASH_MISMATCH")
        path = self._path(project_id, envelope["review_id"])
        if path.exists():
            raise HubRefusal("PIPPI_REVIEW_EXISTS")
        body = {"schema": RECORD_SCHEMA, "project_id": project_id, "project_root": project["project_root"],
                "review_id": envelope["review_id"], "review_class": envelope["review_class"],
                "subject_role": envelope["subject_role"], "subject_manifest_root": envelope["subject_manifest_root"],
                "declared_subject_root": envelope["declared_subject_root"], "envelope_root": envelope["envelope_root"],
                "envelope_sha256": verified["archive_sha256"], "envelope_path": str(archived_path.resolve()),
                "status": "PACKAGED", "courthouse_work_order_root": None, "return_sha256": None,
                "return_path": None, "return_root": None, "reported_outcome": None, "publication_plan_root": None,
                "publication_authorized": False, **BOUNDARY}
        record = {**body, "review_record_root": root(body)}
        self._atomic(path, record)
        self.hub.append("REVIEW_ENVELOPE_REGISTERED", {"project_id": project_id, "review_id": envelope["review_id"],
                                                       "envelope_root": envelope["envelope_root"],
                                                       "envelope_sha256": verified["archive_sha256"]})
        return deepcopy(record)

    def get(self, project_id: str, review_id: str) -> dict[str, Any]:
        path = self._path(project_id, review_id)
        if not path.is_file():
            raise HubRefusal("PIPPI_REVIEW_UNKNOWN")
        value = strict_loads(path.read_bytes())
        body = {key: deepcopy(row) for key, row in value.items() if key != "review_record_root"}
        if (value.get("schema") != RECORD_SCHEMA or value.get("review_record_root") != root(body) or
                value.get("status") not in {"PACKAGED","DISPATCH_PREPARED","RETURNED","PUBLICATION_PROPOSED"} or
                value.get("publication_authorized") is not False or
                any(value.get(key)!=row for key,row in BOUNDARY.items())):
            raise HubRefusal("PIPPI_REVIEW_RECORD_INVALID")
        return value

    def list(self, project_id: str | None = None) -> list[dict[str, Any]]:
        paths = (sorted((self.root / project_id).glob("*.json"), key=lambda item: item.name)
                 if project_id else
                 sorted(self.root.glob("*/*.json"),
                        key=lambda item: item.relative_to(self.root).as_posix()))
        return [self.get(path.parent.name, path.stem) for path in paths]

    def substance(self, *, project_id: str, review_id: str) -> dict[str, Any]:
        """Project exact envelope/return substance without creating alternate state."""
        record = self.get(project_id, review_id)
        envelope_path = Path(record["envelope_path"])
        verified = verify_review_envelope(envelope_path, expected_sha256=record["envelope_sha256"])
        with zipfile.ZipFile(envelope_path, "r") as archive:
            envelope = validate_review_envelope(strict_loads(archive.read("REVIEW-ENVELOPE.json")))
        returned: dict[str, Any] | None = None
        evidence_files: list[dict[str, Any]] = []
        if record["return_path"]:
            raw = Path(record["return_path"]).read_bytes()
            if _sha(raw) != record["return_sha256"]:
                raise HubRefusal("PIPPI_REVIEW_RETURN_ARCHIVE_HASH_MISMATCH")
            with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
                returned = validate_review_return(strict_loads(archive.read("REVIEW-RETURN.json")))
                contents = strict_loads(archive.read("REVIEW-RETURN-CONTENTS.json"))
                observed = _closed_inventory(
                    archive,
                    metadata={"REVIEW-RETURN.json", "REVIEW-RETURN-CONTENTS.json"},
                    schema=RETURN_CONTENTS_SCHEMA,
                )
                if contents != observed or returned["return_root"] != record["return_root"]:
                    raise HubRefusal("PIPPI_REVIEW_RETURN_INVALID")
                evidence_files = deepcopy(contents["files"])
        findings = deepcopy(returned["findings"]) if returned else []
        severity_counts: dict[str, int] = {}
        for finding in findings:
            severity = str(finding.get("severity", finding.get("sev", "UNSPECIFIED"))).upper()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        body = {
            "schema": "mosaic.ucm.pippi-review-substance.v0.1",
            "project_id": project_id,
            "review_id": review_id,
            "envelope_root": verified["envelope_root"],
            "review_class": envelope["review_class"],
            "subject_role": envelope["subject_role"],
            "independent_review_required": envelope["independent_review_required"],
            "envelope_limitations": deepcopy(envelope["limitations"]),
            "reviewer_identity_root": returned["reviewer_identity_root"] if returned else None,
            "reported_outcome": returned["reported_outcome"] if returned else None,
            "findings": findings,
            "severity_counts": severity_counts,
            "return_limitations": deepcopy(returned["limitations"]) if returned else [],
            "evidence_files": evidence_files,
            "interpretation": "EXACT_PROJECTION_NOT_ALTERNATE_AUTHORITY",
            **BOUNDARY,
        }
        return {**body, "substance_root": root(body)}

    def _replace(self, record: dict[str, Any], **changes: Any) -> dict[str, Any]:
        body = {key: deepcopy(row) for key, row in record.items() if key != "review_record_root"}
        body.update(changes)
        updated = {**body, "review_record_root": root(body)}
        self._atomic(self._path(updated["project_id"], updated["review_id"]), updated)
        return updated

    def prepare_courthouse(self, *, project_id: str, review_id: str,
                           destination_jurisdiction: str) -> dict[str, Any]:
        record = self.get(project_id, review_id)
        work_order = build_courthouse_work_order(project=self.hub.get_project(project_id),
            objective=f"Independent review of {review_id}", payload_root=record["envelope_root"],
            destination_jurisdiction=destination_jurisdiction)
        updated = self._replace(record, status="DISPATCH_PREPARED",
                                courthouse_work_order_root=work_order["work_order_root"])
        self.hub.append("COURTHOUSE_WORK_ORDER_DRAFTED", {"project_id": project_id, "review_id": review_id,
                                                          "work_order_root": work_order["work_order_root"]})
        return {"review_record": updated, "work_order": work_order}

    def import_return(self, *, project_id: str, review_id: str, return_path: Path) -> dict[str, Any]:
        record = self.get(project_id, review_id)
        raw = Path(return_path).read_bytes()
        try:
            with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
                result = validate_review_return(strict_loads(archive.read("REVIEW-RETURN.json")))
                contents = strict_loads(archive.read("REVIEW-RETURN-CONTENTS.json"))
                observed = _closed_inventory(archive,
                    metadata={"REVIEW-RETURN.json", "REVIEW-RETURN-CONTENTS.json"}, schema=RETURN_CONTENTS_SCHEMA)
                if contents != observed:
                    raise HubRefusal("PIPPI_REVIEW_RETURN_CONTENTS_INVALID")
                if (result.get("review_id") != review_id or result.get("envelope_sha256") != record["envelope_sha256"] or
                        result.get("evidence_contents_root") != contents["contents_root"]):
                    raise HubRefusal("PIPPI_REVIEW_RETURN_INVALID")
        except (KeyError, zipfile.BadZipFile, OSError, ValueError) as exc:
            if isinstance(exc, HubRefusal):
                raise
            raise HubRefusal("PIPPI_REVIEW_RETURN_INVALID", type(exc).__name__) from exc
        returned_sha,returned_path=archive_local(data_root=self.hub.root,data=raw)
        updated = self._replace(record, status="RETURNED", return_sha256=returned_sha,
                                return_path=str(returned_path.resolve()),return_root=result["return_root"],
                                reported_outcome=result["reported_outcome"])
        self.hub.append("COURTHOUSE_RESULT_IMPORTED", {"project_id": project_id, "review_id": review_id,
                                                       "return_root": result["return_root"],
                                                       "reported_outcome": result["reported_outcome"],
                                                       "authority_interpretation": "NONE"})
        return updated

    def compare(self, *, project_id: str, left_review_id: str, right_review_id: str) -> dict[str, Any]:
        left = self.get(project_id, left_review_id); right = self.get(project_id, right_review_id)
        fields = ("subject_manifest_root", "declared_subject_root", "envelope_root", "status",
                  "reported_outcome", "publication_plan_root")
        changes = [{"field": field, "left": left[field], "right": right[field]}
                   for field in fields if left[field] != right[field]]
        body = {"schema": "mosaic.ucm.pippi-review-comparison.v0.1", "project_id": project_id,
                "left_review_id": left_review_id, "right_review_id": right_review_id,
                "changes": changes, "semantic_interpretation": "NOT_INFERRED", **BOUNDARY}
        return {**body, "comparison_root": root(body)}

    def propose_publication(self, *, project_id: str, review_id: str,
                            artifact_path: Path, artifact_sha256: str,
                            targets: list[str], dkn_public_namespace: str | None) -> dict[str, Any]:
        record = self.get(project_id, review_id)
        if record["status"] != "RETURNED":
            raise HubRefusal("PIPPI_PUBLICATION_REVIEW_RETURN_REQUIRED")
        plan = build_publication_plan(project=self.hub.get_project(project_id),
                                      artifact_path=artifact_path,
                                      artifact_sha256=artifact_sha256,
                                      targets=targets,
                                      dkn_public_namespace=dkn_public_namespace)
        updated = self._replace(record, status="PUBLICATION_PROPOSED",
                                publication_plan_root=plan["publication_plan_root"])
        self.hub.append("PUBLICATION_PROPOSED", {"project_id": project_id, "review_id": review_id,
                                                 "publication_plan_root": plan["publication_plan_root"],
                                                 "human_authorization_required": True})
        return {"review_record": updated, "publication_plan": plan,
                "human_authorization_required": True, **BOUNDARY}

