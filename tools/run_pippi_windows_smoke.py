#!/usr/bin/env python3
"""Positive Windows install/service/dashboard/uninstall validation for P/PPI."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


BOUNDARY = {"standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def run(command: list[str], *, cwd: Path | None = None,
        env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, env=env, text=True,
                            capture_output=True)
    if result.returncode:
        raise RuntimeError(f"PIPPI_WINDOWS_SMOKE_COMMAND_REFUSED:{command[0]}:"
                           f"{result.stdout[-1000:]}:{result.stderr[-1000:]}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime", type=Path)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.name != "nt":
        raise SystemExit("PIPPI_WINDOWS_SMOKE_REQUIRES_WINDOWS")
    runtime = args.runtime.resolve(); work = args.work.resolve(); output = args.output.resolve()
    if work.exists() or output.exists():
        raise SystemExit("PIPPI_WINDOWS_SMOKE_OUTPUT_NOT_EMPTY")
    work.mkdir(parents=True); output.mkdir(parents=True)
    manifest = json.loads((runtime / "MANIFEST.json").read_text(encoding="utf-8"))
    runtime_root = manifest["root"]
    install_root = work / "installed"; data_root = work / "data"
    phases: list[dict[str, object]] = []

    def phase(name: str, detail: object) -> None:
        row = {"sequence": len(phases) + 1, "phase": name, "status": "PASS",
               "detail": detail}
        phases.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)

    run([sys.executable, "-B", str(runtime / "tools/verify_runtime_tree.py"),
         str(runtime)])
    phase("RUNTIME_VERIFIED", runtime_root)
    install = runtime / "install" / "INSTALL-PIPPI.ps1"
    run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(install), "-ExpectedRuntimeRoot", runtime_root,
         "-InstallRoot", str(install_root), "-DataRoot", str(data_root),
         "-GovernorLabel", "PIPPI-WINDOWS-SMOKE", "-MosaicID", "",
         "-DKNPublicKey", "", "-GitHubAccount", "",
         "-GitHubCredentialReference", "", "-NoShortcut"])
    phase("INSTALL_PASS", str(install_root))
    env = {**os.environ, "PYTHONPATH": str(install_root / "src"),
           "PYTHONDONTWRITEBYTECODE": "1", "TEMP": str(work), "TMP": str(work)}
    verified = run([sys.executable, "-B", "-m", "ucm.pippi_cli", "--data-root",
                    str(data_root), "verify"], cwd=install_root, env=env)
    phase("INSTALLED_STATE_VERIFIED", json.loads(verified.stdout)["journal_head"])
    process = subprocess.Popen(
        [sys.executable, "-B", "-m", "ucm.pippi_cli", "--data-root",
         str(data_root), "serve"], cwd=install_root, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        endpoint = data_root / "IPC-ENDPOINT.json"
        for _ in range(100):
            if endpoint.is_file(): break
            if process.poll() is not None:
                raise RuntimeError("PIPPI_WINDOWS_SMOKE_SERVICE_EXITED")
            time.sleep(0.05)
        else:
            raise RuntimeError("PIPPI_WINDOWS_SMOKE_SERVICE_TIMEOUT")
        acl_code = (
            "import json,sys;from pathlib import Path;"
            "from ucm.pippi_security import verify_private_file;"
            "print(json.dumps(verify_private_file(Path(sys.argv[1])/'IPC.key'),sort_keys=True))")
        acl = run([sys.executable, "-B", "-c", acl_code, str(data_root)],
                  cwd=install_root, env=env)
        phase("IPC_KEY_PRIVATE_ACL_PASS", json.loads(acl.stdout))
        request_code = (
            "import json,sys;from pathlib import Path;"
            "from ucm.pippi_service import request;"
            "print(json.dumps(request('verify',data_root=Path(sys.argv[1])),sort_keys=True))")
        response = run([sys.executable, "-B", "-c", request_code, str(data_root)],
                       cwd=install_root, env=env)
        projected = json.loads(response.stdout)
        phase("AUTHENTICATED_LOOPBACK_PASS", projected["journal_head"])
        stop_code = (
            "import json,sys;from pathlib import Path;"
            "from ucm.pippi_service import request;"
            "print(json.dumps(request('stop',data_root=Path(sys.argv[1])),sort_keys=True))")
        run([sys.executable, "-B", "-c", stop_code, str(data_root)],
            cwd=install_root, env=env)
        process.wait(timeout=10)
        if process.returncode:
            raise RuntimeError("PIPPI_WINDOWS_SMOKE_SERVICE_STOP_FAILED")
        phase("SERVICE_STOP_PASS", process.returncode)
    finally:
        if process.poll() is None:
            process.terminate(); process.wait(timeout=10)
    dashboard = run([sys.executable, "-B", "-m", "ucm.pippi_cli", "--data-root",
                     str(data_root), "dashboard-probe"], cwd=install_root, env=env)
    dashboard_result = json.loads(dashboard.stdout)
    if dashboard_result.get("status") != "PASS":
        raise RuntimeError("PIPPI_WINDOWS_SMOKE_DASHBOARD_REFUSED")
    phase("NATIVE_DASHBOARD_PROBE_PASS", dashboard_result)
    uninstall = install_root / "install" / "UNINSTALL-PIPPI.ps1"
    run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(uninstall), "-InstallRoot", str(install_root), "-DataRoot", str(data_root),
         "-RemoveUserData", "-NoShortcut"])
    if install_root.exists() or data_root.exists():
        raise RuntimeError("PIPPI_WINDOWS_SMOKE_UNINSTALL_INCOMPLETE")
    phase("UNINSTALL_PASS", "runtime_and_disposable_data_removed")
    body = {"schema": "mosaic.ucm.pippi-windows-positive-smoke.v0.1",
            "status": "PASS", "runtime_root": runtime_root,
            "phases": phases, **BOUNDARY}
    result = {**body, "smoke_root": hashlib.sha256(canonical(body)).hexdigest()}
    (output / "PIPPI-WINDOWS-SMOKE.json").write_bytes(canonical(result) + b"\n")
    print(json.dumps({"status": "PASS", "smoke_root": result["smoke_root"]},
                     sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
