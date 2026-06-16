import pytest

from par.mint import MandateError, mint_from_mandate
from par.types.vir import SettlementStatus
from par.verify import verify


def _mandate_resolver(mandate):
    return lambda ref: mandate if ref == mandate["mandate_id"] else None


def _settle_resolver(status):
    return lambda ref: {"status": status}


def test_mint_produces_grounded_active_vir(closed_mandate, subject, counterparty, context):
    vir = mint_from_mandate(closed_mandate, subject, counterparty, context,
                            settlement_status="settled", settlement_ref="ap2://settle/abc")
    assert vir.anchor.mandate_hash.startswith("sha256:")
    res = verify(vir, _mandate_resolver(closed_mandate), _settle_resolver("settled"))
    assert res.verified and res.well_formed and res.active
    assert res.violations == []


def test_mint_rejects_non_closed_checkout(subject, counterparty, context):
    bad = {"type": "ap2.checkout_mandate.open", "mandate_id": "x", "merchant": "m"}
    with pytest.raises(MandateError):
        mint_from_mandate(bad, subject, counterparty, context)


def test_mint_rejects_mandate_with_payment_data(subject, counterparty, context):
    leaky = {"type": "ap2.checkout_mandate.closed", "mandate_id": "x", "merchant": "m",
             "instrument": "4111111111111111"}
    with pytest.raises(MandateError):
        mint_from_mandate(leaky, subject, counterparty, context)


def test_tampered_mandate_fails_hash(closed_mandate, subject, counterparty, context):
    vir = mint_from_mandate(closed_mandate, subject, counterparty, context)
    tampered = dict(closed_mandate, merchant="did:web:evil.example")
    res = verify(vir, _mandate_resolver(tampered))
    assert not res.verified
    assert any("tampered" in v for v in res.violations)


def test_unresolvable_anchor(closed_mandate, subject, counterparty, context):
    vir = mint_from_mandate(closed_mandate, subject, counterparty, context)
    res = verify(vir, lambda ref: None)
    assert not res.verified and not res.active


def test_chargeback_invalidates(closed_mandate, subject, counterparty, context):
    # Minted as settled; the settlement oracle later reports a chargeback.
    vir = mint_from_mandate(closed_mandate, subject, counterparty, context,
                            settlement_status="charged_back", settlement_ref="ap2://settle/abc")
    res = verify(vir, _mandate_resolver(closed_mandate), _settle_resolver("charged_back"))
    assert res.well_formed          # the interaction evidence is still well-formed
    assert not res.active           # but a chargeback invalidates it
    assert any("Settlement-Consistency" in v for v in res.violations)


def test_refund_does_not_invalidate(closed_mandate, subject, counterparty, context):
    # A refund is NOT adversarial: the interaction completed and was unwound by agreement.
    vir = mint_from_mandate(closed_mandate, subject, counterparty, context,
                            settlement_status="refunded", settlement_ref="ap2://settle/abc")
    res = verify(vir, _mandate_resolver(closed_mandate), _settle_resolver("refunded"))
    assert res.well_formed
    assert not any("Settlement-Consistency" in v for v in res.violations)  # refund is not invalidating
    assert not res.active           # not "active/in-good-standing", but valid evidence the engine interprets


def test_oracle_status_drift_flagged(closed_mandate, subject, counterparty, context):
    # VIR cached "settled" but the live oracle now says "charged_back".
    vir = mint_from_mandate(closed_mandate, subject, counterparty, context,
                            settlement_status="settled", settlement_ref="ap2://settle/abc")
    res = verify(vir, _mandate_resolver(closed_mandate), _settle_resolver("charged_back"))
    assert any("differs from VIR" in v for v in res.violations)
    assert not res.active


def test_withheld_settlement_with_no_cache_is_not_active(closed_mandate, subject, counterparty, context):
    # Fail-closed: no live source and no cached attestation -> not active.
    vir = mint_from_mandate(closed_mandate, subject, counterparty, context,
                            settlement_status="settled", settlement_ref="ap2://settle/abc")
    res = verify(vir, _mandate_resolver(closed_mandate), lambda ref: None)
    assert not res.active
    assert any("no settlement proof" in v for v in res.violations)


def test_cached_attestation_survives_infrastructure_churn(closed_mandate, subject, counterparty, context):
    # Honest agent: the signed settlement token is cached on the VIR. Even with NO
    # live oracle (PSP gone / API changed), the durable signature verifies offline.
    vir = mint_from_mandate(closed_mandate, subject, counterparty, context,
                            settlement_status="settled", settlement_ref="ap2://settle/abc",
                            settlement_attestation={"status": "settled", "sig": "<network-jws>"})
    # No live resolver at all; default allow_stale=True trusts the cached signature.
    res = verify(vir, _mandate_resolver(closed_mandate), settlement_resolver=None)
    assert res.active
    assert any("cached attestation" in v for v in res.violations)  # stale note, not invalidation

    # High-stakes consumer demands a fresh reversal check: not active until re-checked.
    res2 = verify(vir, _mandate_resolver(closed_mandate), settlement_resolver=None, allow_stale=False)
    assert not res2.active
