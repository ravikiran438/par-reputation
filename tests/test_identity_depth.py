from par.identity import grade, graded_party, MAX_DEPTH
from par.types.vir import Party, Role


def test_ladder_base_levels():
    assert grade("self_asserted") == 0
    assert grade("did.vc") == 1
    assert grade("fido.kya") == 2
    assert grade("ap2.vdc") == 2


def test_assurance_bumps_and_clamp():
    assert grade("ap2.vdc", "ial2") == 3
    assert grade("ap2.vdc", "IAL3") == 4          # case-insensitive
    assert grade("fido.kya", "ial3") == 4         # clamped at MAX_DEPTH
    assert grade("ap2.vdc", "ial3") <= MAX_DEPTH


def test_self_asserted_ignores_assurance():
    assert grade("self_asserted", "ial3") == 0


def test_unknown_proof_defaults_to_zero():
    assert grade("mystery.proof", "ial2") == 0


def test_graded_party_sets_depth():
    p = Party(operator_id="did:web:m.example", identity_proof="ap2.vdc",
              identity_depth=0, role=Role.SERVICE_AGENT)
    g = graded_party(p, "ial2")
    assert g.identity_depth == 3
    assert p.identity_depth == 0   # original unchanged (copy)
