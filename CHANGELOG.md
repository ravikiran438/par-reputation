# Changelog

## v0.1.0 (Phase 0, 2026-06)

Initial prototype of Provenance-Anchored Reputation (PAR).

- Verified Interaction Record (VIR) model anchored to AP2 Closed Checkout Mandates.
- Six safety properties enforced in `validators/invariants.py` and modeled in `Par.tla`.
- `mint_from_mandate()` as the sole VIR producer; `verify()` against the live mandate.
- Settlement-consistency: chargebacks and disputes invalidate a VIR; refunds do not.
- Settlement oracle (ADR-003): live status from a network/PSP-signed settlement attestation (outcome only), separate from the checkout mandate and the merchant.
- Operator-independence signal (`signals/independence.py`, ADR-002): graph-based detection of reciprocal self-dealing clusters.
- Real AP2 SDK `CartMandate` adapter (`adapters/ap2.py`) plus integration tests.
- Lightweight `identity_depth` ladder (`identity.py`): proof and assurance map to depth 0..4 (heuristic default).
- A2A extension manifest and specification (`v1/`).
- 27 tests (2 real-AP2 tests skip without the SDK on path); end-to-end demos.
- Scope: evidence layer only; scoring is delegated to consuming engines.

## Preprint

The accompanying preprint (`preprint/`) tracks the project write-up independently of
the software version; its full revision history is in git. The current draft presents
the core idea (settlement-anchored evidence as a costly signal, AP2 as the first rail)
in an academic register. The earlier, longer draft with the extended security analysis
(threat model, settlement-oracle and transparency-log detail, the independence-signal
evaluation) remains available in git history.
