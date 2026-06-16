"""Lightweight identity_depth ladder.

A small, deliberately heuristic mapping from an external identity proof (plus an
optional assurance level) to a PAR `identity_depth` in 0..4. This is a starting
default, NOT a calibrated standard; calibrating these levels against AP2 VDC /
FIDO assurance is future work. PAR produces the *depth* (an evidence grade);
scoring engines decide how to weight it.
"""

from __future__ import annotations

from typing import Optional

from par.types.vir import Party

# Base depth by proof type.
_BASE = {
    "self_asserted": 0,   # no external verification
    "did.vc": 1,          # a verifiable credential, issuer unspecified
    "fido.kya": 2,        # FIDO "Know Your Agent" attestation
    "ap2.vdc": 2,         # AP2 verifiable digital credential
}

# Optional bump from a recognized assurance level (e.g. NIST IAL).
_ASSURANCE_BUMP = {
    None: 0,
    "ial1": 0,
    "ial2": 1,
    "ial3": 2,
}

MAX_DEPTH = 4


def grade(identity_proof: str, assurance_level: Optional[str] = None) -> int:
    """Map (proof, assurance) -> identity_depth in 0..MAX_DEPTH.

    `self_asserted` is always 0 regardless of assurance. Unknown proofs default
    to 0 (treated as un-verified). Unknown assurance levels add no bump.
    """
    # Unknown or self-asserted proofs are un-verified: depth 0, assurance ignored.
    if identity_proof not in _BASE or identity_proof == "self_asserted":
        return 0
    bump = _ASSURANCE_BUMP.get((assurance_level or "").lower() or None, 0)
    return max(0, min(MAX_DEPTH, _BASE[identity_proof] + bump))


def graded_party(party: Party, assurance_level: Optional[str] = None) -> Party:
    """Return a copy of `party` with identity_depth set from the ladder."""
    return party.model_copy(update={"identity_depth": grade(party.identity_proof, assurance_level)})
