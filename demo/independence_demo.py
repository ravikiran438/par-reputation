"""Operator-independence demo: a healthy operator vs. a self-dealing pair.

Run: python demo/independence_demo.py   (from repo root)
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from par.signals.independence import flag_self_dealing, operator_independence  # noqa: E402
from par.types.vir import (  # noqa: E402
    Anchor, Context, Party, Role, SettlementStatus, VerifiedInteractionRecord,
)


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


def show(report):
    print(f"  {report.operator_id}")
    print(f"    inbound={report.n_inbound} distinct={report.distinct_counterparties} "
          f"top_share={report.top_share} reciprocal_balance={report.reciprocal_balance}")
    print(f"    score={report.score}  flags={report.flags}")


def main() -> None:
    good = "did:web:travelmart.example"
    healthy = [vir(good, f"did:web:buyer-{i}.example") for i in range(15)]
    print("Healthy operator (15 distinct buyers):")
    show(operator_independence(good, healthy))

    merchant = "did:web:wash.example"
    shill = "did:web:shill.example"   # the same actor's second verified entity
    wash = []
    for _ in range(8):
        wash += [vir(merchant, shill), vir(shill, merchant)]
    wash += [vir(merchant, "did:web:real-1.example"), vir(merchant, "did:web:real-2.example")]
    print("\nSelf-dealing pair (8 mutual settled txns between two own entities):")
    show(operator_independence(merchant, wash))

    print("\nflag_self_dealing() over the wash set:")
    for r in flag_self_dealing(wash):
        print(f"  FLAGGED {r.operator_id}: {r.flags}")
    print("\nOK")


if __name__ == "__main__":
    main()
