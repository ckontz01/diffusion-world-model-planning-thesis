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
