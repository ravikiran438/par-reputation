import pytest

from par.types.vir import Context, Party, Role


@pytest.fixture
def closed_mandate():
    """A minimal Closed AP2 Checkout Mandate (no payment data, no settlement status)."""
    return {
        "type": "ap2.checkout_mandate.closed",
        "mandate_id": "ap2://mandates/abc#closed",
        "merchant": "did:web:merchant.example",
        "items": [{"sku": "FL-123", "class": "non_refundable_fare"}],
    }


@pytest.fixture
def settlement_resolver():
    """A network-signed settlement oracle: maps settlement_ref -> {status}."""
    store = {"ap2://settle/abc": {"status": "settled"}}

    def resolve(ref):
        return store.get(ref)

    resolve.store = store  # tests can mutate to simulate refund/chargeback
    return resolve


@pytest.fixture
def subject():
    return Party(
        operator_id="did:web:merchant.example",
        identity_proof="ap2.vdc",
        identity_depth=3,
        role=Role.SERVICE_AGENT,
    )


@pytest.fixture
def counterparty():
    return Party(
        operator_id="did:web:buyer-platform.example",
        identity_proof="ap2.vdc",
        identity_depth=2,
        role=Role.BUYER_AGENT,
    )


@pytest.fixture
def context():
    return Context(skill="flight_booking", item_class="non_refundable_fare")
