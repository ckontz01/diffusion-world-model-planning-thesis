# Post-E14 boundary diagnostic implementation decisions 1

Date: 25 August 2026

Status: pre-full-run technical implementation record

## Initial immutable snapshot

The first diagnostic snapshot was
`gdp-post-e14-boundary-3971bb230cad54e1`, with source-manifest SHA-256
`3971bb230cad54e1b62bd0c9d3954c95c5f487a302a436b8d93ba13f66be38dc`.
Its static preflight passed three unit tests.

## Smoke job 299172 technical failure

The one-cell smoke job failed before loading the E14 cache, endpoint model, or
world model and before producing any output artifact. The diagnostic referred
to `spec.EXPECTED_GPU_NAME`, a constant added in the later Gate-C wrapper
snapshot but absent from the immutable E14 offline snapshot used as this
diagnostic's base. Python raised `AttributeError` immediately after detecting
CUDA.

The correction defines the same exact required device string,
`NVIDIA RTX 6000 Ada Generation`, inside the diagnostic module. It does not
change a task, row, seed, model, candidate, metric, threshold, or
interpretation.

The empty failed smoke output location is preserved. A new immutable snapshot
and a new output location are required for the replacement smoke.

## Revised static-freeze compatibility correction

The first attempt to freeze the analyzer stopped during test collection. The
immutable E14 offline base predates the later `read_sha256_records` helper that
the analyzer initially imported. No replacement smoke or full diagnostic was
submitted. The analyzer now contains its own strict two-file GNU-checksum
reader. The failed staging directory is preserved and the corrected freeze
uses a new staging location.

Before the replacement smoke completed and before any full cell was submitted,
a static inspection also found that the upstream offline specification did not
yet expose `CANDIDATE_COUNT` as a module constant. The analyzer now fixes the
already-protocol-defined value `300` locally, just as the original E14 offline
evaluator did. This does not change an experiment setting.

## Replacement smoke 299174 coordinate correction

The replacement smoke completed the Python diagnostic and exactly reproduced
the first stored E14 boundary row, but its Slurm wrapper then exited 127 because
the postcheck invoked the container-only environment interpreter from the host.
The postcheck now uses `/usr/bin/python3`, matching the proven E14 normalized
wrapper. The metric files are preserved but are not valid diagnostic evidence.

Inspection of that smoke revealed that the initial legal-limit comparison was
in the wrong coordinate system. E14 actions are the released evaluator's
StandardScaler-transformed planner inputs, not raw environment actions. The
environment bounds are `[-1,1]`, but those numbers must first be transformed
using `planner_primitive_action_mean` and
`planner_primitive_action_std` from the exact hashed transition cache. The
diagnostic now requires that cache, verifies its SHA-256, performs the mapping,
and records both coordinate systems and scaler statistics. This correction was
made before any full cell was submitted. Smoke 299174 is explicitly excluded
from scientific interpretation.

The coordinate-transform helper has an independent synthetic unit test. This
revision freezes from a third, uniquely named staging directory so neither the
initial snapshot nor either failed smoke can be mistaken for the corrected
diagnostic.

## Analyzer fixed before full execution

Before any full diagnostic cell was submitted, a deterministic six-cell
analyzer and synthetic tests were added. The analyzer validates every output
hash and all-row E14 reproduction claim, reports predeclared row-distribution
quantiles and equal-task/equal-seed descriptive summaries, and has no
scientific gate or E15 authorization authority.

## Full jobs 299176 and 299180: float32-bound correction

All six cells of array 299176 completed successfully, reproduced every stored
E14 robust-boundary row, and analyzer 299180 completed with valid hashes. The
legal-limit interpretation is nevertheless excluded. The released
`StandardScaler.transform` preserves float32 and performs subtraction and
division as two separately rounded in-place operations. The diagnostic had
used one float64 expression followed by one float32 cast. For several Cube
dimensions, the two algebraically equivalent calculations differ by one ULP;
the shortcut consequently labelled many expert actions exactly at `-1` or
`+1` as outside the environment.

The corrected diagnostic now reproduces the released two-operation float32
mapping exactly. It reports strict legal OOB separately from the primary
four-float32-epsilon tolerant legal OOB diagnostic, matching the repository's
existing planner-standardizer rounding envelope. The analyzer independently
recomputes and validates both mapped ranges and pins the deployed environment
source hashes. This was identified before E15 was designed, trained, or
authorized. The robust-quantile reproduction from 299176 remains a useful
technical check, but none of its legal-OOB numbers may support a conclusion.

The first static freeze of this correction stopped in its new scaler-rounding
unit test. The test had incorrectly equated the most extreme cached expert
value with `StandardScaler.transform(-1)`; source float32 controls may extend
by a raw-action rounding unit while still falling inside the registered
four-epsilon envelope. No smoke or full job was submitted. The corrected test
now constructs an independent sklearn `StandardScaler` with the frozen
statistics and requires bit-exact agreement with its float32 transform.

The next static freeze also stopped before execution because the independent
test used the nonexistent ndarray method `.square()` while assigning sklearn's
unused `var_` compatibility attribute. It now uses `np.square(std)`. This was
test-only and no scientific job was submitted.

The following static freeze stopped in the same independent test: applying
the two float32 operations to separate one-dimensional low/high arrays did not
bit-match sklearn's two-row matrix transform on one Cube coordinate. The
implementation now transforms the low/high pair together as the exact
two-row float32 matrix passed to `StandardScaler.transform`; the analyzer uses
an independent copy of the same released matrix semantics. No scientific job
was submitted from this failed staging tree.

The next static freeze showed that matrix shape was not the cause. Inspection
of the installed sklearn primary implementation found the missing exact step:
current `StandardScaler.transform` explicitly casts `mean_` and `scale_` to
the input dtype before its in-place operations. The corrected helper and the
independent analyzer now cast both frozen statistics to float32 first, exactly
matching the installed released evaluator. Again, the failed staging tree
created no scientific job.
