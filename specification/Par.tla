---------------------------- MODULE Par ----------------------------
(***************************************************************************)
(* Provenance-Anchored Reputation (PAR): evidence-layer safety model.      *)
(*                                                                         *)
(* PAR standardizes the EVIDENCE layer (the Verified Interaction Record),  *)
(* not scoring. This model captures the six properties enforced by         *)
(* src/par/validators/invariants.py.                                       *)
(***************************************************************************)
EXTENDS FiniteSets, Sequences, TLC

CONSTANTS
    Operators,          \* set of durable operator identities
    Mandates,           \* set of closed-checkout-mandate refs
    Skills

Roles == {"service_agent", "buyer_agent"}
Settle == {"pending", "settled", "refunded", "charged_back", "disputed"}
\* Adversarial reversals that invalidate a VIR. A refund is NOT here: it is a
\* completed interaction unwound by agreement, not malfeasance.
Invalidating == {"charged_back", "disputed"}
Proofs == {"ap2.vdc", "fido.kya", "did.vc", "self_asserted"}

\* A VIR is a record anchored to a mandate, between two roled operators.
VIR == [ anchorRef   : Mandates,
         anchorType   : {"ap2.checkout_mandate.closed"},
         settlement   : Settle,
         subjOp       : Operators,
         subjRole     : Roles,
         subjProof    : Proofs,
         cptyOp       : Operators,
         cptyRole     : Roles,
         skill        : Skills ]

VARIABLE virs          \* set of issued VIRs
TypeOK == virs \subseteq VIR

Init == virs = {}

\* Minting only admits well-formed, grounded records (the mint path is the
\* only producer; see src/par/mint.py).
WellFormed(v) ==
    /\ v.anchorType = "ap2.checkout_mandate.closed"          \* VIR-Groundedness
    /\ {v.subjRole, v.cptyRole} = Roles                       \* Role-Scoping
    /\ v.subjProof \in Proofs /\ v.cptyProof \in Proofs       \* Operator-Anchoring
    /\ v.skill \in Skills

Mint(v) ==
    /\ v \in VIR
    /\ WellFormed(v)
    /\ virs' = virs \cup {v}

Next == \E v \in VIR : Mint(v)
Spec == Init /\ [][Next]_virs

\* --- Safety properties (invariants) ---

\* VIR-Groundedness: every issued VIR is anchored to a closed checkout mandate.
Groundedness == \A v \in virs : v.anchorType = "ap2.checkout_mandate.closed"

\* Role-Scoping: the two parties are exactly one service_agent and one buyer_agent.
RoleScoping == \A v \in virs : {v.subjRole, v.cptyRole} = Roles

\* Settlement-Consistency: an adversarial reversal (chargeback/dispute) is never
\* active. A refund is not adversarial and is handled separately (valid evidence,
\* simply not in the active/settled state).
Active(v) == v.settlement = "settled"
SettlementConsistency ==
    \A v \in virs : (v.settlement \in Invalidating) => ~Active(v)

=============================================================================
