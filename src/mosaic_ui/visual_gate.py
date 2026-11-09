"""Deterministic pixel-difference gates for Mosaic owned-window review captures."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path
from typing import Iterable

from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .model import UIRefusal


class VisualGateRefusal(UIRefusal):
    pass


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    distances = (abs(estimate - left), abs(estimate - up), abs(estimate - upper_left))
    return (left, up, upper_left)[distances.index(min(distances))]


def _png_rgb(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise VisualGateRefusal("VISUAL_PNG_SIGNATURE_REFUSED", str(path))
    offset, width, height, payload = 8, 0, 0, bytearray()
    while offset + 12 <= len(data):
        size = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        body = data[offset + 8:offset + 8 + size]
        crc = struct.unpack(">I", data[offset + 8 + size:offset + 12 + size])[0]
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            raise VisualGateRefusal("VISUAL_PNG_CRC_REFUSED", str(path))
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", body)
            if (depth, color, compression, filtering, interlace) != (8, 2, 0, 0, 0):
                raise VisualGateRefusal("VISUAL_PNG_FORMAT_REFUSED", str(path))
        elif kind == b"IDAT":
            payload.extend(body)
        elif kind == b"IEND":
            break
        offset += size + 12
    if width <= 0 or height <= 0:
        raise VisualGateRefusal("VISUAL_PNG_DIMENSIONS_REFUSED", str(path))
    raw = zlib.decompress(bytes(payload))
    stride = width * 3
    if len(raw) != (stride + 1) * height:
        raise VisualGateRefusal("VISUAL_PNG_PAYLOAD_REFUSED", str(path))
    rows: list[bytes] = []
    for y in range(height):
        row = raw[y * (stride + 1):(y + 1) * (stride + 1)]
        filter_kind, decoded = row[0], bytearray(row[1:])
        previous = rows[-1] if rows else bytes(stride)
        if filter_kind not in {0, 1, 2, 3, 4}:
            raise VisualGateRefusal("VISUAL_PNG_FILTER_REFUSED", f"{path}:{filter_kind}")
        for index in range(stride):
            left = decoded[index - 3] if index >= 3 else 0
            up = previous[index]
            upper_left = previous[index - 3] if index >= 3 else 0
            predictor = 0 if filter_kind == 0 else left if filter_kind == 1 else up if filter_kind == 2 \
                else (left + up) // 2 if filter_kind == 3 else _paeth(left, up, upper_left)
            decoded[index] = (decoded[index] + predictor) & 0xFF
        rows.append(bytes(decoded))
    return width, height, b"".join(rows)


def compare_pngs(baseline: Path, candidate: Path) -> dict:
    bw, bh, before = _png_rgb(baseline)
    cw, ch, after = _png_rgb(candidate)
    if (bw, bh) != (cw, ch):
        return {
            "dimensions_match": False,
            "baseline": {"width": bw, "height": bh},
            "candidate": {"width": cw, "height": ch},
            "mismatched_pixels": None,
            "mismatch_ratio": 1.0,
            "mean_channel_delta": 1.0,
            "max_channel_delta": 255,
            "difference_bounds": None,
        }
    mismatched = 0
    channel_delta = 0
    maximum = 0
    min_x, min_y, max_x, max_y = bw, bh, -1, -1
    for pixel in range(bw * bh):
        start = pixel * 3
        left, right = before[start:start + 3], after[start:start + 3]
        deltas = [abs(left[index] - right[index]) for index in range(3)]
        if any(deltas):
            mismatched += 1
            x, y = pixel % bw, pixel // bw
            min_x, min_y, max_x, max_y = min(min_x, x), min(min_y, y), max(max_x, x), max(max_y, y)
        channel_delta += sum(deltas)
        maximum = max(maximum, *deltas)
    bounds = None if mismatched == 0 else {
        "x": min_x, "y": min_y, "width": max_x - min_x + 1, "height": max_y - min_y + 1,
    }
    return {
        "dimensions_match": True,
        "baseline": {"width": bw, "height": bh},
        "candidate": {"width": cw, "height": ch},
        "mismatched_pixels": mismatched,
        "mismatch_ratio": round(mismatched / max(1, bw * bh), 9),
        "mean_channel_delta": round(channel_delta / max(1, len(before) * 255), 9),
        "max_channel_delta": maximum,
        "difference_bounds": bounds,
    }


def _capture_index(manifest_path: Path) -> tuple[dict[tuple[str, str, int], dict], dict]:
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("schema") != "mosaic.ui.review-gallery.v0.1":
        raise VisualGateRefusal("VISUAL_MANIFEST_SCHEMA_REFUSED", str(manifest_path))
    index = {}
    for row in manifest.get("views", []):
        key = (str(row.get("view_id")), str(row.get("theme_id")), int(row.get("dpi", 0)))
        if key in index or not all((key[0], key[1], key[2])):
            raise VisualGateRefusal("VISUAL_MANIFEST_KEY_REFUSED", repr(key))
        path = Path(row["path"])
        if not path.is_absolute():
            path = manifest_path.parent / path
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != row.get("sha256"):
            raise VisualGateRefusal("VISUAL_CAPTURE_HASH_REFUSED", str(path))
        index[key] = {**row, "resolved_path": path}
    return index, manifest


def run_visual_gate(
    baseline_manifest: Path,
    candidate_manifest: Path,
    output: Path,
    *,
    max_mismatch_ratio: float = 0.0,
    max_mean_channel_delta: float = 0.0,
) -> tuple[dict, int]:
    if not 0 <= max_mismatch_ratio <= 1 or not 0 <= max_mean_channel_delta <= 1:
        raise VisualGateRefusal("VISUAL_THRESHOLD_REFUSED")
    baseline, baseline_body = _capture_index(baseline_manifest)
    candidate, candidate_body = _capture_index(candidate_manifest)
    missing = sorted(set(baseline) - set(candidate))
    unexpected = sorted(set(candidate) - set(baseline))
    checks = []
    for key in sorted(set(baseline) & set(candidate)):
        diff = compare_pngs(baseline[key]["resolved_path"], candidate[key]["resolved_path"])
        passed = (
            diff["dimensions_match"]
            and diff["mismatch_ratio"] <= max_mismatch_ratio
            and diff["mean_channel_delta"] <= max_mean_channel_delta
        )
        checks.append({
            "view_id": key[0], "theme_id": key[1], "dpi": key[2],
            "baseline_sha256": baseline[key]["sha256"],
            "candidate_sha256": candidate[key]["sha256"],
            "diff": diff, "disposition": "PASS" if passed else "REFUSE",
        })
    failures = [f"{row['view_id']}:{row['theme_id']}:{row['dpi']}" for row in checks if row["disposition"] != "PASS"]
    failures.extend(f"MISSING:{':'.join(map(str, key))}" for key in missing)
    failures.extend(f"UNEXPECTED:{':'.join(map(str, key))}" for key in unexpected)
    result = {
        "schema": "mosaic.ui.visual-regression-gate.v0.1",
        "baseline_commitment": baseline_body.get("commitment"),
        "candidate_commitment": candidate_body.get("commitment"),
        "thresholds": {
            "max_mismatch_ratio": max_mismatch_ratio,
            "max_mean_channel_delta": max_mean_channel_delta,
        },
        "checks": checks,
        "failures": failures,
        "disposition": "PASS_LOCAL_CANDIDATE" if not failures else "REFUSE",
        "standing": "LOCAL_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "PIXEL_DIFFERENCE_ON_EXACT_CAPTURE_ENVIRONMENT_NOT_BROAD_RENDERING_EQUIVALENCE",
    }
    result["commitment"] = commitment("MOSAIC.UI.VISUAL_REGRESSION_GATE.v0.1", result)
    receipt = {
        "schema": "mosaic.ui.visual-regression-receipt.v0.1",
        "gate_commitment": result["commitment"],
        "checks": len(checks),
        "failed": len(failures),
        "disposition": result["disposition"],
        "authority_effect": "NONE",
    }
    receipt["receipt_commitment"] = commitment("MOSAIC.UI.VISUAL_REGRESSION_RECEIPT.v0.1", receipt)
    output.mkdir(parents=True, exist_ok=True)
    atomic_write(output / "visual-regression-gate.json", canonical_bytes(result) + b"\n")
    atomic_write(output / "visual-regression-receipt.json", canonical_bytes(receipt) + b"\n")
    return receipt, 0 if not failures else 32


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two Mosaic native review galleries at pixel level.")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-mismatch-ratio", type=float, default=0.0)
    parser.add_argument("--max-mean-channel-delta", type=float, default=0.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        receipt, code = run_visual_gate(
            args.baseline.resolve(), args.candidate.resolve(), args.output.resolve(),
            max_mismatch_ratio=args.max_mismatch_ratio,
            max_mean_channel_delta=args.max_mean_channel_delta,
        )
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return code
    except (VisualGateRefusal, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "schema": "mosaic.ui.visual-regression-refusal.v0.1",
            "disposition": "REFUSE",
            "refusal_code": getattr(exc, "code", "VISUAL_GATE_INPUT_OR_IO_REFUSED"),
            "detail": getattr(exc, "detail", str(exc)),
            "authority_effect": "NONE",
        }, indent=2, sort_keys=True))
        return 32


if __name__ == "__main__":
    raise SystemExit(main())
