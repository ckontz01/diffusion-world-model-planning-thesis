# Preparation record — 18 September 2026

Accepted parent: `05973d5932e21c13b86cd95307dc055bba646255`.
Branch: `candidate-value-score-information-preparation-20260918`.

The only remote work was an identifier/availability/seal/header lineage probe on accepted training artifacts. It authenticated 384 roots and 1,426 banks without numerical model evaluation. The probe source and its exact certificate are retained here; score omission remains an original design choice, not a retroactive fault.

Held-out available-bank counts by fold are 354, 363, 351, 358 (binary records 5,664, 5,808, 5,616, 5,728). Complement fitting-bank counts are 1,072, 1,063, 1,075, 1,068 (binary training rows 17,152, 17,008, 17,200, 17,088). Every fold has 144 fitting and 48 held-out sources; unavailability changes row counts, not role allocation or updates.

Twelve focused synthetic tests pass, including the complete four-fold driver with 24 mocked fit calls, fixed forward-only models and optimizer creation forbidden. Tests cover source separation, train-only scaling, score sign, exact-zero control inputs, constant-score columns, weighting, paired minibatch order, 43,200-update grid, tie behavior, approval-before-data-access, and exclusive/capped outputs. These are technical tests, not training or evidence of scientific promise.

No real-data fit, new outcome, GPU allocation, Slurm job, closed-loop call, or reserved payload access was performed. No historical source, output, model or E12 draft was edited. The new worker has no proposer/world-model/simulator execution path. The source package contains accepted data-reader and metric helpers, not research payloads, and ships a disabled approval template.

## Tested executable source package

External SSD: `D:/THESIS-BACKUPS/candidate-value-score-information-20260918/preparation-v1`.
Verified volume label `THESIS_SSD`, identity `0a2f1ba9-0000-0000-0000-100000000000`.
Source manifest SHA-256: `68145e6458da0b90255dd98e4fa2b9469dea12907797d7830c9bd233314be35c`.
Sixteen source/metadata files, 423,422 bytes before manifest/template. Line endings in executable text are explicitly LF. Shell syntax validation and the same twelve tests passed from the packaged copy. Exact package closure was also tested with an in-memory synthetic approval (not written); no saved-data reader or worker was invoked by that check. The on-disk approval remains disabled. No package upload or cluster launch occurred.
