"""End-to-end PAR demo: a settled AP2 mandate -> a VIR -> verification -> chargeback.

Run: python demo/run_demo.py   (from the repo root, with src on PYTHONPATH)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from par.mint import mint_from_mandate  # noqa: E402
from par.types.vir import Context, Party, Role, SettlementStatus  # noqa: E402
from par.verify import verify  # noqa: E402


def main() -> None:
    # The checkout mandate (merchant-signed cart) carries NO settlement status.
    mandate = {
        "type": "ap2.checkout_mandate.closed",
        "mandate_id": "ap2://mandates/demo-001#closed",
        "merchant": "did:web:travelmart.example",
        "items": [{"sku": "FL-SFO-JFK", "class": "non_refundable_fare"}],
    }
    mandate_resolver = lambda ref: mandate if ref == mandate["mandate_id"] else None  # noqa: E731

    # The settlement oracle: a network/PSP-signed attestation (outcome only).
    oracle = {"ap2://settle/demo-001": {"status": "settled"}}
    settle_resolver = lambda ref: oracle.get(ref)  # noqa: E731

    subject = Party(operator_id="did:web:travelmart.example", identity_proof="ap2.vdc",
                    identity_depth=3, role=Role.SERVICE_AGENT)
    counterparty = Party(operator_id="did:web:assistant.example", identity_proof="ap2.vdc",
                         identity_depth=2, role=Role.BUYER_AGENT)
    context = Context(skill="flight_booking", item_class="non_refundable_fare")

    vir = mint_from_mandate(mandate, subject, counterparty, context,
                            settlement_status="settled", settlement_ref="ap2://settle/demo-001")
    print("Minted VIR:", vir.interaction_id)
    print("  anchor hash:", vir.anchor.mandate_hash)

    r = verify(vir, mandate_resolver, settle_resolver)
    print(f"  settled:    verified={r.verified} well_formed={r.well_formed} active={r.active}")
    assert r.active

    # A refund is NOT adversarial: the VIR stays valid evidence (just not active).
    refunded = mint_from_mandate(mandate, subject, counterparty, context,
                                 settlement_status="refunded", settlement_ref="ap2://settle/demo-001")
    rr = verify(refunded, mandate_resolver, lambda ref: {"status": "refunded"})
    print(f"  refunded:   well_formed={rr.well_formed} active={rr.active} "
          f"invalidated={'Settlement-Consistency' in ' '.join(rr.violations)}")
    assert rr.well_formed and not rr.active

    # A chargeback IS adversarial: the network oracle reports it; the VIR is invalidated.
    oracle["ap2://settle/demo-001"] = {"status": "charged_back"}
    vir.anchor.settlement_status = SettlementStatus.CHARGED_BACK
    r2 = verify(vir, mandate_resolver, settle_resolver)
    print(f"  chargeback: active={r2.active}  ({r2.violations[-1]})")
    assert not r2.active
    print("OK")


if __name__ == "__main__":
    main()
