# R1 implementation and execution history

## Authorization and source preflight

The initial source preflight (`f07126e`) found hashes, not final action values,
for historical CEM outputs. The user explicitly approved fixed saved-candidate
stimuli, with reproducible pre-execution selection and correct action semantics.
The prior-top control retains its authentic saved returned action tensor.
The preflight note remains a historical record of the earlier pending choice;
the separately named R1 plan records the subsequently authorized work.

`c795b9b` introduced the bounded native-interface harness and eight local
unit tests. A local indentation error was caught during test collection and
fixed before any snapshot or simulator execution. The frozen original R1
source manifest is `2c5ea97ae66b1f4714bcd58f7a33d3b57bb9276df672f5023966bf96c6a33a67`.
Its five source entries passed checksums before submission.

## Job 300297: successful scheduler execution, incomplete Cube coverage

Run root:
`/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-r1/run-20260905-2c5ea97a`.
Completed 0:0 in 6m15s. The eight tests passed in the pinned SAGE environment.
Stimuli were chosen and sealed before the first simulator reset.

All twelve PushT traces contained complete restoration and 15-action coverage.
All eight Cube traces counted native reset-internal step calls toward the
15-action cap. This omitted the before-first-action capture and truncated
post-restoration execution. The summary reducer stopped on the missing event;
it wrote no misleading successful analysis. Scheduler completion alone was
not treated as diagnostic validity.

The preserved invalid Cube traces each contain two reset-internal calls and
thirteen post-restoration actions. Across both jobs the complete accounting
is 28 initializations, 404 post-restoration actions and 32 reset-internal calls;
the valid analysis uses 20 initializations and 300 post-restoration actions.

## Job 300298: eight Cube-only replacements

The sole simulator-harness correction separates reset-internal calls from
the post-restoration counter. A regression test covers that distinction;
nine harness tests pass. The runner was restricted to Cube cases 3/4 in
both stacks, two fresh repeats each. No valid PushT trace was rerun or selected
by outcome. Both preparations produced identical STIMULI.json bytes.

New snapshot source manifest:
`549757ef959a79ba77de5a4ec2384edb71ab2639f72d265f66b7c1a64ebe7f6a`.
Run root:
`/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19-r1/run-20260905-549757ef`.
Job 300298 completed 0:0 in 3m09s. Every corrected Cube initialization logged
two native reset-internal actions, then exactly fifteen stimulus actions.
All original files are preserved. No environment, model, checkpoint, selected
stimulus, normalization rule or historical result was changed.

## Analysis and checks

The engineering reducer verifies adjacent seals, exact preparation identity,
case/stack/repeat identity, before-action capture, all fifteen before/after
step events, a single fixed-return call and cap termination. It analyzes
the twelve valid PushT and eight replacement Cube traces, not the incomplete
Cube files. Six reducer tests cover numerical comparison, stage alignment,
state-field separation and the missing-coverage rejection.

The smaller review package was generated from the verified full analysis and
raw traces. An independent CPU check reselected all five stimuli directly
from the original banks without using the harness selection function or any
model: candidate zero was all-zero in each CEM bank, index one was the first
eligible candidate, and every chosen value/content hash matched.

All 27 local tests passed in 21.42 seconds: fifteen R1 harness/reducer tests
and twelve existing E18 regression tests. The independent package verifier,
shell syntax check and git whitespace checks also passed. Parent E18 and
diagnostic source manifests and both R1 source manifests were reverified after
execution. Current canonical R1 source bytes match the replacement manifest.
Historical E18/E19/D2/L1 source/results remain untouched, as do the three
untracked E12 drafts. The greedy-64 change is outline-only. No scheduler
monitor or author-contact automation was created.

## Storage and scope

Canonical edits: `/home/chris/thesis` in WSL Thesis-Ubuntu (external-SSD-backed).
Only STIMULI.json and the approximately 3.1 MB review reduction are copied
locally; the full analysis and all raw traces remain on Lustre. Jobs used
read-only bindings for prior source/data and a writable fresh R1 output root.
The fixed-return object contains no model and cannot make a second call.
No planning, training, protected metrics, holdout creation, benchmark success
analysis, E18-versus-SAGE efficacy comparison or author contact occurred.
