"""Atheris-compatible contract validator target; not run by builder qualification."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from uclop.canonical import Refusal, strict_loads
from ucm.amcas import validate_contract as validate_amcas
from ucm.realization import validate_contract as validate_realization


def fuzz_one_input(data: bytes) -> None:
    try:
        value = strict_loads(data)
    except Refusal:
        return
    if type(value) is not dict:
        return
    try:
        if value.get("schema") == "mosaic.realization-space-contract.v0.1":
            validate_realization(value)
        elif value.get("schema") in {"mosaic.amcas.integration-contract.v0.1",
                                    "mosaic.amcas.integration-contract.v0.2"}:
            validate_amcas(value)
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
