"""Allow ``python -m ucm`` to use the installed UCM console surface."""
from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
