"""Exact-candidate human review requests, templates, and fail-closed receipt verification."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical import atomic_write, canonical_bytes, commitment, read_json
from .model import UIRefusal
from .release_acceptance import acceptance_subject_root


LANES = (
    {
        "lane": "ACCESSIBILITY",
        "scope": "SCREEN_READER_NAMES_STATES_FOCUS_ANNOUNCEMENTS_AND_ERROR_FEEDBACK",
        "required_evidence": ["ASSISTIVE_TECHNOLOGY_AND_VERSION", "HOST_IDENTITY", "TASK_NOTES"],
    },
    {
        "lane": "KEYBOARD",
        "scope": "NO_POINTER_COMPLETE_TASKS_FOCUS_ORDER_SHORTCUTS_ESCAPE_AND_RECOVERY",
        "required_evidence": ["HOST_IDENTITY", "TASK_NOTES", "FOCUS_OBSERVATIONS"],
    },
    {
        "lane": "LOCALIZATION",
        "scope": "HUMAN_LANGUAGE_QUALITY_RTL_MIXED_SCRIPT_TYPOGRAPHY_AND_STABLE_VALUES",
        "required_evidence": ["LOCALES_REVIEWED", "REVIEWER_LANGUAGE_SCOPE", "TASK_NOTES"],
    },
    {
        "lane": "USABILITY",
        "scope": "REFERENCE_WORKFLOW_DISCOVERABILITY_COMPREHENSION_ERROR_RECOVERY_AND_EFFICIENCY",
        "required_evidence": ["TASK_SET", "HOST_IDENTITY", "TASK_NOTES"],
    },
    {
        "lane": "SUBJECTIVE_VISUAL",
        "scope": "HIERARCHY_TYPOGRAPHY_SPACING_COLOR_DENSITY_RESPONSIVENESS_AND_PLATFORM_FIT",
        "required_evidence": ["SURFACES_REVIEWED", "HOST_IDENTITY", "TASK_NOTES"],
    },
)


class HumanReviewRefusal(UIRefusal):
    pass


def make_human_review_request(
    subjects: list[dict[str, Any]], evidence_commitment: str,
) -> dict[str, Any]:
    value = {
        "schema": "mosaic.ui.human-review-request.v1",
        "subject_root": acceptance_subject_root(subjects, evidence_commitment),
        "evidence_commitment": evidence_commitment,
        "lanes": [dict(item) for item in LANES],
        "required_disposition": "APPROVED",
        "status": "PENDING_EXTERNAL_HUMAN_REVIEW",
        "standing": "LOCAL_CANDIDATE_REQUEST",
        "authority_effect": "NONE",
        "claim_boundary": "REQUEST_CREATION_AND_REVIEW_TOOLING_DO_NOT_CONSTITUTE_HUMAN_REVIEW_OR_RELEASE_ADMISSION",
    }
    value["commitment"] = commitment("MOSAIC.UI.HUMAN_REVIEW_REQUEST.v1", value)
    return value


def make_human_review_template(request_path: Path, output: Path) -> dict[str, Any]:
    request, output = read_json(request_path.resolve()), output.resolve()
    _validate_request(request)
    if output.exists():
        raise HumanReviewRefusal("HUMAN_REVIEW_OUTPUT_EXISTS", str(output))
    value = {
        "schema": "mosaic.ui.human-review-receipt.v1",
        "request_commitment": request["commitment"],
        "subject_root": request["subject_root"],
        "reviews": [
            {
                "lane": lane["lane"], "reviewer_id": "REPLACE_WITH_NAMED_HUMAN_REVIEWER",
                "completed_at": "REPLACE_WITH_ISO_8601_TIME", "disposition": "PENDING",
                "evidence_refs": [], "notes": "REPLACE_WITH_HUMAN_OBSERVATIONS",
            }
            for lane in request["lanes"]
        ],
        "standing": "UNCOMPLETED_TEMPLATE",
        "authority_effect": "NONE",
        "claim_boundary": "TEMPLATE_IS_NOT_A_HUMAN_REVIEW_RECEIPT_OR_RELEASE_DECISION",
    }
    atomic_write(output, canonical_bytes(value) + b"\n")
    return value


def _validate_request(request: dict[str, Any]) -> None:
    body = dict(request)
    observed = body.pop("commitment", None)
    if observed != commitment("MOSAIC.UI.HUMAN_REVIEW_REQUEST.v1", body) \
            or request.get("schema") != "mosaic.ui.human-review-request.v1" \
            or request.get("authority_effect") != "NONE" \
            or request.get("lanes") != [dict(item) for item in LANES]:
        raise HumanReviewRefusal("HUMAN_REVIEW_REQUEST_REFUSED", "")


def verify_human_review_receipt(request_path: Path, receipt_path: Path) -> dict[str, Any]:
    request, receipt = read_json(request_path.resolve()), read_json(receipt_path.resolve())
    _validate_request(request)
    keys = {
        "schema", "request_commitment", "subject_root", "reviews", "standing",
        "authority_effect", "claim_boundary", "commitment",
    }
    if set(receipt) != keys or receipt.get("schema") != "mosaic.ui.human-review-receipt.v1" \
            or receipt.get("request_commitment") != request["commitment"] \
            or receipt.get("subject_root") != request["subject_root"] \
            or receipt.get("authority_effect") != "NONE":
        raise HumanReviewRefusal("HUMAN_REVIEW_RECEIPT_REFUSED", "SHAPE_OR_BINDING")
    body = dict(receipt)
    observed = body.pop("commitment", None)
    if observed != commitment("MOSAIC.UI.HUMAN_REVIEW_RECEIPT.v1", body):
        raise HumanReviewRefusal("HUMAN_REVIEW_RECEIPT_REFUSED", "COMMITMENT")
    reviews = receipt.get("reviews")
    lanes = [item["lane"] for item in LANES]
    if not isinstance(reviews, list) or [item.get("lane") for item in reviews if isinstance(item, dict)] != lanes:
        raise HumanReviewRefusal("HUMAN_REVIEW_RECEIPT_REFUSED", "LANES")
    for review in reviews:
        if set(review) != {"lane", "reviewer_id", "completed_at", "disposition", "evidence_refs", "notes"} \
                or review.get("disposition") not in {"APPROVED", "REJECTED", "DEFERRED"} \
                or not isinstance(review.get("reviewer_id"), str) or review["reviewer_id"].startswith("REPLACE_") \
                or not review.get("reviewer_id") \
                or not isinstance(review.get("completed_at"), str) or "T" not in review["completed_at"] \
                or not isinstance(review.get("evidence_refs"), list) or not review["evidence_refs"] \
                or not all(isinstance(item, str) and item for item in review["evidence_refs"]) \
                or not isinstance(review.get("notes"), str) or not review["notes"] \
                or review["notes"].startswith("REPLACE_"):
            raise HumanReviewRefusal("HUMAN_REVIEW_RECEIPT_REFUSED", str(review.get("lane")))
    approved = all(review["disposition"] == "APPROVED" for review in reviews)
    return {
        "schema": "mosaic.ui.human-review-verification.v1",
        "request_commitment": request["commitment"],
        "receipt_commitment": observed,
        "subject_root": request["subject_root"],
        "lane_count": len(reviews),
        "reviewer_ids": sorted({review["reviewer_id"] for review in reviews}),
        "status": "PASS_HUMAN_REVIEW_CANDIDATE" if approved else "HUMAN_REVIEW_HOLD",
        "standing": "HUMAN_REVIEW_CANDIDATE_EVIDENCE",
        "authority_effect": "NONE",
        "claim_boundary": "HUMAN_REVIEW_APPROVAL_DOES_NOT_CONSTITUTE_EXTERNAL_SIGNATURE_OR_CONSTITUTIONAL_ADMISSION",
    }


__all__ = [
    "HumanReviewRefusal", "LANES", "make_human_review_request", "make_human_review_template",
    "verify_human_review_receipt",
]
