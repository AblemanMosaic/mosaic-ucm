"""Atheris-compatible canonical parser target; not run by builder qualification."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import Refusal, canonical_bytes, strict_loads


def fuzz_one_input(data: bytes) -> None:
    try:
        value = strict_loads(data)
        reparsed = strict_loads(canonical_bytes(value))
        if value != reparsed:
            raise AssertionError("CANONICAL_ROUNDTRIP_MISMATCH")
    except Refusal:
        return


def main() -> None:
    try:
        import atheris
    except ImportError as error:
        raise SystemExit("Install atheris only in a disposable reviewer environment.") from error
    atheris.Setup(sys.argv, fuzz_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
