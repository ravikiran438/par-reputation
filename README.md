# PAR: Provenance-Anchored Reputation

**Status:** Phase 0 prototype · Draft v0.1 · Apache-2.0

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20712592.svg)](https://doi.org/10.5281/zenodo.20712592)

A standardized **evidence layer** for agent reputation, built on one principle:
reputation evidence should be a **costly signal** (Spence's signaling theory,
Zahavi's handicap principle), credible because it is expensive to fake. The least
costly source of such a record is one a real economic **settlement** already
produces. PAR therefore anchors each reputation record to a **multi-party-signed
settlement credential with an item/payment split** rather than a self-issued
attestation. AP2's **Closed Checkout Mandate** (signed by user, merchant, and
payment network) is the first such credential; the construction is rail-agnostic.
No blockchain.

## Why

Agent-reputation scoring is an open, plural space: multiple efforts, each with its
own method, and the discussion is ongoing. That is healthy and should stay plural.
What is **not** standardized is the evidence layer *beneath* the scoring: the proof
of interaction. Today every system issues that proof itself, as either:

- a ledger row a registry inserts (trust the registry), or
- an attestation the two agents co-sign (trust they are not one operator).

Both are forgeable by a **single operator running both sides** (self-dealing).
PAR replaces that foundation with a **multi-party** artifact: an AP2 Closed
Checkout Mandate. To mint a reputation event you must have run a real, settled,
multi-party transaction.

PAR can be standardized on the **existing core specs (A2A + AP2)**, with **no
on-chain attestation**.

## What PAR is and is not

| | |
|---|---|
| **Is** | The Verified Interaction Record (VIR): a verifiable, identity-anchored, privacy-preserving proof-of-interaction, plus the validators that enforce it. |
| **Is not** | A scoring engine. Decay, multi-dimensional weighting, PageRank, and trust graphs are delegated to consuming engines and are out of scope here. |

## The Verified Interaction Record

```
VIR ── anchor ──> multi-party settlement credential, item/payment split (AP2 Checkout Mandate first)
    ── settlement ──> network/PSP-signed outcome attestation (cached, offline-verifiable)
    ── subject / counterparty ──> durable operator identities (DID/VDC/KYA), role-tagged
    ── context ──> checkout-derived scope only (skill, item_class)  [no payment data]
```

## Safety properties

`VIR-Groundedness`, `Operator-Anchoring`, `Principal-Privacy`,
`Settlement-Consistency`, `Role-Scoping`, `Input-Reproducibility`. Three
(Groundedness, Role-Scoping, Settlement-Consistency) are model-checked in
[`specification/Par.tla`](specification/Par.tla); all six are enforced in
[`src/par/validators/invariants.py`](src/par/validators/invariants.py) and
`verify.py`.

## Layout

```
par-reputation/
├── src/par/
│   ├── types/vir.py          # the VIR model (normative)
│   ├── canonical.py          # canonical-JSON content hashing
│   ├── mint.py               # mint_from_mandate(): the sole producer of VIRs
│   ├── verify.py             # verify() against checkout mandate + settlement oracle
│   ├── identity.py           # lightweight identity_depth ladder
│   ├── adapters/ap2.py       # real AP2 SDK CartMandate -> anchor mapping
│   ├── signals/independence.py  # operator-independence (self-dealing detection)
│   └── validators/invariants.py # the six safety properties
├── specification/Par.tla     # TLA+ model (3 invariants)
├── v1/manifest.json + SPEC.md # A2A extension surface
├── demo/                     # run_demo.py, independence_demo.py
├── tests/                    # pytest (27)
└── adrs/                     # 001 anchor, 002 independence, 003 settlement oracle
```

## Quick start

```bash
pip install -e ".[test]"
python -m pytest -q          # 25 run; 2 real-AP2 tests need the SDK (see below) for 27 total
python demo/run_demo.py            # mint -> verify -> chargeback
python demo/independence_demo.py   # operator-independence / self-dealing detection
python demo/eval_independence.py    # light eval: signal over canonical topologies
```

### Wiring a real AP2 mandate

PAR can ingest a genuine AP2 SDK `CartMandate` (the merchant-signed cart that AP2
finalizes into a closed Checkout Mandate) via `par.adapters.ap2`:

```bash
AP2_SDK_PATH=/path/to/AP2/code/sdk/python python -m pytest -q tests/test_ap2_real_mandate.py
```

The adapter maps only cart/checkout-derived fields into the PAR anchor; the AP2
PaymentMandate (instrument data) is never touched (Principal-Privacy).

## Relationship to prior work

PAR is complementary, not competitive. It gives existing scoring engines a common
input substrate:

- **Agent Reputation Protocol (ARP)** (<https://github.com/makito20256/arp-trust-substrate>,
  A2A Discussion #1631): its threat model explicitly defers identity and forgery
  resistance, which PAR supplies.
- **AP2** (<https://ap2-protocol.org/>): the first settlement-credential rail (the anchor); the construction is rail-agnostic.
- **A2A** (<https://a2a-protocol.org/>): the extension transport.
- **ERC-8004**: uses on-chain x402 payment-gated reviews; PAR is the off-chain,
  full-mandate-chain, principal-shielded alternative.

## Citation

If you reference this work, please cite the preprint:

> Kadaboina, R. K. (2026). *Provenance-Anchored Reputation: Grounding Agent
> Reputation in Real, Completed Payments.* Zenodo.
> <https://doi.org/10.5281/zenodo.20712592>

```bibtex
@misc{kadaboina2026par,
  author       = {Kadaboina, Ravi Kiran},
  title        = {Provenance-Anchored Reputation: Grounding Agent Reputation in Real, Completed Payments},
  year         = {2026},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.20712592},
  url          = {https://doi.org/10.5281/zenodo.20712592}
}
```

## License

Apache-2.0. See [LICENSE](LICENSE).
