"""Operator-independence signal.

AP2 mandates prove a user + merchant + payment network *signed*; they do NOT
prove the buyer operator and merchant operator are *independent*. A single actor
running two verified entities can mint clean VIRs by transacting real money
between them (self-dealing). This module turns the VIR set into a transaction
graph and computes, per operator, how independent its reputation evidence is.

This is an EVIDENCE-INTEGRITY signal (a property of the VIR graph), not a
reputation score. PAR exposes it alongside VIRs so any scoring engine can
discount or flag concentrated, reciprocal self-dealing clusters.

Score is in [0, 1]: 1 = diverse, independent counterparties; low = reputation
dominated by a single, reciprocal counterparty (the wash-trading signature).
The boolean `flags` are the primary actionable output; the score is a summary.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from par.types.vir import VerifiedInteractionRecord

MIN_INTERACTIONS = 3            # below this, evidence is too thin to judge
HIGH_CONCENTRATION = 0.60       # top counterparty share that trips a flag
RECIPROCAL_BALANCE = 0.60       # balance of mutual flow that trips a flag
LOW_DIVERSITY_RATIO = 0.34      # distinct/total below this is low diversity

# Score weights: diversity vs. (inverse) self-dealing indicator.
_W_DIVERSITY = 0.5
_W_INDEPENDENCE = 0.5


@dataclass
class IndependenceReport:
    operator_id: str
    n_inbound: int                       # VIRs where this operator is the subject
    distinct_counterparties: int
    top_counterparty: Optional[str]
    top_share: float                     # fraction of inbound from the top counterparty
    normalized_entropy: float            # counterparty diversity, 0..1
    reciprocal_balance: float            # how mutual the top pair's flow is, 0..1
    self_dealing_indicator: float        # top_share * reciprocal_balance, 0..1
    score: Optional[float]               # 0..1, None if insufficient data
    flags: List[str] = field(default_factory=list)


def _normalized_entropy(counts: Counter) -> float:
    n = sum(counts.values())
    distinct = len(counts)
    if distinct <= 1 or n == 0:
        return 0.0
    h = -sum((c / n) * math.log(c / n) for c in counts.values())
    return h / math.log(distinct)


def operator_independence(
    operator_id: str, virs: Iterable[VerifiedInteractionRecord]
) -> IndependenceReport:
    virs = list(virs)
    inbound = [v for v in virs if v.subject.operator_id == operator_id]
    n = len(inbound)

    cp_counts = Counter(v.counterparty.operator_id for v in inbound)
    distinct = len(cp_counts)
    top_counterparty, top_count = (cp_counts.most_common(1)[0] if cp_counts else (None, 0))
    top_share = (top_count / n) if n else 0.0
    norm_entropy = _normalized_entropy(cp_counts)

    # Reciprocity of the dominant pair: how balanced is forward vs reverse flow?
    reciprocal_balance = 0.0
    if top_counterparty is not None:
        forward = top_count
        reverse = sum(
            1
            for v in virs
            if v.subject.operator_id == top_counterparty
            and v.counterparty.operator_id == operator_id
        )
        if forward + reverse > 0:
            reciprocal_balance = (min(forward, reverse) / (forward + reverse)) * 2.0  # 0..1

    self_dealing = top_share * reciprocal_balance

    flags: List[str] = []
    if n < MIN_INTERACTIONS:
        flags.append("insufficient_data")
    if top_share >= HIGH_CONCENTRATION:
        flags.append("high_concentration")
    if top_share >= 0.5 and reciprocal_balance >= RECIPROCAL_BALANCE:
        flags.append("reciprocal_cluster")  # the self-dealing signature
    if n >= MIN_INTERACTIONS and distinct and (distinct / n) < LOW_DIVERSITY_RATIO:
        flags.append("low_diversity")

    score: Optional[float]
    if n == 0:
        score = None
    else:
        score = max(0.0, min(1.0, _W_DIVERSITY * norm_entropy + _W_INDEPENDENCE * (1.0 - self_dealing)))

    return IndependenceReport(
        operator_id=operator_id,
        n_inbound=n,
        distinct_counterparties=distinct,
        top_counterparty=top_counterparty,
        top_share=round(top_share, 4),
        normalized_entropy=round(norm_entropy, 4),
        reciprocal_balance=round(reciprocal_balance, 4),
        self_dealing_indicator=round(self_dealing, 4),
        score=None if score is None else round(score, 4),
        flags=flags,
    )


def flag_self_dealing(virs: Iterable[VerifiedInteractionRecord]) -> List[IndependenceReport]:
    """Return independence reports for every subject operator that trips a self-dealing flag."""
    virs = list(virs)
    operators = {v.subject.operator_id for v in virs}
    reports = [operator_independence(op, virs) for op in operators]
    return [
        r for r in reports
        if "reciprocal_cluster" in r.flags or "high_concentration" in r.flags
    ]
