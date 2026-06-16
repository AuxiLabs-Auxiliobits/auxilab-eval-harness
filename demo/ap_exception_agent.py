"""Mock AP (Accounts Payable) Exception Handling Agent.

This stands in for Brief #5 from the AuxiLabs hackathon. It is intentionally
simple — and intentionally a little buggy — so the eval harness has
something to find: real bugs, format errors, and the occasional
hallucination.

Input shape:
    {
        "invoice_id":      str,
        "amount":          float,
        "vendor":          str,
        "po_number":       Optional[str],
        "due_date":        str (ISO),
        "duplicate_of":    Optional[str],   # known-duplicate hint
        "currency":        Optional[str],
    }

Output shape:
    {
        "decision":        "approve" | "flag_duplicate" | "needs_review" | "reject",
        "reason":          str,
        "exception_type":  str,
        "next_action":     str,
        "confidence":      float in [0, 1],
    }
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


_KNOWN_VENDORS: set[str] = {
    "Acme Corp",
    "Globex Inc",
    "Initech",
    "Umbrella Logistics",
    "Hooli",
    "Stark Industries",
}

# Threshold above which an invoice needs manager review.
_REVIEW_THRESHOLD = 10_000.0


def handle_ap_exception(payload: dict[str, Any]) -> dict[str, Any]:
    """Classify an AP invoice exception and return a structured decision.

    The agent inspects the payload and chooses one of four decisions. It is
    deliberately imperfect: some edge cases (very large invoices, foreign
    currency without a PO) will produce subtle mistakes that the eval
    harness should catch.
    """
    invoice_id = str(payload.get("invoice_id", "")).strip()
    amount = float(payload.get("amount") or 0.0)
    vendor = str(payload.get("vendor", "")).strip()
    po_number = payload.get("po_number")
    duplicate_of = payload.get("duplicate_of")
    due_date_raw = payload.get("due_date")
    currency = (payload.get("currency") or "USD").upper()

    # 1. Duplicate detection — strongest signal.
    if duplicate_of:
        return {
            "decision": "flag_duplicate",
            "reason": (
                f"Invoice {invoice_id} appears to be a duplicate of "
                f"{duplicate_of} from {vendor}."
            ),
            "exception_type": "DuplicateInvoice",
            "next_action": "Block payment and notify AP supervisor.",
            "confidence": 0.95,
        }

    # 2. Validation: missing critical fields.
    if not invoice_id or not vendor or amount <= 0:
        return {
            "decision": "reject",
            "reason": "Invoice missing required fields (id / vendor / amount).",
            "exception_type": "InvalidPayload",
            "next_action": "Return to vendor for resubmission.",
            "confidence": 0.9,
        }

    # 3. Unknown vendor → needs onboarding.
    if vendor not in _KNOWN_VENDORS:
        return {
            "decision": "needs_review",
            "reason": (
                f"Vendor {vendor!r} is not in the approved master file. "
                "Vendor onboarding required before payment."
            ),
            "exception_type": "UnknownVendor",
            "next_action": "Route to vendor onboarding queue.",
            "confidence": 0.8,
        }

    # 4. Missing PO for material spend.
    if po_number in (None, "", "null") and amount > 1_000:
        return {
            "decision": "needs_review",
            "reason": (
                f"PO number missing for {vendor} invoice of "
                f"{amount:.2f} {currency}. Three-way match cannot be "
                "performed."
            ),
            "exception_type": "MissingPO",
            "next_action": "Request PO from requisitioner.",
            "confidence": 0.85,
        }

    # 5. Past-due dates → escalate.
    if _is_past_due(due_date_raw):
        return {
            "decision": "needs_review",
            "reason": (
                f"Due date {due_date_raw} is in the past — late payment "
                "fee may apply."
            ),
            "exception_type": "PastDue",
            "next_action": "Escalate to AP manager for prioritisation.",
            "confidence": 0.75,
        }

    # 6. Large amount → manager review.
    if amount >= _REVIEW_THRESHOLD:
        return {
            "decision": "needs_review",
            "reason": (
                f"Invoice amount {amount:.2f} {currency} exceeds the "
                f"{_REVIEW_THRESHOLD:.0f} {currency} approval threshold."
            ),
            "exception_type": "OverThreshold",
            "next_action": "Forward to AP manager for sign-off.",
            "confidence": 0.85,
        }

    # 7. Default: approve.
    return {
        "decision": "approve",
        "reason": (
            f"Invoice {invoice_id} from {vendor} for {amount:.2f} "
            f"{currency} passes all validation checks."
        ),
        "exception_type": "None",
        "next_action": "Schedule payment per vendor terms.",
        "confidence": 0.9,
    }


def _is_past_due(value: Any) -> bool:
    if not value:
        return False
    try:
        if isinstance(value, date):
            d = value
        else:
            d = datetime.fromisoformat(str(value)).date()
    except ValueError:
        return False
    return d < date.today()
