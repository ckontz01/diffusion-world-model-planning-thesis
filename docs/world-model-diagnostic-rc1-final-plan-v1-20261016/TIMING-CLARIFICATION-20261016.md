# Fixed RC1 timing screen and preservation intervals

This addendum supplies the numerical timing specification requested by Pro's final review. It changes no scientific procedure, model invocation, allocation ceiling or operation allowance. The formulas and reserves are fixed before any RC1 timings are observed. A passing screen is a necessary scheduling condition, not a worst-case performance guarantee or a substitute for the included full native stages.

## Measurements within the already counted gate

For each task, let L be the elapsed wall time of its reviewed adapter construction: existing checkpoint/encoder loading, strict state binding, device transfer and evaluation setup, synchronized at completion. Let E be the maximum elapsed wall time of its already counted single-image extractions in the fixed 72-call role/repeat portion of the gate. Synchronize CUDA immediately before and after each counted extraction. Measure the complete per-image preprocessing, input transfer, original encoder call and float32 output boundary; any host transfer, hashing or grouping not inside that interval belongs to the non-encoding allowance below.

Use each task's L and E separately. No averaging away slow observations, timing-dependent image selection, discarded first call, extra warmup, benchmark forward, new input or timing retry is permitted. Reference-only candidate calls remain counted in the gate but are not used to choose a faster E. Preserve all measured values and the fixed maximum rule. If a required timing is missing, nonfinite or negative, fail the timing screen.

## Fixed pass inequalities

The two screening estimates are:

- Head work estimate: `2 * (L + 352 * E) + 600 <= 1740` seconds.
- Included DINO parent work estimate: `2 * (L + 166 * E) + 1800 <= 3540` seconds.

The multiplier 2 is a fixed conservative inflation of observed loading/encoding time, not an empirically validated worst-case bound. The 600-second head reserve covers all remaining worker work: startup/import/input authentication, source reads and grouping/host copies, fixed float64 ridge fitting, within-worker validation summary, output/member hashing and writing. It is not an extra 600 seconds beyond the 1740-second work interval.

The 1800-second parent reserve covers all non-encoding worker work: startup/import/authentication/readout loading, unchanged CEM and predictor/chunk operations, physical restoration/oracle/evaluation/tails, S0/S1 evaluation, worker checks and output/member hashing/writing. The 166-frame screen covers the largest included DINO parent (148 ordinary plus 18 Reacher parity); the failed PushT continuation has only its specified 144 future frames. Do not allocate the unused difference to additional work. The parent estimate does not infer chunk100 performance from a chunk16 reference or prove CEM/physics throughput. Its actual root000 workload still has to finish and pass acceptance under the complete fixed deadline.

The estimates allocate whole work intervals, including loading; do not add the terms again to the job's allocation reservation. The independent acceptance process is outside those work estimates but inside the separate 60-second preservation interval: at most 55 seconds for independent arithmetic/schema/member validation and final receipts, with 5 seconds reserved for supervisor finalization. No research forward or fit is permitted during preservation. All workers stop at their work deadline; failed or timed-out checks preserve evidence and stop progression without a retry allowance.

The RC1 gate itself remains 120 seconds of total work plus 60 preservation (55 validation and 5 finalization), including the measured calls, independent native reference, comparisons and export. Each new head remains 1740 plus 60; each remaining parent remains 3540 plus 60. CPU analysis/final preservation retain their separate original finite contract and require the new complete lineage/member enumeration. No cap or operation count is increased by this clarification.

## Failure and interpretation

Require BOTH task-specific screens to pass before authorizing the proposed head and continuation stages. A screen failure does not trigger a new measurement, representation/batch change, shortened science, longer allocation, refit search or resubmission. Retain STOP and the exact inequality inputs. A passing screen permits only the next independently authorized stage; actual elapsed time, module/frame counters, memory, output/tmp/log limits and all scientific acceptance checks remain binding.

The numerical reserves are fixed scheduling choices under the existing work budgets, not claims derived from real RC1 performance. No RC1 timing, model execution or full-workload acceptance has been performed. This bounded documentation correction follows Pro's requested clarification; no second Pro review or execution authority is claimed for it.
