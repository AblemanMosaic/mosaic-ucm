"""Verify and stage a UCM archive into a new directory."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

from VERIFY import verify


def stage(archive: Path, destination: Path, *, schema: str | None = None,
          role: str | None = None):
    result = verify(archive, schema, role)
    destination = destination.resolve()
    if destination.exists():
        raise ValueError("STAGE_DESTINATION_EXISTS")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        with zipfile.ZipFile(archive) as source:
            for info in source.infolist():
                target = temporary / info.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write(source.read(info))
                    stream.flush(); os.fsync(stream.fileno())
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return {**result, "staged_to": str(destination)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path); parser.add_argument("destination", type=Path)
    parser.add_argument("--schema"); parser.add_argument("--role")
    args = parser.parse_args()
    try:
        result = stage(args.archive, args.destination, schema=args.schema, role=args.role)
        print(__import__("json").dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as error:
        print(__import__("json").dumps({"status": "REFUSED", "diagnostic": str(error),
            "standing": "INFORMATION_ONLY", "authority_effect": "NONE",
            "real_a5": False, "g0": "CLOSED"}, sort_keys=True, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
