#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, sys, zipfile
from pathlib import PurePosixPath

SCHEMA = "mosaic.ucm.agentic-adaptation-sidecar.v0.1"
ROLE = "UCM_AMCAS_AGENTIC_ADAPTATION_SIDECAR"
BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")

def main():
    path = pathlib.Path(sys.argv[1])
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        assert len(infos) == len({row.filename for row in infos})
        assert all(row.compress_type == zipfile.ZIP_STORED and row.date_time == (1980,1,1,0,0,0)
                   and row.file_size <= 64 * 1024 * 1024 for row in infos)
        assert all(name and name == PurePosixPath(name).as_posix()
                   and not name.startswith("/") and ".." not in PurePosixPath(name).parts
                   and "\\" not in name and ":" not in name
                   for name in (row.filename for row in infos))
        payloads = {row.filename: archive.read(row) for row in infos}
    manifest = json.loads(payloads.pop("MANIFEST.json"))
    assert manifest["schema"] == SCHEMA and manifest["artifact_role"] == ROLE
    assert {key: manifest[key] for key in BOUNDARY} == BOUNDARY
    body = {key: value for key, value in manifest.items() if key != "manifest_root"}
    assert hashlib.sha256(canonical(body)).hexdigest() == manifest["manifest_root"]
    rows = [{"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            for name, raw in sorted(payloads.items())]
    assert rows == manifest["files"]
    contract = json.loads(payloads["SIDECAR-CONTRACT.json"])
    cbody = {key: value for key, value in contract.items() if key != "contract_root"}
    assert hashlib.sha256(canonical(cbody)).hexdigest() == contract["contract_root"]
    assert {key: contract[key] for key in BOUNDARY} == BOUNDARY
    print(json.dumps({"status":"PASS", "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                      "manifest_root":manifest["manifest_root"], **BOUNDARY}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
