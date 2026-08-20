# E9 abandonment record

Date: 2026-08-17  
Status: abandoned before a valid evaluation; no scientific result

E9 was frozen as an AE-only exposed-D2 closed-loop study, but a subsequent
source-level audit established that its five arms, D2 starts, checkpoints,
scorer/planner seeds, CEM settings, weights, and `D2CostModel` implementation
were the same as the already completed E3 arms. The immutable E3 and E9 copies
of `acid_alt_d2_models.py` had identical SHA-256
`67635ebb05505210bca3e712e73e95c8f8e81c0ea873260f238cf8218e04b15c`;
their residual-diffusion trainer copies also matched at SHA-256
`871ebc12c4af778031155f78b060e017c7060775d3f2e32bb49dc986925a52ad`.
Because E3 had already measured AE success `0.79778` versus reconstructed ACID
`0.84889`, repeating the deterministic study could not answer a new question.

Array `297724` and dependent analysis `297725` were therefore cancelled. Some
early array elements failed during startup because the newly added protected-
path guard matched the incidental characters `d3` inside the immutable
snapshot hash. No valid E9 evaluation or aggregate was produced and no E9
outcome may be cited. The local guard was subsequently changed from raw
substring matching to token-aware path matching.

The E9 snapshot and failed/cancelled scheduler records remain preserved as an
audit trail. Development proceeds through the scientifically distinct E8A
proposal-refinement route instead.
