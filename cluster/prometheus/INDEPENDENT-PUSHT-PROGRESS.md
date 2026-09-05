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
