# ADR-002: Operator-independence signal over the VIR graph

**Status:** Accepted (v0.1)

## Context

Anchoring reputation to an AP2 mandate (ADR-001) proves a user, a merchant, and a
payment network *signed* a transaction. It does **not** prove the buyer operator
and the merchant operator are *independent*. A single actor can stand up two
separately-verified (KYA'd) entities and run genuine, settled, non-reversed
transactions between them to mint clean VIRs, self-dealing that the anchor alone
cannot detect. This is the residual gap acknowledged in the design note and
preprint.

## Decision

Expose an **operator-independence signal** computed purely from the VIR graph (who
transacted with whom), alongside VIRs. For a subject operator it reports:

- counterparty **diversity** (normalized entropy of its inbound counterparties),
- **concentration** (share from the single top counterparty),
- **reciprocal balance** of the dominant pair (the wash-trading signature is high
  concentration *and* balanced mutual flow),
- a composite **score** in [0, 1], and boolean **flags**
  (`high_concentration`, `reciprocal_cluster`, `low_diversity`,
  `insufficient_data`).

This is an **evidence-integrity** signal, a property of the interaction graph,
not a reputation score. PAR still delegates scoring; it provides this signal so
engines can discount or reject concentrated, reciprocal self-dealing.

## Consequences

- Directly attacks the residual self-dealing surface: a two-entity wash-trading
  cluster shows up as low independence with a `reciprocal_cluster` flag.
- Stays within PAR's remit (evidence integrity, like ARP's ledger-level
  anti-collusion checks) without specifying reputation scoring.
- **Honest bound:** this is *detection*, not *prevention*. A sufficiently patient
  actor who spreads self-dealing across many entities and dilutes reciprocity can
  reduce the signal. Independence raises the cost and surfaces the obvious cases;
  it is not a categorical anti-Sybil guarantee.
- The `flags` are the primary actionable output; the continuous `score` is a
  summary for ranking/threshold use.
