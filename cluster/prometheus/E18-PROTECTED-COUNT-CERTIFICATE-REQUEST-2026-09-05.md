# Count-only availability certificate requested for a possible later expansion

This is a request specification for the authorized data custodian, **not an
instruction to the implementation agent to open protected memberships**. It was
not sent externally and is not a certificate that additional data is available.

Return counts only, with no episode IDs, selected starts, pixels, physical
values, model outputs or performance values. Use the existing immutable PushT
partition/exposure registries and public official SAGE identifiers. Record
input-manifest hash references, audit-code version, scope and custodian
attestation; do not open or hash protected outcome artifacts to produce it.

Required definition: distinct episodes with at least one common start admitting
both endpoint indices start+75 and start+150, metadata consistent with the
accepted seven-field PushT initializer, excluding every episode previously used
for planner training/validation, evaluated/inspected development or diagnostics,
E19 paper/sentinel runs, D3/D4 and any prior protected outcome exposure. Exclude
locked C1/I1/D5 allocations; do not inspect their outcomes. No duplicate starts
or seeds count as additional episodes.

Report for each potentially releasable partition:

1. Total length-compatible episode count and incremental exclusions by reason.
2. Remaining count after all known exposure and protected-allocation exclusions;
   list which exposure categories are uncertified or incomplete.
3. Among that remainder, counts in SAGE train/validation/test (identifier-only),
   and known/unknown exact LeWM training exposure. Do not assume unknown is zero.
4. Maximum E18-only capacity and maximum jointly eligible untouched SAGE reserve.
5. Feasible count pairs `(E18 allocation, untouched SAGE reserve)` for reserve
   sizes0/50/100/200 where possible, retaining episode disjointness. These are
   capacities, not finalized allocation lists or a new confirmation manifest.

Global metadata upper bounds are P3:406 and P4:386 length-compatible episodes.
These do not establish availability. The current allowed P2 audit finds82, with
SAGE roles73train/9validation/0test. A proposed release requires separate user
approval; no certificate alone authorizes evaluation, model changes or a SAGE
grid rerun.
