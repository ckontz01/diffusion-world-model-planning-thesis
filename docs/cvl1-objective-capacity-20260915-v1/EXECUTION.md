# Objective × capacity v1 — execution record

The user authorizes one new saved-feature CPU learning study with four fixed
configurations, 48 cross-fit and 12 full-data fits. The historical result and
diagnosis are not modified. See [the frozen protocol](PROTOCOL.md).

## Prelaunch checks

17 focused synthetic tests passed, covering paired same-draw targets and zeros,
two binary draws, baseline identity, nonbinary-label rejection, hierarchical
weights, distinct new/historical tie rules, deterministic source-disjoint folds,
training-only/common normalization, exact parameter counts, zero relative baseline,
ensemble arithmetic, original-BCE optimizer equivalence on synthetic fixtures,
finite zero-target relative fitting, gain/loss reduction, recommendation rules,
exclusive size-reserved output, validation-read barrier and CPU reservations.

Source implementation: `analysis/cvl1-objective-capacity-20260915-v1/study.py`;
focused tests: `test_study.py`; read-only runtime wrapper: `run.sh` in the same
directory. Original model and data helpers are authenticated against accepted
CVL-1 source manifest, not copied or edited. Git/source/job/output identities and
actual accounting will be appended after launch/completion, without changing
the scientific protocol. No GPU or original simulator data is required.

The one submission requests account superworld, partition defq, qos normal,
4 CPUs, 8G memory and 02:00:00. A frozen source export, exclusive launch intent
and exclusive run directory precede the single `sbatch` call. The source export
only applies reversible CRLF→LF transport normalization, with its own hashes.
No job retry is authorized. Terminal artifacts and logs, including any failure,
are retained and backed up to the external THESIS_SSD.
