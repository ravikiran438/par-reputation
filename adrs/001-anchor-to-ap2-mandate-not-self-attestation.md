# ADR-001: Anchor reputation to an AP2 mandate, not a self-issued attestation

**Status:** Accepted (v0.1)

## Context

Existing agent-reputation efforts derive trust from interaction records whose
proof of occurrence is **issued by the interacting parties**:

- **ARP** (`agent-reputation-protocol`, A2A Discussion #1631) inserts a row into
  its own ledger, you trust the registry operator. Its `THREAT_MODEL.md`
  concedes it does not defend against Sybil-across-registered-agents, portable
  attestation forgery, or cross-provider calibration.
- **MoltBridge** has the two agents co-sign an Ed25519 attestation, you trust
  the two parties are not the same operator.

Both are forgeable by a **single operator running both sides** (self-dealing):
two distinct keys can manufacture a clean, mutually-signed interaction history.

## Decision

Anchor each Verified Interaction Record to an **AP2 Closed Checkout Mandate**, a
credential signed by *user + merchant + payment network* (three independent
parties), rather than to a party-issued attestation. Minting a VIR therefore
requires a real, settled, multi-party transaction.

## Consequences

- **Self-dealing costs real settlement**, not a free signature.
- **Identity for free**: the mandate binds to durable operator/merchant identity
  (the "identity hardening" ARP defers).
- **Principal-privacy for free**: VIRs ride the Checkout Mandate (items), never
  the Payment Mandate (instrument).
- **Off-chain**: provenance comes from AP2/FIDO credentials, no blockchain.
- **Honest boundary**: payment-*gated* reviewing exists (ERC-8004 x402,
  on-chain). PAR's delta is off-chain portability, the full mandate chain
  (intent → checkout → payment), and principal-shielding.
- **Cost**: PAR depends on AP2 adoption for its anchor. Mitigation: accept any
  equivalent multi-party settlement VDC; AP2 is the first instantiation.
