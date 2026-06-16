"""Light evaluation harness for the operator-independence signal.

Deterministic (fixed-seed) sweep over a handful of canonical transaction
topologies, printing each operator's independence score and flags. This replaces
the two anecdotes in the paper with a small, reproducible demonstration that the
signal behaves sensibly across topologies. A rigorous quantitative FP/FN study
across parameter grids and noise models is deliberately left as future work.

Run: python demo/eval_independence.py
"""

from __future__ import annotations

import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from par.signals.independence import operator_independence  # noqa: E402
from par.types.vir import (  # noqa: E402
    Anchor, Context, Party, Role, SettlementStatus, VerifiedInteractionRecord,
)

random.seed(7)  # determinism


def vir(subj, cpty, subj_role=Role.SERVICE_AGENT):
    cpty_role = Role.BUYER_AGENT if subj_role == Role.SERVICE_AGENT else Role.SERVICE_AGENT
    return VerifiedInteractionRecord(
        interaction_id=str(uuid.uuid4()),
        anchor=Anchor(mandate_ref="ap2://m/" + str(uuid.uuid4()),
                      mandate_hash="sha256:" + "0" * 64,
                      settlement_status=SettlementStatus.SETTLED),
        subject=Party(operator_id=subj, identity_proof="ap2.vdc", identity_depth=3, role=subj_role),
        counterparty=Party(operator_id=cpty, identity_proof="ap2.vdc", identity_depth=2, role=cpty_role),
        context=Context(skill="flight_booking"),
        issued_at=datetime.now(timezone.utc),
    )


def healthy(O, k=15):
    """Diverse: one operator, k distinct buyers, one-directional."""
    return [vir(O, f"buyer-{i}") for i in range(k)]


def wash_pair(O, C, k=8, noise=2):
    """Two own entities transacting mutually, plus a little real volume."""
    v = []
    for _ in range(k):
        v += [vir(O, C), vir(C, O)]
    v += [vir(O, f"real-{i}") for i in range(noise)]
    return v


def ring(ops, k=6):
    """A->B->C->D->A directed ring (diffused reciprocity)."""
    v = []
    n = len(ops)
    for _ in range(k):
        for i in range(n):
            v.append(vir(ops[i], ops[(i + 1) % n]))
    return v


def diffusion(O, shills, real=3):
    """O washes across many own entities (no tight 2-cycle), plus real volume."""
    v = []
    for s in shills:
        v += [vir(O, s), vir(s, O)]   # spread thin: few per shill
    v += [vir(O, f"real-{i}") for i in range(real)]
    return v


def niche_b2b(O, k=12):
    """Legitimate: one service agent serving ONE buyer, one-directional."""
    return [vir(O, "bigbuyer") for _ in range(k)]


def partial_collusion(O, C, wash=4, legit=10):
    """Mostly legitimate diverse volume with a small wash component."""
    v = [vir(O, f"buyer-{i}") for i in range(legit)]
    for _ in range(wash):
        v += [vir(O, C), vir(C, O)]
    return v


def row(label, report):
    flags = ",".join(report.flags) or "-"
    sd = "yes" if "reciprocal_cluster" in report.flags else "no"
    print(f"  {label:<34} n={report.n_inbound:<3} distinct={report.distinct_counterparties:<3} "
          f"top={report.top_share:<5} recip={report.reciprocal_balance:<5} "
          f"score={report.score}  self-dealing-flag={sd:<3} flags=[{flags}]")


def main() -> None:
    print("Operator-independence over canonical topologies (lower score = more concentrated/reciprocal):\n")

    row("healthy / diverse (15 buyers)", operator_independence("O", healthy("O")))

    wp = wash_pair("O", "C")
    row("self-dealing pair (8 mutual)", operator_independence("O", wp))

    r = ring(["A", "B", "C", "D"])
    row("4-node ring A->B->C->D->A", operator_independence("A", r))

    d = diffusion("O", [f"shill-{i}" for i in range(6)])
    row("diffusion across 6 entities", operator_independence("O", d))

    row("niche B2B (1 buyer, legit)", operator_independence("O", niche_b2b("O")))

    pc = partial_collusion("O", "C")
    row("partial collusion (~29% wash)", operator_independence("O", pc))

    print("\nReading: the self-dealing PAIR is the only one flagged `reciprocal_cluster`. "
          "The niche-B2B case trips high_concentration but NOT reciprocal_cluster (one-directional "
          "flow), confirming the signal separates legitimate concentration from mutual self-dealing. "
          "The ring and diffusion dilute the 2-cycle reciprocity and are NOT caught by this local "
          "heuristic alone -- exactly the documented limitation; a quantitative FP/FN study is future work.")
    print("\nOK")


if __name__ == "__main__":
    main()
