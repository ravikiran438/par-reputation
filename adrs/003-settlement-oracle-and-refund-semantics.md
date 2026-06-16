# ADR-003: Settlement oracle and refund vs. chargeback semantics

**Status:** Accepted (v0.1)

## Context

Two flaws were identified in the original anchor design.

1. **Settlement oracle gap.** A VIR's anchor records a live settlement status
   (settled / refunded / charged_back), but settlement is a property of the
   payment network / PSP, *not* of the merchant-signed Checkout Mandate. The
   Phase-0 code conflated the two by storing `settlement_status` inside the
   checkout mandate. That is either (a) self-reported by the merchant, which a
   self-dealing merchant would exploit by never reporting its own chargeback, or
   (b) read from the Payment Mandate, which would break Principal-Privacy by
   linking the public VIR to private payment state.

2. **Refund treated as malfeasance.** Settlement-Consistency invalidated a VIR on
   both `refunded` and `charged_back`. But a refund is often *good* merchant
   behavior (returns, customer service), whereas a chargeback is a
   network-adjudicated dispute. Grouping them punishes generous return policies
   and incentivizes agents to block legitimate returns.

## Decision

**Settlement oracle.** Settlement status is obtained from a separate,
network/PSP-signed **settlement attestation** referenced by the anchor's
`settlement_ref`. It carries only the *outcome* (settled / refunded /
charged_back / disputed), never the payment instrument. The merchant is not the
oracle. `verify()` takes a `settlement_resolver` that returns this attestation;
the checkout mandate no longer carries settlement status.

- Privacy holds: an outcome bit is not the Payment Mandate's content; no ZK
  bridge is required to expose an outcome while hiding the instrument.
- Independence holds: the network signs the outcome, so a self-dealing merchant
  cannot suppress its own chargeback.

**Refund vs. chargeback.** Only adversarial reversals invalidate:
`Invalidating = {charged_back, disputed}`. A `refunded` VIR remains valid
evidence (well-formed) and is simply not in the active/settled state; the scoring
engine decides how to weight a completed-then-refunded interaction.

## Consequences

- Resolves the "settlement oracle paradox": live status without exposing the
  Payment Mandate and without trusting the merchant.
- Removes the perverse incentive against legitimate refunds.
- Anti-wash-trading is unaffected: wash-traders avoid reversals, so the change
  does not weaken Settlement-Consistency against them; chargeback/dispute still
  invalidate.
- Phase-0 stands in for the network signature: tests/demos supply a
  `settlement_resolver`; a production deployment verifies the attestation's
  signature against the network/PSP key.

## Fail-closed and availability (added after review)

The oracle is **fail-closed**: if the settlement attestation cannot be resolved,
or disagrees with the VIR's cached status, the VIR is **not active**. This defeats
a censoring merchant that withholds the attestation for a transaction it knows was
charged back ("PSP downtime"): withholding yields nothing, because absence of a
settlement proof is not a positive. Because both parties to an AP2 transaction
receive settlement confirmation, the attestation may be supplied by the
counterparty or a neutral settlement service, not only by the party under review,
so no single party has a monopoly on its own outcome.
