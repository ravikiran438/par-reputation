"""Verified Interaction Record (VIR): the PAR evidence primitive.

A VIR is the atomic, verifiable claim that a reputation-bearing interaction
occurred between two identified operators, anchored to an AP2 Closed Checkout
Mandate rather than a self-issued attestation.

PAR standardizes only this evidence layer. Scoring is delegated to engines
(ARP, MoltBridge, others) that consume VIRs.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


VIR_VERSION = "0.1"

# Allowed external identity-proof types (the substrate PAR consumes, never builds).
IDENTITY_PROOFS = {"ap2.vdc", "fido.kya", "did.vc", "self_asserted"}

# The only anchor PAR accepts in v0.1: a *closed* AP2 checkout mandate.
ANCHOR_TYPE_CLOSED_CHECKOUT = "ap2.checkout_mandate.closed"


class Role(str, Enum):
    SERVICE_AGENT = "service_agent"
    BUYER_AGENT = "buyer_agent"


class SettlementStatus(str, Enum):
    PENDING = "pending"          # not yet settled
    SETTLED = "settled"          # payment cleared
    REFUNDED = "refunded"        # fully unwound by agreement (NOT adversarial; does not invalidate)
    PARTIAL_REFUND = "partial_refund"  # partially unwound (e.g. minor defect); non-invalidating
    CHARGED_BACK = "charged_back" # network-adjudicated dispute (adversarial; invalidates)
    DISPUTED = "disputed"        # dispute opened, not yet resolved (invalidates pending resolution)


# Outcomes that indicate the interaction did NOT legitimately complete.
INVALIDATING_STATUSES = {SettlementStatus.CHARGED_BACK, SettlementStatus.DISPUTED}


class Anchor(BaseModel):
    """The multi-party proof-of-interaction: a closed AP2 checkout mandate.

    The mandate is signed by user + merchant. The live *settlement status*,
    however, is a property of the payment network / PSP, not of the checkout
    mandate. PAR therefore obtains it from a separate, network-signed settlement
    attestation referenced by `settlement_ref` (outcome only, never the payment
    instrument), keeping the merchant out of the loop and the Payment Mandate
    private. `settlement_status` records the last attested outcome.
    """

    type: str = ANCHOR_TYPE_CLOSED_CHECKOUT
    mandate_ref: str = Field(..., description="Resolvable reference to the checkout mandate.")
    mandate_hash: str = Field(..., description="sha256:<hex> over the canonical mandate.")
    settlement_ref: Optional[str] = Field(
        None, description="Reference to the network/PSP-signed settlement attestation (outcome only)."
    )
    settlement_attestation: Optional[dict] = Field(
        None,
        description=(
            "The network/PSP-signed settlement outcome token, cached at mint. "
            "Being a signature, it is durable and re-verifiable OFFLINE: an honest "
            "agent's history does not depend on the issuer staying online. A fresh "
            "live query is needed only to detect a reversal AFTER mint."
        ),
    )
    settlement_status: SettlementStatus = SettlementStatus.SETTLED


class Party(BaseModel):
    """An identified operator (durable identity), never an ephemeral instance."""

    operator_id: str = Field(..., description="Durable operator identity, e.g. did:web:...")
    identity_proof: str = Field(..., description="One of IDENTITY_PROOFS.")
    identity_depth: int = Field(0, ge=0, le=4, description="0=self-asserted … 4=externally verified.")
    role: Role


class Context(BaseModel):
    """Checkout-Mandate-derived scope ONLY. No payment-mandate fields, no PII."""

    skill: str = Field(..., description="Capability scope of the claim, e.g. flight_booking.")
    item_class: Optional[str] = Field(None, description="Item-level class from the checkout mandate.")


class VerifiedInteractionRecord(BaseModel):
    vir_version: str = VIR_VERSION
    interaction_id: str
    anchor: Anchor
    subject: Party
    counterparty: Party
    context: Context
    evaluation_ref: Optional[str] = Field(None, description="Pointer to a DELEGATED scoring record.")
    issued_at: datetime
    issuer_sig: Optional[str] = Field(None, description="JWS over the VIR by the evaluating party.")

    model_config = {"extra": "forbid"}  # Principal-Privacy: no smuggled fields.
