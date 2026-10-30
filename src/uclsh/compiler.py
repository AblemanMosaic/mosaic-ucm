from __future__ import annotations

from typing import Any

from .artifact import build_artifact_host
from .canonical import strict_loads
from .kernel import Kernel


def compile_module_text(raw: bytes | str, *, kernel: Kernel | None = None) -> dict[str, Any]:
    active = kernel or Kernel()
    text = raw.decode("utf-8", errors="strict") if type(raw) is bytes else raw
    document = strict_loads(text)
    # build_artifact_host performs the complete module check. Keeping a second
    # identical traversal here doubled compiler-court cost without adding an
    # independent validation boundary.
    return build_artifact_host(text, document, active.descriptor["root"], active.primitive_names)

