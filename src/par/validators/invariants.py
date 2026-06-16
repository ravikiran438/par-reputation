"""PAR safety-property validators.

Each function maps to a named property in specification/Par.tla and returns a
list of human-readable violations (empty == holds).

Structural properties (Groundedness, Operator-Anchoring, Principal-Privacy,
Role-Scoping) determine whether a VIR is *well-formed evidence*.
Settlement-Consistency determines whether a well-formed VIR is *active* (counts
toward reputation right now).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from par.types.vir import (
    ANCHOR_TYPE_CLOSED_CHECKOUT,
    IDENTITY_PROOFS,
    INVALIDATING_STATUSES,
    Role,
    SettlementStatus,
    VerifiedInteractionRecord,
)

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
# Durable operator identity: a DID or an https URL, never an ephemeral instance.
_DURABLE_ID_RE = re.compile(r"^(did:[a-z0-9]+:.+|https://.+)$")
# Markers that would indicate payment-instrument / principal data leaking in.
_FORBIDDEN_MARKERS = ("pan", "card_number", "payment_mandate", "instrument", "cvv", "ssn")


@dataclass
class ValidationResult:
    well_formed: bool
    active: bool
    violations: List[str] = field(default_factory=list)


def vir_groundedness(vir: VerifiedInteractionRecord) -> List[str]:
    """No reputation event without a referenced, hash-verified closed checkout mandate."""
    v: List[str] = []
    if vir.anchor.type != ANCHOR_TYPE_CLOSED_CHECKOUT:
        v.append(f"VIR-Groundedness: anchor.type must be {ANCHOR_TYPE_CLOSED_CHECKOUT}.")
    if not vir.anchor.mandate_ref:
        v.append("VIR-Groundedness: anchor.mandate_ref is required.")
    if not _HASH_RE.match(vir.anchor.mandate_hash or ""):
        v.append("VIR-Groundedness: anchor.mandate_hash must be sha256:<64-hex>.")
    return v


def operator_anchoring(vir: VerifiedInteractionRecord) -> List[str]:
    """Every VIR binds to a durable operator identity via an external proof."""
    v: List[str] = []
    for label, party in (("subject", vir.subject), ("counterparty", vir.counterparty)):
        if not _DURABLE_ID_RE.match(party.operator_id or ""):
            v.append(f"Operator-Anchoring: {label}.operator_id must be a DID or https URL (durable).")
        if party.identity_proof not in IDENTITY_PROOFS:
            v.append(f"Operator-Anchoring: {label}.identity_proof '{party.identity_proof}' not recognized.")
        if party.identity_proof == "self_asserted" and party.identity_depth != 0:
            v.append(f"Operator-Anchoring: {label} self_asserted must have identity_depth 0.")
    return v


def principal_privacy(vir: VerifiedInteractionRecord) -> List[str]:
    """No Payment-Mandate field or principal PII may enter a VIR."""
    v: List[str] = []
    blob = vir.model_dump_json().lower()
    for marker in _FORBIDDEN_MARKERS:
        if marker in blob:
            v.append(f"Principal-Privacy: forbidden marker '{marker}' present in VIR.")
    return v


def role_scoping(vir: VerifiedInteractionRecord) -> List[str]:
    """Signals are role- and skill-tagged; the two parties hold opposite commerce roles."""
    v: List[str] = []
    roles = {vir.subject.role, vir.counterparty.role}
    if roles != {Role.SERVICE_AGENT, Role.BUYER_AGENT}:
        v.append("Role-Scoping: subject and counterparty must be one service_agent and one buyer_agent.")
    if not vir.context.skill:
        v.append("Role-Scoping: context.skill is required to scope the claim.")
    return v


def settlement_consistency(vir: VerifiedInteractionRecord) -> List[str]:
    """An adversarial reversal (chargeback/dispute) invalidates a VIR.

    A *refund* is NOT adversarial: it is an interaction that completed and was
    then unwound by agreement (e.g. a return). It does not invalidate the VIR; it
    is recorded as a distinct outcome the scoring engine may interpret. Only
    network-adjudicated reversals (chargeback, open dispute) invalidate.
    """
    v: List[str] = []
    status = vir.anchor.settlement_status
    if status in INVALIDATING_STATUSES:
        v.append(f"Settlement-Consistency: anchor settlement_status is {status.value}; VIR is invalidated.")
    return v


STRUCTURAL = (vir_groundedness, operator_anchoring, principal_privacy, role_scoping)


def validate(vir: VerifiedInteractionRecord) -> ValidationResult:
    structural_violations: List[str] = []
    for check in STRUCTURAL:
        structural_violations.extend(check(vir))

    settlement_violations = settlement_consistency(vir)
    well_formed = not structural_violations
    active = (
        well_formed
        and not settlement_violations
        and vir.anchor.settlement_status == SettlementStatus.SETTLED
    )
    return ValidationResult(
        well_formed=well_formed,
        active=active,
        violations=structural_violations + settlement_violations,
    )
