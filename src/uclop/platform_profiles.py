from __future__ import annotations

import pathlib
import re
from typing import Any

from .canonical import exact_keys, require, require_root, root


PLATFORMS = {"POSIX", "WINDOWS"}
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{index}" for index in range(1, 10)), *(f"LPT{index}" for index in range(1, 10))}
_TOOL = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")


def _validate_path(value: Any, platform: str) -> str:
    require(type(value) is str and value and "\x00" not in value, "PLATFORM_PATH_INVALID")
    if platform == "POSIX":
        path = pathlib.PurePosixPath(value)
        require(path.is_absolute() and ".." not in path.parts and "." not in path.parts and "\\" not in value and str(path) == value, "PLATFORM_PATH_INVALID")
    else:
        path = pathlib.PureWindowsPath(value)
        require(path.is_absolute() and ".." not in path.parts and "." not in path.parts and "/" not in value and str(path) == value, "PLATFORM_PATH_INVALID")
        for part in path.parts[1:]:
            stem = part.rstrip(" .").split(".")[0].upper()
            require(part == part.rstrip(" .") and stem not in WINDOWS_RESERVED, "PLATFORM_PATH_INVALID")
    return value


def make_platform_profile(*, platform: str, profile_id: str, root_paths: dict[str, str], tool_roots: dict[str, str], isolation_features: list[str], network_default: str) -> dict[str, Any]:
    require(platform in PLATFORMS and type(profile_id) is str and 3 <= len(profile_id) <= 96, "PLATFORM_PROFILE_INVALID")
    require(type(root_paths) is dict and set(root_paths) == {"staging", "runtime", "evidence", "rollback"}, "PLATFORM_ROOT_PATH_SET_INVALID")
    checked_paths = {key: _validate_path(root_paths[key], platform) for key in sorted(root_paths)}
    normalized_paths = [value.casefold() if platform == "WINDOWS" else value for value in checked_paths.values()]
    require(len(normalized_paths) == len(set(normalized_paths)), "PLATFORM_PATH_COLLISION")
    require(type(tool_roots) is dict and tool_roots, "PLATFORM_TOOL_SET_INVALID")
    checked_tools = {}
    for name in sorted(tool_roots):
        require(type(name) is str and bool(_TOOL.fullmatch(name)), "PLATFORM_TOOL_NAME_INVALID")
        checked_tools[name] = require_root(tool_roots[name])
    require(type(isolation_features) is list and isolation_features == sorted(isolation_features) and isolation_features, "PLATFORM_ISOLATION_SET_INVALID")
    require(network_default == "DENY", "PLATFORM_NETWORK_DEFAULT_INVALID")
    body = {
        "schema": "ucl.ucm.protected_platform_profile.v1", "platform": platform, "profile_id": profile_id,
        "root_paths": checked_paths, "tool_roots": checked_tools, "isolation_features": isolation_features,
        "network_default": network_default, "persistent_changes_allowed": False, "fixture_only": True,
        "installed": False, "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    return {**body, "profile_root": root(body)}


def verify_platform_profile(value: Any) -> dict[str, Any]:
    item = exact_keys(value, {"schema", "platform", "profile_id", "root_paths", "tool_roots", "isolation_features", "network_default", "persistent_changes_allowed", "fixture_only", "installed", "standing", "authority_effect", "profile_root"}, "$.platform_profile")
    body = {key: item[key] for key in item if key != "profile_root"}
    require(item["schema"] == "ucl.ucm.protected_platform_profile.v1" and item["profile_root"] == root(body), "PLATFORM_PROFILE_ROOT_INVALID")
    rebuilt = make_platform_profile(platform=item["platform"], profile_id=item["profile_id"], root_paths=item["root_paths"], tool_roots=item["tool_roots"], isolation_features=item["isolation_features"], network_default=item["network_default"])
    require(rebuilt == item, "PLATFORM_PROFILE_CONTENT_INVALID")
    return body


def compare_platform_profiles(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    verify_platform_profile(left); verify_platform_profile(right)
    require(left["platform"] != right["platform"], "PLATFORM_PROFILE_DIVERSITY_REQUIRED")
    shared_contract = {
        "path_roles": sorted(left["root_paths"]), "tool_names": sorted(set(left["tool_roots"]) & set(right["tool_roots"])),
        "network_default": left["network_default"], "persistent_changes_allowed": False,
        "fixture_only": True, "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
    }
    require(left["network_default"] == right["network_default"] == "DENY", "PLATFORM_NETWORK_DIVERGENCE")
    require(sorted(left["root_paths"]) == sorted(right["root_paths"]), "PLATFORM_PATH_ROLE_DIVERGENCE")
    body = {"schema": "ucl.ucm.platform_profile_comparison.v1", "left_profile_root": left["profile_root"], "right_profile_root": right["profile_root"], "shared_contract": shared_contract, "status": "PASS_REFERENCE_EQUIVALENCE"}
    return {**body, "comparison_root": root(body)}

