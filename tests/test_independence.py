"""Operator-independence signal: healthy vs. self-dealing vs. thin evidence."""
import uuid
from datetime import datetime, timezone

from par.signals.independence import operator_independence, flag_self_dealing
from par.types.vir import (
    Anchor, Context, Party, Role, SettlementStatus, VerifiedInteractionRecord,
)


def _vir(subject_op, counterparty_op, subj_role=Role.SERVICE_AGENT):
    cpty_role = Role.BUYER_AGENT if subj_role == Role.SERVICE_AGENT else Role.SERVICE_AGENT
    return VerifiedInteractionRecord(
        interaction_id=str(uuid.uuid4()),
        anchor=Anchor(mandate_ref="ap2://m/" + str(uuid.uuid4()),
                      mandate_hash="sha256:" + "0" * 64,
                      settlement_status=SettlementStatus.SETTLED),
        subject=Party(operator_id=subject_op, identity_proof="ap2.vdc",
                      identity_depth=3, role=subj_role),
        counterparty=Party(operator_id=counterparty_op, identity_proof="ap2.vdc",
                           identity_depth=2, role=cpty_role),
        context=Context(skill="flight_booking"),
        issued_at=datetime.now(timezone.utc),
    )


def test_healthy_operator_scores_high_no_flags():
    O = "did:web:good.example"
    virs = [_vir(O, f"did:web:buyer-{i}.example") for i in range(15)]
    r = operator_independence(O, virs)
    assert r.n_inbound == 15 and r.distinct_counterparties == 15
    assert r.score is not None and r.score >= 0.9
    assert r.flags == []


def test_wash_trading_flagged_reciprocal_cluster():
    O = "did:web:merchant.example"
    C = "did:web:shill.example"          # operator's own second entity
    virs = []
    # 8 mutual transactions each way between O and C, plus 2 genuine others.
    for _ in range(8):
        virs.append(_vir(O, C))
        virs.append(_vir(C, O))
    virs.append(_vir(O, "did:web:real-1.example"))
    virs.append(_vir(O, "did:web:real-2.example"))

    r = operator_independence(O, virs)
    assert r.top_counterparty == C
    assert "reciprocal_cluster" in r.flags
    assert "high_concentration" in r.flags
    assert r.score is not None and r.score < 0.5

    flagged = flag_self_dealing(virs)
    flagged_ops = {x.operator_id for x in flagged}
    assert O in flagged_ops and C in flagged_ops


def test_insufficient_data_flagged():
    O = "did:web:new.example"
    virs = [_vir(O, "did:web:b1.example"), _vir(O, "did:web:b2.example")]
    r = operator_independence(O, virs)
    assert "insufficient_data" in r.flags


def test_unknown_operator_returns_none_score():
    virs = [_vir("did:web:a.example", "did:web:b.example")]
    r = operator_independence("did:web:nobody.example", virs)
    assert r.n_inbound == 0 and r.score is None
