#!/usr/bin/env python3
"""Standard-library verifier for a P/PPI adaptive cold-boot archive."""
from __future__ import annotations

import argparse, hashlib, json, pathlib, zipfile


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def sha(raw): return hashlib.sha256(raw).hexdigest()


def members(raw:bytes):
    import io
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        infos=zf.infolist(); names=[i.filename for i in infos]
        canonical_order = (names == sorted(names) or
                           (bool(names) and names[0] == "MANIFEST.json" and names[1:] == sorted(names[1:])))
        if not canonical_order or len(names)!=len(set(names)):raise ValueError("PIPPI_ARCHIVE_ORDER_OR_DUPLICATE")
        result={}
        for info in infos:
            path=pathlib.PurePosixPath(info.filename)
            if info.filename.startswith("/") or "\\" in info.filename or ".." in path.parts or info.is_dir():
                raise ValueError("PIPPI_ARCHIVE_PATH_INVALID")
            result[info.filename]=zf.read(info)
        return result


def verify(raw:bytes):
    rows=members(raw)
    required={"MANIFEST.json","BOOT/COLD-BOOT.json","UCM/UCM-v0.1-runtime.zip",
        "UGK/UGK-ADAPTIVE-PROFILE.json","PIPPI/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json",
        "META/STATE-MANIFEST.json","META/DKN-BINDING.json","META/THR-MANIFEST.json",
        "META/SELF-CERTIFICATE.json"}
    if not required<=set(rows):
        raise ValueError("PIPPI_COLD_BOOT_REQUIRED_MEMBER_MISSING")
    manifest=json.loads(rows["MANIFEST.json"])
    listed=manifest.get("members")
    expected=sorted([{"path":name,"sha256":sha(data),"bytes":len(data)} for name,data in rows.items() if name!="MANIFEST.json"],key=lambda row:row["path"])
    if listed!=expected or manifest.get("member_count")!=len(expected):raise ValueError("PIPPI_COLD_BOOT_MANIFEST_INVALID")
    body={k:v for k,v in manifest.items() if k!="manifest_root"}
    if manifest.get("manifest_root")!=sha(canonical(body)):raise ValueError("PIPPI_COLD_BOOT_MANIFEST_ROOT_INVALID")
    meta=json.loads(rows["BOOT/COLD-BOOT.json"])
    meta_body={k:v for k,v in meta.items() if k!="cold_boot_root"}
    if meta.get("cold_boot_root")!=sha(canonical(meta_body)):raise ValueError("PIPPI_COLD_BOOT_META_INVALID")
    if meta.get("runtime_sha256")!=sha(rows["UCM/UCM-v0.1-runtime.zip"]):raise ValueError("PIPPI_RUNTIME_PIN_INVALID")
    ugk=json.loads(rows["UGK/UGK-ADAPTIVE-PROFILE.json"])
    ugk_body={k:v for k,v in ugk.items() if k!="ugk_profile_root"}
    contract=json.loads(rows["PIPPI/PIPPI-ADAPTIVE-COLD-BOOT-CONTRACT.json"])
    contract_body={k:v for k,v in contract.items() if k!="cold_boot_contract_root"}
    if (ugk.get("ugk_profile_root")!=sha(canonical(ugk_body))
            or meta.get("ugk_profile_root")!=ugk.get("ugk_profile_root")):
        raise ValueError("PIPPI_UGK_PROFILE_ROOT_INVALID")
    if (contract.get("cold_boot_contract_root")!=sha(canonical(contract_body))
            or meta.get("cold_boot_contract_root")!=contract.get("cold_boot_contract_root")):
        raise ValueError("PIPPI_COLD_BOOT_CONTRACT_ROOT_INVALID")
    project_present="PROJECT/PROJECT-CAPSULE.json" in rows
    if project_present != (meta.get("project_capsule_sha256") is not None):
        raise ValueError("PIPPI_PROJECT_CAPSULE_PRESENCE_INVALID")
    if project_present and meta["project_capsule_sha256"]!=sha(rows["PROJECT/PROJECT-CAPSULE.json"]):
        raise ValueError("PIPPI_PROJECT_CAPSULE_PIN_INVALID")
    runtime=members(rows["UCM/UCM-v0.1-runtime.zip"])
    if "MANIFEST.json" not in runtime:raise ValueError("PIPPI_RUNTIME_MANIFEST_MISSING")
    runtime_manifest=json.loads(runtime["MANIFEST.json"])
    runtime_expected=sorted([{"path":name,"sha256":sha(data),"bytes":len(data)} for name,data in runtime.items() if name!="MANIFEST.json"],key=lambda row:row["path"])
    if runtime_manifest.get("members")!=runtime_expected:raise ValueError("PIPPI_RUNTIME_MANIFEST_INVALID")
    runtime_body={k:v for k,v in runtime_manifest.items() if k!="root"}
    if runtime_manifest.get("root")!=sha(canonical(runtime_body)):raise ValueError("PIPPI_RUNTIME_MANIFEST_ROOT_INVALID")
    if (runtime_manifest.get("version")!="v0.1"
            or runtime_manifest.get("engineering_revision")!="r033"):
        raise ValueError("PIPPI_RUNTIME_IDENTITY_INVALID")
    runtime_thr=json.loads(runtime["META/THR-MANIFEST.json"])
    source_root=runtime_thr.get("admissibility",{}).get("source_manifest_root")
    identity_root=runtime_thr.get("admissibility",{}).get("release_identity_root")
    state=json.loads(rows["META/STATE-MANIFEST.json"])
    dkn=json.loads(rows["META/DKN-BINDING.json"])
    thr=json.loads(rows["META/THR-MANIFEST.json"])
    cert=json.loads(rows["META/SELF-CERTIFICATE.json"])
    payload_names=sorted(name for name in rows if name!="MANIFEST.json" and not name.startswith("META/"))
    state_rows=[{"path":name,"sha256":sha(rows[name]),"bytes":len(rows[name])} for name in payload_names]
    state_body={k:v for k,v in state.items() if k!="state_root"}
    if (state.get("state_root")!=sha(canonical(state_body)) or state.get("members")!=state_rows
            or state.get("artifact")!="PIPPI_ADAPTIVE_COLD_BOOT"
            or state.get("engineering_revision")!="r033"):
        raise ValueError("PIPPI_STATE_MANIFEST_INVALID")
    dkn_body={k:v for k,v in dkn.items() if k!="dkn_binding_root"}
    if (dkn.get("dkn_binding_root")!=sha(canonical(dkn_body))
            or dkn.get("public_namespace")!="mosaic.ucm.v0.1"
            or dkn.get("status")!="DECLARED_UNBOUND" or dkn.get("permission_granted") is not False):
        raise ValueError("PIPPI_DKN_BINDING_INVALID")
    sections={"H_s":thr.get("state"),"H_c":thr.get("admissibility"),
        "H_m":thr.get("meaning"),"H_j":thr.get("locality"),"H_r":thr.get("receipt_identity")}
    thr_body={k:v for k,v in thr.items() if k!="h_body"}
    if (thr.get("h_body")!=sha(canonical(thr_body))
            or any(thr.get("commitments",{}).get(k)!=sha(canonical(v)) for k,v in sections.items())
            or thr.get("state",{}).get("state_root")!=state["state_root"]
            or thr.get("admissibility",{}).get("source_manifest_root")!=source_root
            or thr.get("admissibility",{}).get("release_identity_root")!=identity_root
            or thr.get("locality",{}).get("dkn_binding_root")!=dkn["dkn_binding_root"]):
        raise ValueError("PIPPI_THR_MANIFEST_INVALID")
    cert_body={k:v for k,v in cert.items() if k!="certificate_root"}
    if (cert.get("certificate_root")!=sha(canonical(cert_body))
            or cert.get("state_root")!=state["state_root"]
            or cert.get("thr_body_root")!=thr["h_body"]
            or cert.get("dkn_binding_root")!=dkn["dkn_binding_root"]
            or cert.get("certificate_status")!="READY_FOR_EXTERNAL_DKN_CERTIFICATION"
            or cert.get("signature_hex") is not None or cert.get("storage_location_bound") is not False):
        raise ValueError("PIPPI_SELF_CERTIFICATE_INVALID")
    return {"schema":"mosaic.ucm.pippi-cold-boot-verification.v0.1","status":"PASS",
            "archive_sha256":sha(raw),"manifest_root":manifest["manifest_root"],
            "cold_boot_root":meta["cold_boot_root"],"runtime_sha256":meta["runtime_sha256"],
            "state_root":state["state_root"],"thr_body_root":thr["h_body"],
            "dkn_binding_root":dkn["dkn_binding_root"],"certificate_root":cert["certificate_root"],
            "members":len(expected),"standing":"INFORMATION_ONLY","authority_effect":"NONE",
            "real_a5":False,"g0":"CLOSED"}


def main():
    p=argparse.ArgumentParser();p.add_argument("archive",type=pathlib.Path);a=p.parse_args()
    try: result=verify(a.archive.read_bytes())
    except Exception as exc:
        result={"status":"REFUSED","diagnostic":type(exc).__name__,"detail":str(exc),
                "standing":"INFORMATION_ONLY","authority_effect":"NONE","real_a5":False,"g0":"CLOSED"}
        print(json.dumps(result,sort_keys=True));return 3
    print(json.dumps(result,sort_keys=True));return 0


if __name__=="__main__":raise SystemExit(main())
