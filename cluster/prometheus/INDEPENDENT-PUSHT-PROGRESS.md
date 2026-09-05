# Independent PushT evaluation: implementation plan and checkpoint

User authorization: implement the collector, common SAGE integration, large
statistical/resource design, final dataset and evaluation; make incremental commits.
This is a new evaluation population, not historical SAGE reproduction.

Preserve the R3 initializer, accepted E18 driver, all six/nine checkpoint families,
historical scientific results, and the three untracked E12 drafts.

Stages:
1. Inspect and pin the native collection policy and simulator interfaces.
2. Implement a reference-trajectory collector starting from the same R3 physical
   initialization used at evaluation, with disjoint pilot and final random streams.
   H75/H150 are offsets along the reference trajectory, not minimal path lengths.
   No task selection based on compared planners. Log all generation attempts.
3. Integrate released full SAGE in the E18 simulator under the same physical
   contract, preserving method-specific preprocessing and checkpoint statistics.
   Test on pilot records and retain compatibility changes transparently.
4. Freeze a large, justified design after collection validity and SAGE timing
   checks; explicitly specify claims, multiplicity, failure treatment and runtime.
5. Generate independent final records, seal them before comparative outcomes,
   execute the registered arms, independently aggregate and publish all results.

Current stage: source/interface inspection. No final records or outcomes exist.
The known weak random collection policy is not claimed to reproduce the expert
training-data distribution. Pilot quality diagnostics will establish the scope.
Large raw data remain on Prometheus with hashes, generation commands and paths
committed; code, protocols, readable summaries and task state are committed to Git.
No unattended assistant monitoring is implied by cluster execution.

Pilot 300310 failed before collection because the SAGE tree on PYTHONPATH shadowed swm006. Corrected by appending SAGE only after importing the installed common runtime. A local REPL syntax error accidentally resubmitted the old pilot as 300311; that job was cancelled, not accepted as replacement evidence.

Collector pilot 300312 completed: three collector tests passed; 24 accepted reference trajectories from 54 attempts. Rejected 9 initial overlaps and 21 out-of-arena trajectories, independent of compared planners. Every accepted trajectory contacted the block. Neither H75 nor H150 was initially solved in these 24. Pilot stream is disjoint from any final stream. The previous duplicate 300311 had already failed before cancellation was attempted; preserve it as failed, not cancelled.

Six-arm pilot 300313--300318 completed. Five E18 arms executed; SAGE attempts were technical loader failures, not efficacy evidence. SAGE inherited the old JEPA class; besides BF16 incompatibility, that class recomputes rather than preserves a supplied goal embedding. Restore the original E19 pickle mapping to released SAGE LeWM/Predictor classes, retaining the shared swm006 simulator. No SAGE equations or checkpoint weights change.

Corrected SAGE pilot 300319 reached real planning but strict Box enforcement rejected native decoded commands. The released evaluator does not project commands and the native step accepts them. Main SAGE comparison will preserve finite native commands; a separately labelled sage_box sensitivity arm projects them. All methods share the same native environment operation. The bounded E18 output is a method property, not an imposed advantage against an artificially failing SAGE baseline. Both variants will be reported, never selected by performance.

Native SAGE and explicit boxed-SAGE pilots 300320/300321 completed without planner failures. All seven arms have identical initial physical/raw-input hashes on both pilot records/horizons. Pilot evidence is in independent-pusht-evidence. Native SAGE may exceed its declared Box; main comparison preserves this native behavior. Final-data design remains separate from pilot outcomes.

Validation 300322: six tests passed; the exact decoder equivalence test caught float32 coefficient-rounding differences up to 5.96e-8 in the newly handwritten decoder. Replace it with the original installed StandardScaler using pinned coefficients, with no fit. Do not relax the exact-equivalence test. The collector and R3 are unchanged; final data have not been generated.

Validation 300323 passed all 7 collector/decoder/full-budget tests. The large-design simulation completed: N6000 variance-one normal-approximation joint power lower bound 0.837; cumulative marginal power 0.949 in the bounded-extreme simulation. These are planning assumptions, not a finite-sample universal guarantee. Final collection protocol and source have not been changed using comparative final outcomes.

GPU parity300324 passed: bit-identical actions and states to accepted FreshEpisode on all five E18 arms. Final-reference output now saves the exact requested initial vector as well as observed state; no collector dynamics changed. The full sequential reducer, independent CSV verifier, controller dependency tests and negative-signal futility rule are being validated before final data generation.

Final validation300325 completed: 22 collector, driver, physical-outcome, sequential-analysis and controller tests passed. Main design is now frozen before final records: six arms, three primary contrasts, looks1600/3200/6000, fixed alpha spending and strong-adverse futility. All model bytes and R3 remain unchanged. Collector progress logging added without altering generated samples. Full large-study collection and immutable registry are next.

Final collection job 300326 and stage0 chain submitted from frozen source63f0440. Source/registry/protocol are committed before comparative final outputs. Study root: /lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-63f0440. Jobs: {"stage": 0, "cumulative_n": 1600, "task_count": 450, "array_job": "300327", "analysis_job": "300328", "continuation_job": "300329", "dependency": "300326", "source_manifest_sha256": "1b86846d65a9f59ca108fefca6ab77af01e2f543deaa2e4264d784dc9e97f662"}. Host Python preparation initially lacked NumPy; it was rerun in the existing pinned container before any dataset output, with no source/protocol change. No final comparative outcome has been read.
