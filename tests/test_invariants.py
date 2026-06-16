"""One test per safety property: the happy VIR holds, a targeted mutation breaks it."""

from par.mint import mint_from_mandate
from par.types.vir import Party, Role
from par.validators.invariants import (
    operator_anchoring,
    principal_privacy,
    role_scoping,
    settlement_consistency,
    validate,
    vir_groundedness,
)


def _vir(closed_mandate, subject, counterparty, context):
    return mint_from_mandate(closed_mandate, subject, counterparty, context)


def test_all_properties_hold_on_clean_vir(closed_mandate, subject, counterparty, context):
    vir = _vir(closed_mandate, subject, counterparty, context)
    res = validate(vir)
    assert res.well_formed and res.active and res.violations == []


def test_groundedness_breaks_on_bad_hash(closed_mandate, subject, counterparty, context):
    vir = _vir(closed_mandate, subject, counterparty, context)
    vir.anchor.mandate_hash = "sha256:notavalidhash"
    assert vir_groundedness(vir)


def test_operator_anchoring_breaks_on_ephemeral_id(closed_mandate, subject, counterparty, context):
    vir = _vir(closed_mandate, subject, counterparty, context)
    vir.subject.operator_id = "instance:run-42"  # ephemeral, not durable
    assert operator_anchoring(vir)


def test_principal_privacy_breaks_on_leaked_marker(closed_mandate, counterparty, context):
    # Smuggle a forbidden marker into an operator_id string.
    leaky_subject = Party(
        operator_id="did:web:merchant.example",
        identity_proof="ap2.vdc",
        identity_depth=3,
        role=Role.SERVICE_AGENT,
    )
    vir = mint_from_mandate(closed_mandate, leaky_subject, counterparty, context)
    vir.context.item_class = "card_number-ending-4242"
    assert principal_privacy(vir)


def test_role_scoping_breaks_when_same_role(closed_mandate, subject, context):
    same_role_counterparty = Party(
        operator_id="did:web:other.example",
        identity_proof="ap2.vdc",
        identity_depth=2,
        role=Role.SERVICE_AGENT,  # both service_agent -> invalid
    )
    vir = mint_from_mandate(closed_mandate, subject, same_role_counterparty, context)
    assert role_scoping(vir)


def test_settlement_consistency_chargeback_invalidates_refund_does_not(
    closed_mandate, subject, counterparty, context
):
    from par.types.vir import SettlementStatus

    vir = _vir(closed_mandate, subject, counterparty, context)
    vir.anchor.settlement_status = SettlementStatus.REFUNDED
    assert settlement_consistency(vir) == []          # refund is NOT adversarial
    vir.anchor.settlement_status = SettlementStatus.CHARGED_BACK
    assert settlement_consistency(vir)                # chargeback invalidates
    vir.anchor.settlement_status = SettlementStatus.DISPUTED
    assert settlement_consistency(vir)                # open dispute invalidates
    vir.anchor.settlement_status = SettlementStatus.PARTIAL_REFUND
    assert settlement_consistency(vir) == []          # partial refund is NOT adversarial
