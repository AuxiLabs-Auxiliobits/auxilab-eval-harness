"""Mock Payment Run Agent (Brief #8 from the AuxiLabs hackathon).

This stands in for "another team's submission" — it is intentionally
imperfect so the eval harness has real defects to surface (a wrong
priority label, a security-relevant edge case, and a schema violation).

Input shape:
    {
        "payment_id":            str,
        "invoice_id":            str,
        "vendor":                str,
        "amount":                float,
        "currency":              str,
        "due_date":              str (ISO),
        "available_cash":        float,
        "batch_total_committed": float,
        "vendor_tier":           Optional[str],   # strategic|standard|watchlist
        "fraud_score":           Optional[float], # 0..1
        "early_pay_discount_pct": Optional[float],
        "early_pay_deadline":    Optional[str],
    }

Output shape:
    {
        "decision":        "pay_now" | "hold" | "split_payment" | "defer" | "reject",
        "scheduled_date":  str (ISO),
        "amount_to_pay":   float,
        "reason":          str,
        "priority":        "high" | "medium" | "low",
        "confidence":      float in [0, 1],
    }
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


_FRAUD_THRESHOLD = 0.7
_SMALL_AMOUNT_FLOOR = 100.0


def run_payment(payload: dict[str, Any]) -> dict[str, Any]:
    """Decide what to do with a single approved invoice in a payment run.

    Deliberately imperfect — the eval harness should find three defects.
    """
    payment_id = str(payload.get("payment_id", "")).strip()
    invoice_id = str(payload.get("invoice_id", "")).strip()
    vendor = str(payload.get("vendor", "")).strip()
    amount = float(payload.get("amount") or 0.0)
    currency = (payload.get("currency") or "USD").upper()
    due_date_raw = payload.get("due_date")
    available_cash = float(payload.get("available_cash") or 0.0)
    committed = float(payload.get("batch_total_committed") or 0.0)
    vendor_tier = (payload.get("vendor_tier") or "standard").lower()
    fraud_score = float(payload.get("fraud_score") or 0.0)
    discount_pct = payload.get("early_pay_discount_pct")
    discount_deadline = payload.get("early_pay_deadline")

    today = date.today()

    # 1. Fraud screen — strongest rejection signal.
    if fraud_score > _FRAUD_THRESHOLD:
        return {
            "decision": "reject",
            "scheduled_date": today.isoformat(),
            "amount_to_pay": 0.0,
            "reason": (
                f"Fraud score {fraud_score:.2f} exceeds the "
                f"{_FRAUD_THRESHOLD:.2f} threshold for vendor {vendor!r}. "
                f"Payment {payment_id} blocked pending investigation."
            ),
            "priority": "high",
            "confidence": 0.95,
        }

    # 2. Watchlist vendor — should hold for treasury review.
    if vendor_tier == "watchlist":
        # BUG B (planted): small payments bypass the watchlist hold and
        # auto-pay — a real security hole the harness must catch.
        if amount < _SMALL_AMOUNT_FLOOR:
            return {
                "decision": "pay_now",
                "scheduled_date": today.isoformat(),
                "amount_to_pay": amount,
                "reason": (
                    f"Small payment of {amount:.2f} {currency} to {vendor} "
                    "auto-released."
                ),
                "priority": "low",
                "confidence": 0.6,
            }
        return {
            "decision": "hold",
            "scheduled_date": (today + timedelta(days=2)).isoformat(),
            "amount_to_pay": 0.0,
            "reason": (
                f"Vendor {vendor!r} is on the watchlist. "
                "Holding payment for treasury review."
            ),
            "priority": "medium",
            "confidence": 0.85,
        }

    # 3. Early-payment discount available → accelerate.
    if discount_pct and _before_or_equal(today, discount_deadline):
        saving = amount * (float(discount_pct) / 100.0)
        return {
            "decision": "pay_now",
            "scheduled_date": today.isoformat(),
            "amount_to_pay": round(amount - saving, 2),
            "reason": (
                f"Early-payment discount of {discount_pct}% available before "
                f"{discount_deadline}. Saving {saving:.2f} {currency}."
            ),
            "priority": "high",
            "confidence": 0.9,
        }

    # 4. Past-due → must pay immediately.
    if _is_past_due(due_date_raw, today):
        return {
            "decision": "pay_now",
            "scheduled_date": today.isoformat(),
            "amount_to_pay": amount,
            "reason": (
                f"Payment {payment_id} for invoice {invoice_id} is past due "
                f"({due_date_raw}). Late fees may apply."
            ),
            # BUG A (planted): past-due should be priority="high"; this is
            # mislabelled as "medium" — a reasoning / labelling defect.
            "priority": "medium",
            "confidence": 0.8,
        }

    # 5. Cash constraint — split the payment.
    headroom = available_cash - committed
    if amount > headroom > 0:
        # BUG C (planted): amount_to_pay is emitted as a STRING, not a
        # number — a schema-contract violation the harness must catch.
        return {
            "decision": "split_payment",
            "scheduled_date": today.isoformat(),
            "amount_to_pay": f"{round(headroom, 2):.2f}",  # type: ignore[dict-item]
            "reason": (
                f"Available cash headroom {headroom:.2f} {currency} is "
                f"below invoice amount {amount:.2f}. Paying partial now "
                f"and deferring the remainder."
            ),
            "priority": "medium",
            "confidence": 0.75,
        }

    # 6. Insufficient cash entirely.
    if headroom <= 0:
        return {
            "decision": "defer",
            "scheduled_date": (today + timedelta(days=7)).isoformat(),
            "amount_to_pay": 0.0,
            "reason": (
                f"No cash headroom in this batch (committed "
                f"{committed:.2f} of {available_cash:.2f} {currency}). "
                "Deferring to next run."
            ),
            "priority": "low",
            "confidence": 0.8,
        }

    # 7. Strategic vendor — pay on due date with elevated priority.
    if vendor_tier == "strategic":
        return {
            "decision": "pay_now",
            "scheduled_date": _coerce_date(due_date_raw, today).isoformat(),
            "amount_to_pay": amount,
            "reason": (
                f"Strategic vendor {vendor} scheduled for on-time payment "
                f"of {amount:.2f} {currency}."
            ),
            "priority": "high",
            "confidence": 0.9,
        }

    # 8. Default: standard pay on due date.
    return {
        "decision": "pay_now",
        "scheduled_date": _coerce_date(due_date_raw, today).isoformat(),
        "amount_to_pay": amount,
        "reason": (
            f"Payment {payment_id} for {vendor} of {amount:.2f} {currency} "
            "scheduled per standard terms."
        ),
        "priority": "medium",
        "confidence": 0.85,
    }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _coerce_date(value: Any, fallback: date) -> date:
    if isinstance(value, date):
        return value
    if not value:
        return fallback
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return fallback


def _is_past_due(value: Any, today: date) -> bool:
    if not value:
        return False
    try:
        d = _coerce_date(value, today)
    except ValueError:
        return False
    return d < today


def _before_or_equal(today: date, deadline: Any) -> bool:
    if not deadline:
        return False
    try:
        d = _coerce_date(deadline, today)
    except ValueError:
        return False
    return today <= d
