"""Mint a VIR from an AP2 Closed Checkout Mandate.

Phase 0 uses a minimal mandate shape standing in for a real AP2 Checkout
Mandate VDC. The mint path is deliberately the *only* way to create a VIR, so
that every VIR is grounded in a multi-party settlement artifact rather than a
self-issued attestation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from par.canonical import content_hash
from par.types.vir import (
    ANCHOR_TYPE_CLOSED_CHECKOUT,
    Anchor,
    Context,
    Party,
    SettlementStatus,
    VerifiedInteractionRecord,
)


class MandateError(ValueError):
    pass


def _require_closed_checkout(mandate: Mapping[str, Any]) -> None:
    if mandate.get("type") != ANCHOR_TYPE_CLOSED_CHECKOUT:
        raise MandateError(
            f"mandate.type must be {ANCHOR_TYPE_CLOSED_CHECKOUT}; got {mandate.get('type')!r}"
        )
    for key in ("mandate_id", "merchant"):
        if key not in mandate:
            raise MandateError(f"mandate missing required field: {key}")
    # Principal-Privacy at the source: the checkout mandate must NOT carry payment data.
    if "payment_mandate" in mandate or "instrument" in mandate:
        raise MandateError("checkout mandate must not embed payment-mandate / instrument data")


def mint_from_mandate(
    mandate: Mapping[str, Any],
    subject: Party,
    counterparty: Party,
    context: Context,
    *,
    settlement_status: SettlementStatus | str = SettlementStatus.SETTLED,
    settlement_ref: str | None = None,
    settlement_attestation: dict | None = None,
    evaluation_ref: str | None = None,
    issuer_sig: str | None = None,
) -> VerifiedInteractionRecord:
    """Create a VIR anchored to a closed AP2 checkout mandate.

    `mandate` is the resolved Closed Checkout Mandate (merchant-signed cart). Its
    hash is computed over the canonical JSON so the anchor is tamper-evident.

    The settlement *status* is NOT part of the checkout mandate: it is a property
    of the payment network / PSP and is asserted by a separate settlement
    attestation (referenced by `settlement_ref`). It is passed in here rather than
    read from the mandate.
    """
    _require_closed_checkout(mandate)

    anchor = Anchor(
        type=ANCHOR_TYPE_CLOSED_CHECKOUT,
        mandate_ref=str(mandate["mandate_id"]),
        mandate_hash=content_hash(dict(mandate)),
        settlement_ref=settlement_ref,
        settlement_attestation=settlement_attestation,
        settlement_status=SettlementStatus(settlement_status),
    )

    return VerifiedInteractionRecord(
        interaction_id=str(uuid.uuid4()),
        anchor=anchor,
        subject=subject,
        counterparty=counterparty,
        context=context,
        evaluation_ref=evaluation_ref,
        issued_at=datetime.now(timezone.utc),
        issuer_sig=issuer_sig,
    )
