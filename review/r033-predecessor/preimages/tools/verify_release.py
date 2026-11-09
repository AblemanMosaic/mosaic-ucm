#!/usr/bin/env python3
"""Verify v0.1 release archives without importing UCM subject code."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import zipfile
from pathlib import PurePosixPath


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


META_NAMES = {
    "META/STATE-MANIFEST.json", "META/DKN-BINDING.json",
    "META/THR-MANIFEST.json", "META/SELF-CERTIFICATE.json",
}


def verify_certification(zf: zipfile.ZipFile, *, role: str, completeness: str,
                         source_manifest_root: str,
                         release_identity_root: str,
                         engineering_revision: str) -> dict:
    if not META_NAMES <= set(zf.namelist()):
        raise SystemExit("RELEASE_CERTIFICATION_META_MISSING:" + role)
    state = json.loads(zf.read("META/STATE-MANIFEST.json"))
    dkn = json.loads(zf.read("META/DKN-BINDING.json"))
    thr = json.loads(zf.read("META/THR-MANIFEST.json"))
    cert = json.loads(zf.read("META/SELF-CERTIFICATE.json"))
    payload_names = sorted(name for name in zf.namelist()
                           if name != "MANIFEST.json" and not name.startswith("META/"))
    rows = [{"path": name, "sha256": sha(zf.read(name)), "bytes": len(zf.read(name))}
            for name in payload_names]
    state_body = {key: value for key, value in state.items() if key != "state_root"}
    if (state.get("state_root") != sha(canonical(state_body))
            or state.get("members") != rows
            or state.get("artifact") != role
            or state.get("version") != "v0.1"
            or state.get("engineering_revision") != engineering_revision):
        raise SystemExit("RELEASE_CERTIFICATION_STATE_REFUSED:" + role)
    dkn_body = {key: value for key, value in dkn.items() if key != "dkn_binding_root"}
    if (dkn.get("dkn_binding_root") != sha(canonical(dkn_body))
            or dkn.get("status") not in {"DECLARED_UNBOUND", "BOUND_EXTERNAL"}
            or dkn.get("permission_granted") is not False):
        raise SystemExit("RELEASE_CERTIFICATION_DKN_REFUSED:" + role)
    sections = {"H_s": thr.get("state"), "H_c": thr.get("admissibility"),
                "H_m": thr.get("meaning"), "H_j": thr.get("locality"),
                "H_r": thr.get("receipt_identity")}
    if (thr.get("h_body") != sha(canonical({key: value for key, value in thr.items()
                                             if key != "h_body"}))
            or any(thr.get("commitments", {}).get(name) != sha(canonical(section))
                   for name, section in sections.items())
            or thr.get("state", {}).get("state_root") != state["state_root"]
            or thr.get("admissibility", {}).get("source_manifest_root") != source_manifest_root
            or thr.get("admissibility", {}).get("release_identity_root") != release_identity_root
            or thr.get("meaning", {}).get("artifact_role") != role
            or thr.get("meaning", {}).get("completeness") != completeness
            or thr.get("locality", {}).get("dkn_binding_root") != dkn["dkn_binding_root"]):
        raise SystemExit("RELEASE_CERTIFICATION_THR_REFUSED:" + role)
    cert_body = {key: value for key, value in cert.items() if key != "certificate_root"}
    if (cert.get("certificate_root") != sha(canonical(cert_body))
            or cert.get("state_root") != state["state_root"]
            or cert.get("thr_body_root") != thr["h_body"]
            or cert.get("dkn_binding_root") != dkn["dkn_binding_root"]
            or cert.get("storage_location_bound") is not False):
        raise SystemExit("RELEASE_SELF_CERTIFICATE_REFUSED:" + role)
    if dkn["status"] == "DECLARED_UNBOUND":
        if (cert.get("certificate_status") != "READY_FOR_EXTERNAL_DKN_CERTIFICATION"
                or cert.get("signature_hex") is not None
                or cert.get("signature_suite") is not None):
            raise SystemExit("RELEASE_SELF_CERTIFICATE_STATUS_REFUSED:" + role)
    else:
        if cert.get("certificate_status") != "PASS_SELF_CERTIFIED":
            raise SystemExit("RELEASE_SELF_CERTIFICATE_STATUS_REFUSED:" + role)
    return {"state_root": state["state_root"], "thr_body_root": thr["h_body"],
            "dkn_binding_root": dkn["dkn_binding_root"],
            "certificate_root": cert["certificate_root"],
            "certificate_status": cert["certificate_status"]}


def verify(path: pathlib.Path, expected: str, expected_role: str,
           expected_completeness: str, *, source_manifest_root: str,
           release_identity_root: str, engineering_revision: str) -> dict:
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise SystemExit(f"ARCHIVE_PIN_MISMATCH:{path.name}")
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        if len(names) != len(set(names)) or names.count("MANIFEST.json") != 1:
            raise SystemExit(f"ARCHIVE_SET_INVALID:{path.name}")
        for name in names:
            member = PurePosixPath(name)
            if member.is_absolute() or ".." in member.parts or "\\" in name:
                raise SystemExit(f"ARCHIVE_PATH_REFUSED:{path.name}:{name}")
        mf = json.loads(zf.read("MANIFEST.json"))
        if (
            mf.get("schema") != "mosaic.ucm.artifact-manifest.v0.1"
            or mf.get("version") != "v0.1"
            or mf.get("engineering_revision") != engineering_revision
            or mf.get("standing") != "INFORMATION_ONLY"
            or mf.get("authority_effect") != "NONE"
            or mf.get("real_a5") is not False
            or mf.get("g0") != "CLOSED"
        ):
            raise SystemExit(f"ARCHIVE_BOUNDARY_REFUSED:{path.name}")
        if mf.get("artifact") != expected_role or mf.get("completeness") != expected_completeness:
            raise SystemExit(f"ARCHIVE_ROLE_REFUSED:{path.name}")
        rows = {row["path"]: row for row in mf["members"]}
        if set(names) != {"MANIFEST.json", *rows}:
            raise SystemExit(f"ARCHIVE_CLOSED_SET_REFUSED:{path.name}")
        for name, row in rows.items():
            data = zf.read(name)
            if sha(data) != row["sha256"] or len(data) != row["bytes"]:
                raise SystemExit(f"ARCHIVE_MEMBER_REFUSED:{path.name}:{name}")
        body = {k: v for k, v in mf.items() if k != "root"}
        if sha(canonical(body)) != mf["root"]:
            raise SystemExit(f"MANIFEST_ROOT_REFUSED:{path.name}")
        mf["certification"] = verify_certification(
            zf, role=expected_role, completeness=expected_completeness,
            source_manifest_root=source_manifest_root,
            release_identity_root=release_identity_root,
            engineering_revision=engineering_revision)
        return mf


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("release", type=pathlib.Path)
    parser.add_argument("--expected-release-root", required=True)
    args = parser.parse_args()
    release = json.loads(args.release.read_text(encoding="utf-8"))
    body = {k: v for k, v in release.items() if k != "root"}
    if sha(canonical(body)) != release["root"]:
        raise SystemExit("RELEASE_ROOT_REFUSED")
    if release["root"] != args.expected_release_root:
        raise SystemExit("RELEASE_EXTERNAL_PIN_MISMATCH")
    if (
        release.get("schema") != "mosaic.ucm.release.v0.1"
        or release.get("product") != "Universal Constitutional Machine"
        or release.get("version") != "v0.1"
        or release.get("engineering_revision") != "r033"
        or release.get("publisher") != "Ableman Mosaic"
        or release.get("copyright") != "Copyright 2026 Ableman Mosaic"
        or release.get("license") != "Apache-2.0"
        or release.get("standing") != "INFORMATION_ONLY"
        or release.get("authority_effect") != "NONE"
        or release.get("real_a5") is not False
        or release.get("g0") != "CLOSED"
    ):
        raise SystemExit("RELEASE_BOUNDARY_REFUSED")
    if not all(type(release.get(field)) is str and len(release[field]) == 64 for field in ("source_manifest_root", "release_identity_root")):
        raise SystemExit("RELEASE_SOURCE_IDENTITY_REFUSED")
    roles = [row.get("role") for row in release["artifacts"]]
    if (len(roles) != len(set(roles)) or
            set(roles[:3]) != {"UCM_RUNTIME", "UCM_SDK", "UCM_REVIEW"} or
            len(roles) != 4):
        raise SystemExit("RELEASE_ARTIFACT_ROLE_SET_REFUSED")
    if roles[3] not in {"UCM_LINEAGE_METADATA", "UCM_AUDIT"}:
        raise SystemExit("RELEASE_ARTIFACT_ROLE_SET_REFUSED")
    expected_kind = "PUBLIC_LINEAGE" if roles[3] == "UCM_LINEAGE_METADATA" else "COMPLETE_AUDIT"
    if release.get("release_kind") != expected_kind:
        raise SystemExit("RELEASE_KIND_REFUSED")
    expected_completeness = {
        "UCM_RUNTIME": "COMPLETE_RUNTIME",
        "UCM_SDK": "COMPLETE_SDK",
        "UCM_REVIEW": "SELF_CONTAINED_CUSTODY",
        "UCM_LINEAGE_METADATA": "METADATA_ONLY",
        "UCM_AUDIT": "COMPLETE_FROZEN_CUSTODY",
    }
    verified = []
    manifests = {}
    for row in release["artifacts"]:
        artifact_path = PurePosixPath(row.get("path", ""))
        if artifact_path.is_absolute() or len(artifact_path.parts) != 1 or "\\" in row.get("path", ""):
            raise SystemExit("RELEASE_ARTIFACT_PATH_REFUSED")
        if row.get("completeness") != expected_completeness[row["role"]]:
            raise SystemExit("RELEASE_ARTIFACT_COMPLETENESS_REFUSED")
        manifest = verify(args.release.parent / row["path"], row["sha256"], row["role"], row["completeness"],
                          source_manifest_root=release["source_manifest_root"],
                          release_identity_root=release["release_identity_root"],
                          engineering_revision=release["engineering_revision"])
        if row.get("manifest_root") != manifest["root"] or row.get("bytes") != (args.release.parent / row["path"]).stat().st_size:
            raise SystemExit("RELEASE_ARTIFACT_DESCRIPTOR_REFUSED")
        verified.append({"role": row["role"], "completeness": row["completeness"],
                         "manifest_root": manifest["root"], **manifest["certification"]})
        manifests[row["role"]] = manifest
    partition = release.get("archive_partition")
    if not isinstance(partition, dict):
        raise SystemExit("RELEASE_ARCHIVE_PARTITION_MISSING")
    partition_body = {key: value for key, value in partition.items() if key != "partition_root"}
    if sha(canonical(partition_body)) != partition.get("partition_root"):
        raise SystemExit("RELEASE_ARCHIVE_PARTITION_ROOT_REFUSED")
    prefixes = partition.get("custody_prefixes")
    if (partition.get("schema") != "mosaic.ucm.release-archive-partition.v0.1"
            or partition.get("policy_schema") != "mosaic.ucm.pippi-transtemporal-archive-policy.v0.1"
            or partition.get("review_mode") != "SELF_CONTAINED_CUSTODY"
            or partition.get("status") != "PASS"
            or not isinstance(prefixes, list) or not prefixes):
        raise SystemExit("RELEASE_ARCHIVE_PARTITION_REFUSED")
    for role in ("UCM_RUNTIME", "UCM_SDK"):
        if any(row["path"].startswith(tuple(prefixes)) for row in manifests[role]["members"]
               if not row["path"].startswith("META/")):
            raise SystemExit("RELEASE_ACTIVE_PROFILE_INLINE_CUSTODY_REFUSED:" + role)
    runtime_members = [row for row in manifests["UCM_RUNTIME"]["members"]
                       if not row["path"].startswith("META/")]
    sdk_members = [row for row in manifests["UCM_SDK"]["members"]
                   if not row["path"].startswith("META/")]
    review_members = [row for row in manifests["UCM_REVIEW"]["members"]
                      if not row["path"].startswith("META/")]
    if (any(not row["path"].startswith(tuple(prefixes)) for row in review_members)
            or partition.get("runtime_member_count") != len(runtime_members)
            or partition.get("sdk_member_count") != len(sdk_members)
            or partition.get("review_member_count") != len(review_members)
            or partition.get("custody_denominator_count") != len(review_members)):
        raise SystemExit("RELEASE_ARCHIVE_PARTITION_COUNTS_REFUSED")
    print(json.dumps({"status": "PASS", "release_root": release["root"], "artifact_count": len(release["artifacts"]), "artifacts": verified, "authority_effect": "NONE"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


