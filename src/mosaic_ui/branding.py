"""Committed local branding assets shared by Mosaic UI native surfaces."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .model import UIRefusal


APPLICATION_ID = "AblemanMosaic.UIReview"
APPLICATION_TITLE = "Mosaic UI Review Workbench"
LOGO_SHA256 = "dfce63b96a9d199cd64095f40de521c62044b23be147343c8b4744aa402e5e04"


def verified_logo_path() -> Path:
    path = Path(__file__).resolve().parent / "assets" / "DeeperLogo.png"
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != LOGO_SHA256:
        raise UIRefusal("REVIEW_STARTUP_LOGO_INTEGRITY_REFUSED", str(path))
    return path


__all__ = ["APPLICATION_ID", "APPLICATION_TITLE", "LOGO_SHA256", "verified_logo_path"]
