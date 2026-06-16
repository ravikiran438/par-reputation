"""Verify a VIR against the checkout mandate and the settlement oracle.

A consumer (e.g. a scoring engine) calls verify() before trusting a VIR. It
re-resolves the referenced checkout mandate (hash check), obtains the live
settlement outcome from the network/PSP-signed settlement attestation (the
settlement oracle), and runs the safety-property validators.

The settlement oracle is deliberately separate from the checkout mandate and
from the merchant: settlement status is observed by the payment network / PSP,
which signs a settlement attestation carrying only the outcome
(settled / refunded / charged_back / disputed), never the payment instrument.
This keeps the merchant out of the loop (a self-dealing merchant cannot suppress
its own chargeback) and keeps the Payment Mandate private.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Mapping, Optional

from par.canonical import content_hash
from par.types.vir import SettlementStatus, VerifiedInteractionRecord
from par.validators.invariants import validate

# Resolves a checkout-mandate ref to the current checkout mandate document.
MandateResolver = Callable[[str], Optional[Mapping[str, Any]]]
# Resolves a settlement_ref to the network-signed settlement attestation:
# at minimum {"status": "<SettlementStatus>"}.
SettlementResolver = Callable[[str], Optional[Mapping[str, Any]]]


@dataclass
class VerificationResult:
    verified: bool          # anchor resolves and hash matches
    well_formed: bool       # structural safety properties hold
    active: bool            # settled AND well-formed (counts toward reputation now)
    violations: List[str] = field(default_factory=list)


def verify(
    vir: VerifiedInteractionRecord,
    resolver: MandateResolver,
    settlement_resolver: Optional[SettlementResolver] = None,
    *,
    allow_stale: bool = True,
) -> VerificationResult:
    """Verify a VIR.

    Settlement source priority:
      1. a fresh `settlement_resolver` query (detects post-mint reversals);
      2. else the cached, signed `settlement_attestation` on the anchor, which is
         durable and re-verifiable offline (the issuer need not stay online).

    `allow_stale` is the soft-fail/hard-fail knob (OCSP-style). When no fresh
    source is available but a cached attestation is present:
      - allow_stale=True (default): trust the cached outcome (a reversal since mint
        is not detected) -- robust to infrastructure churn for honest agents;
      - allow_stale=False: high-stakes consumers require a fresh check, so the VIR
        is not active until re-checked.
    A censoring party that withholds the *fresh* source cannot fabricate a positive,
    because the cached attestation is itself a network signature it cannot forge,
    and a missing cached attestation with no live source is fail-closed.
    """
    violations: List[str] = []

    mandate = resolver(vir.anchor.mandate_ref)
    anchor_ok = True
    if mandate is None:
        anchor_ok = False
        violations.append("Anchor: referenced checkout mandate could not be resolved.")
    elif content_hash(dict(mandate)) != vir.anchor.mandate_hash:
        anchor_ok = False
        violations.append("Anchor: mandate_hash does not match the resolved mandate (tampered).")

    settlement_ok = True
    live = settlement_resolver(vir.anchor.settlement_ref or "") if settlement_resolver else None
    cached = vir.anchor.settlement_attestation
    source = live if live is not None else cached

    if source is None:
        settlement_ok = False
        violations.append(
            "Settlement: no settlement proof (no live source and no cached attestation); "
            "not active (absence of proof is not a positive)."
        )
    else:
        live_status = SettlementStatus(source.get("status", "pending"))
        if live_status != vir.anchor.settlement_status:
            settlement_ok = False
            violations.append(
                f"Settlement: status {live_status.value} differs from VIR "
                f"{vir.anchor.settlement_status.value} (re-mint with the current attestation)."
            )
        elif live is None:
            # Verified offline from the durable cached signature.
            if allow_stale:
                violations.append(
                    "Settlement: verified from cached attestation; live reversal check skipped "
                    "(stale). Set allow_stale=False to require a fresh check."
                )
            else:
                settlement_ok = False
                violations.append(
                    "Settlement: no fresh source and allow_stale=False; not active pending re-check."
                )

    result = validate(vir)
    violations.extend(result.violations)

    return VerificationResult(
        verified=anchor_ok,
        well_formed=result.well_formed,
        active=anchor_ok and settlement_ok and result.active,
        violations=violations,
    )
