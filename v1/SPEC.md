# PAR v1: Extension Specification (Draft v0.1)

**Extension URI:** `https://par-reputation.dev/extensions/par/v1`

Provenance-Anchored Reputation (PAR) standardizes the **evidence layer** beneath
agent-reputation scoring: a verifiable, forgery-resistant, identity-anchored,
privacy-preserving record that an interaction occurred and who was behind it.

PAR is **not** a scoring system. Scoring is an open, plural space (ARP,
MoltBridge, and others); PAR gives every engine a common, trustworthy input.

## The Verified Interaction Record (VIR)

A VIR is anchored to an **AP2 Closed Checkout Mandate**: a credential signed by
*user + merchant + payment network*, rather than a self-issued attestation.
Minting a VIR therefore requires a real, settled, multi-party transaction.

See `../src/par/types/vir.py` for the normative model. Fields:

| Field | Meaning |
|---|---|
| `anchor` | The closed checkout mandate ref + sha256 hash + live settlement status |
| `subject` / `counterparty` | Durable operator identities, identity proof, depth, role |
| `context` | Checkout-derived scope only (`skill`, `item_class`), **no payment data** |
| `evaluation_ref` | Optional pointer to a *delegated* scoring record |

## Safety properties (normative)

1. **VIR-Groundedness**: no VIR without a referenced, hash-verified closed checkout mandate.
2. **Operator-Anchoring**: bound to a durable operator identity via an external proof; never an ephemeral instance.
3. **Principal-Privacy**: no Payment-Mandate field or principal PII in a VIR.
4. **Settlement-Consistency**: a refunded/charged-back anchor invalidates its VIR.
5. **Role-Scoping**: signals are role- and skill-tagged; the two parties hold opposite commerce roles.
6. **Input-Reproducibility**: a subject's VIR set is independently re-verifiable from the mandates it references.

Properties 1–5 are model-checked in `../specification/Par.tla` and enforced in
`../src/par/validators/invariants.py`.

## AgentCard integration

A PAR-aware agent declares, under `capabilities.extensions[]`:

```jsonc
{
  "uri": "https://par-reputation.dev/extensions/par/v1",
  "required": false,
  "config": {
    "operator_id": "did:web:merchant.example",
    "vir_endpoint": "https://merchant.example/.well-known/par/virs",
    "derived": { "engine": "arp-compatible", "scores_ref": "https://…/scores" }
  }
}
```

The `derived` block is produced by a delegated engine; PAR guarantees the
*inputs* (VIRs) are verifiable, not the scoring formula.

## Operator-independence signal (evidence integrity)

AP2 anchoring proves three parties *signed*, not that the buyer and merchant
operators are *independent*. PAR therefore exposes an **operator-independence
signal** computed from the VIR graph (see `../src/par/signals/independence.py`
and ADR-002): counterparty diversity (normalized entropy), top-counterparty
concentration, reciprocal balance of the dominant pair, a composite score in
[0,1], and flags (`high_concentration`, `reciprocal_cluster`, `low_diversity`,
`insufficient_data`). A two-entity wash-trading cluster surfaces as low
independence with a `reciprocal_cluster` flag. This is *detection*, not
prevention, and is an evidence-integrity signal, not a reputation score.

## Identity-depth ladder (lightweight)

`identity_depth` (0..4) grades the *external identity proof* behind an operator.
A lightweight heuristic ladder ships in `../src/par/identity.py`: `self_asserted`
= 0, `did.vc` = 1, `fido.kya` / `ap2.vdc` = 2, with an optional assurance bump
(e.g. NIST IAL2 +1, IAL3 +2), clamped at 4. This is a starting default, not a
calibrated standard. PAR emits the depth; scoring engines decide the weight.

## Verifiable evidence availability

The `vir_endpoint` is queryable (filter by status and time window) and serves a
**signed summary**. To keep that summary from being a self-asserted claim, a
subject's VIR set is maintained as an append-only Merkle log with a witnessed
signed tree head, following Certificate Transparency (RFC 6962 / RFC 9162) and
authenticated data structures: the endpoint serves O(log n) inclusion and
consistency proofs against a root witnessed by the settlement oracle or an
independent witness, so omission and equivocation are detectable and audit cost is
logarithmic, not a full download. The settlement-freshness model follows OCSP
(RFC 6960): the cached attestation is a stapled response, the staleness window its
validity period, and a hard-fail consumer is must-staple.

## Relationship to other standards

- **AP2**: supplies the anchor (Closed Checkout Mandate VDC). PAR consumes it; it does not rebuild payments.
- **A2A**: the extension transport. PAR is registry-agnostic.
- **No blockchain.** Provenance comes from AP2/FIDO credentials, not an on-chain ledger.
