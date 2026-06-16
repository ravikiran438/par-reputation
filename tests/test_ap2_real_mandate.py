"""Integration test: mint a VIR from a REAL AP2 SDK CartMandate.

Skips cleanly if the AP2 SDK is not importable (e.g. SDK path not set).
The 3.10 shim for datetime.UTC is applied before importing the SDK.
"""
import datetime
import os
import sys

import pytest

datetime.UTC = getattr(datetime, "UTC", datetime.timezone.utc)  # 3.10 shim

_AP2_SDK = os.environ.get("AP2_SDK_PATH")
if _AP2_SDK and _AP2_SDK not in sys.path:
    sys.path.insert(0, _AP2_SDK)

ap2 = pytest.importorskip("ap2.models.mandate", reason="AP2 SDK not on path")

from ap2.models.mandate import CartContents, CartMandate
from ap2.models.payment_request import (
    PaymentCurrencyAmount,
    PaymentDetailsInit,
    PaymentItem,
    PaymentMethodData,
    PaymentRequest,
)

from par.adapters.ap2 import anchor_mapping_from_cart_mandate
from par.mint import mint_from_mandate
from par.types.vir import Context, Party, Role
from par.verify import verify


def _real_cart_mandate(signed=True):
    amount = PaymentCurrencyAmount(currency="USD", value=423.00)
    total = PaymentItem(label="Flight SFO->JFK (non-refundable)", amount=amount)
    details = PaymentDetailsInit(id="cart-real-001", display_items=[total], total=total)
    pr = PaymentRequest(method_data=[PaymentMethodData(supported_methods="basic-card")], details=details)
    cc = CartContents(id="cart-real-001", user_cart_confirmation_required=True,
                      payment_request=pr, cart_expiry="2026-06-14T00:00:00Z",
                      merchant_name="TravelMart")
    return CartMandate(contents=cc,
                       merchant_authorization="eyJhbGciOiJFUzI1NiJ9.X.SIG" if signed else None)


def _parties_ctx():
    s = Party(operator_id="did:web:travelmart.example", identity_proof="ap2.vdc",
              identity_depth=3, role=Role.SERVICE_AGENT)
    c = Party(operator_id="did:web:assistant.example", identity_proof="ap2.vdc",
              identity_depth=2, role=Role.BUYER_AGENT)
    ctx = Context(skill="flight_booking", item_class="non_refundable_fare")
    return s, c, ctx


def test_mint_vir_from_real_ap2_cart_mandate():
    cm = _real_cart_mandate(signed=True)
    mapping = anchor_mapping_from_cart_mandate(cm)
    assert "settlement_status" not in mapping  # settlement is not part of the checkout mandate
    s, c, ctx = _parties_ctx()
    vir = mint_from_mandate(mapping, s, c, ctx, settlement_status="settled",
                            settlement_ref="ap2://settle/real-001")
    res = verify(vir, lambda ref: mapping if ref == mapping["mandate_id"] else None,
                 lambda ref: {"status": "settled"})
    assert res.verified and res.well_formed and res.active
    # principal-privacy: no payment-instrument data anywhere in the VIR
    assert "payment_response" not in vir.model_dump_json()


def test_unsigned_cart_mandate_rejected():
    cm = _real_cart_mandate(signed=False)
    with pytest.raises(ValueError):
        anchor_mapping_from_cart_mandate(cm)
