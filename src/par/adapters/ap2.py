"""Adapter: a real AP2 CartMandate -> the mandate mapping PAR.mint consumes.

This keeps PAR rail-neutral (mint() takes a plain mapping) while letting it
ingest a genuine AP2 SDK object. Only Checkout/cart-derived fields are mapped;
the AP2 PaymentMandate (instrument data) is never touched (Principal-Privacy).

The AP2 SDK calls the merchant-signed cart a `CartMandate` (the v0.2 spec docs
call the same artifact a closed Checkout Mandate). We map it to PAR's anchor
type `ap2.checkout_mandate.closed`.

Usage:
    from par.adapters.ap2 import anchor_mapping_from_cart_mandate
    mapping = anchor_mapping_from_cart_mandate(cart_mandate, settlement_status="settled")
    vir = mint_from_mandate(mapping, subject, counterparty, context)
"""

from __future__ import annotations

from typing import Any, Mapping

# Forbidden because they belong to the AP2 PaymentMandate, not the cart.
_PAYMENT_ONLY = {"payment_response", "user_authorization", "payment_mandate_contents"}


def anchor_mapping_from_cart_mandate(cart_mandate: Any) -> Mapping[str, Any]:
    """Map an ap2.models.mandate.CartMandate to PAR's checkout-mandate mapping.

    Accepts the real SDK object (duck-typed) so PAR need not import the AP2 SDK.
    Raises ValueError if the cart is unsigned or carries payment-instrument data.

    Note: settlement *status* is NOT part of the checkout mandate. It comes from
    the network-signed settlement attestation and is passed separately to
    mint_from_mandate(settlement_status=..., settlement_ref=...).
    """
    contents = cart_mandate.contents

    if getattr(cart_mandate, "merchant_authorization", None) is None:
        raise ValueError("CartMandate is unsigned (no merchant_authorization); not a valid anchor.")

    # Items are Checkout-derived (labels/amounts), never the user's instrument.
    items = []
    details = contents.payment_request.details
    for it in getattr(details, "display_items", []) or []:
        amt = getattr(it, "amount", None)
        items.append({
            "label": it.label,
            "currency": getattr(amt, "currency", None),
            "value": getattr(amt, "value", None),
        })

    mapping = {
        "type": "ap2.checkout_mandate.closed",
        "mandate_id": contents.id,
        "merchant": contents.merchant_name,
        "items": items,
        # evidence that a merchant actually signed the cart (multi-party anchor)
        "merchant_authorization_present": True,
    }

    # Defense-in-depth: never let a payment-only field slip into the anchor.
    for key in _PAYMENT_ONLY:
        if key in mapping:
            raise ValueError(f"payment-only field '{key}' must not enter the PAR anchor.")

    return mapping
