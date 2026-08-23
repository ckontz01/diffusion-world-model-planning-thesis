# E14 Gate-B serialization erratum

Date: 23 August 2026

Scope: technical output serialization only; fixed after all 32 frozen Gate-B
evaluation cells completed and before any aggregate audit was available.

Job 299070 ran the frozen Gate-B analyzer from scientific snapshot
`bc27ec5c93dfae6681c149fd755d93742a0678583787bad7e3fcd43300d59cae`.
It verified all inputs and calculated the frozen aggregate, but failed while
writing `GATE-B-AUDIT.json` because one or more gate values were NumPy boolean
scalars, which Python's standard JSON encoder does not accept. The atomic
writer removed its partial file; no aggregate audit was produced or read.

The replacement entry point dynamically loads the unchanged analyzer whose
file SHA-256 is
`5362788ed566a5f2f876b63ff004ba878bd5278d28ed323408431f02d3572299`.
It replaces only the analyzer's JSON writer and final JSON display with an
encoder that converts NumPy scalar values via `.item()`. Input validation,
metric loading, aggregation, gates, eligible-endpoint logic, hashes, and the
scientific source manifest are executed by the original module unchanged.
The replacement run uses a new output directory and records both snapshot
hashes and the original analyzer hash.

No task, endpoint, seed, metric, threshold, candidate bank, model, checkpoint,
or result is changed by this erratum. D3, D4, D5, P3, P4, C1, and I1 remain
unread.
