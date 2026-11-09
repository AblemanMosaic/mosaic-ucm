"""Platform-private protection and verification for local P/PPI secrets."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import stat
import subprocess
from typing import Any


class PrivateFileRefusal(RuntimeError):
    """Fail closed when a private file lacks the required platform boundary."""


_WINDOWS_PROTECT = r"""
$ErrorActionPreference='Stop'
$path=[IO.Path]::GetFullPath($env:PIPPI_SECURITY_TARGET)
if(!(Test-Path -LiteralPath $path -PathType Leaf)){throw 'PIPPI_PRIVATE_FILE_MISSING'}
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
$file=New-Object IO.FileInfo($path)
$acl=$file.GetAccessControl()
$acl.SetAccessRuleProtection($true,$false)
foreach($rule in @($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))){[void]$acl.RemoveAccessRuleSpecific($rule)}
$rule=New-Object Security.AccessControl.FileSystemAccessRule($sid,[Security.AccessControl.FileSystemRights]::FullControl,[Security.AccessControl.AccessControlType]::Allow)
$acl.AddAccessRule($rule)
$file.SetAccessControl($acl)
"""

_WINDOWS_VERIFY = r"""
$ErrorActionPreference='Stop'
$path=[IO.Path]::GetFullPath($env:PIPPI_SECURITY_TARGET)
if(!(Test-Path -LiteralPath $path -PathType Leaf)){throw 'PIPPI_PRIVATE_FILE_MISSING'}
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
$file=New-Object IO.FileInfo($path)
$acl=$file.GetAccessControl()
$rules=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
if(!$acl.AreAccessRulesProtected){throw 'PIPPI_PRIVATE_FILE_DACL_INHERITED'}
if($rules.Count -ne 1){throw 'PIPPI_PRIVATE_FILE_DACL_RULE_COUNT_INVALID'}
$rule=$rules[0]
$ruleSid=$rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier])
if($ruleSid.Value -ne $sid.Value){throw 'PIPPI_PRIVATE_FILE_DACL_PRINCIPAL_INVALID'}
if($rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow){throw 'PIPPI_PRIVATE_FILE_DACL_TYPE_INVALID'}
if($rule.IsInherited){throw 'PIPPI_PRIVATE_FILE_DACL_INHERITED'}
$full=[Security.AccessControl.FileSystemRights]::FullControl
if(($rule.FileSystemRights -band $full) -ne $full){throw 'PIPPI_PRIVATE_FILE_DACL_RIGHTS_INVALID'}
[ordered]@{status='PASS';security_model='WINDOWS_PROTECTED_USER_DACL';principal_binding='CURRENT_USER_SID';access_rule_count=$rules.Count;inherited=$false}|ConvertTo-Json -Compress
"""


def _powershell(script: str, path: Path) -> subprocess.CompletedProcess[str]:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    environment = dict(os.environ)
    environment["PIPPI_SECURITY_TARGET"] = str(path)
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True, text=True, env=environment, check=False,
    )


def protect_private_file(path: Path) -> dict[str, Any]:
    """Apply the narrow platform permission boundary, then verify it."""
    candidate = Path(path)
    if candidate.is_symlink():
        raise PrivateFileRefusal("PIPPI_PRIVATE_FILE_TYPE_INVALID")
    target = candidate.resolve(strict=True)
    if not target.is_file():
        raise PrivateFileRefusal("PIPPI_PRIVATE_FILE_TYPE_INVALID")
    if os.name == "nt":
        result = _powershell(_WINDOWS_PROTECT, target)
        if result.returncode:
            raise PrivateFileRefusal(
                "PIPPI_PRIVATE_FILE_DACL_PROTECTION_FAILED:" +
                (result.stderr or result.stdout).strip()[-512:]
            )
    else:
        os.chmod(target, 0o600)
    return verify_private_file(target)


def verify_private_file(path: Path) -> dict[str, Any]:
    """Refuse a private file whose platform protection has drifted."""
    candidate = Path(path)
    if candidate.is_symlink():
        raise PrivateFileRefusal("PIPPI_PRIVATE_FILE_TYPE_INVALID")
    target = candidate.resolve(strict=True)
    if not target.is_file():
        raise PrivateFileRefusal("PIPPI_PRIVATE_FILE_TYPE_INVALID")
    if os.name == "nt":
        result = _powershell(_WINDOWS_VERIFY, target)
        if result.returncode:
            raise PrivateFileRefusal(
                "PIPPI_PRIVATE_FILE_DACL_INVALID:" +
                (result.stderr or result.stdout).strip()[-512:]
            )
        try:
            value = json.loads(result.stdout.strip())
        except (json.JSONDecodeError, TypeError) as error:
            raise PrivateFileRefusal("PIPPI_PRIVATE_FILE_DACL_RESULT_INVALID") from error
        if value.get("status") != "PASS":
            raise PrivateFileRefusal("PIPPI_PRIVATE_FILE_DACL_INVALID")
        return value
    details = target.stat()
    mode = stat.S_IMODE(details.st_mode)
    if mode != 0o600:
        raise PrivateFileRefusal("PIPPI_PRIVATE_FILE_MODE_INVALID")
    if hasattr(os, "geteuid") and details.st_uid != os.geteuid():
        raise PrivateFileRefusal("PIPPI_PRIVATE_FILE_OWNER_INVALID")
    return {"status": "PASS", "security_model": "POSIX_MODE_0600",
            "mode": "0600", "owner_uid": details.st_uid}
