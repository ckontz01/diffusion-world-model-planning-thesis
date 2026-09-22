# ACV0 preparation authorization and boundaries

User direction dated 2026-09-23: read the ACV0 assignment and attached prototype, implement it thoroughly without omission. The full supplied assignment is preserved as `ACV0-INSTRUCTION.txt`. This is new bounded implementation authority, not authority for the proposed real pilot.

Base: `02a6157ecb11ff2a9cf6ced6ce0523b181805db0`. Exclusive worktree/branch: `active-counterfactual-verification-preparation-20260923`. Prior AV0/addendum, LGP/CVL/BP1 records and E12 drafts are read-only. No historical controller, research checkpoint, reference payload, physics environment or GPU is opened/run. No new dependencies or runtime changes. Real execution is disabled in the package.

Preparation ceiling: 14,400 cumulative scripted wall-seconds, four CPU threads/affinity, 8 GiB aggregate process memory, 1,000,000,000 new bytes. All numerical attempts use `bounded_run.py`; failures are retained and not automatically retried. Ordinary source inspection and publishing are not scientific runs. Preserve only the new small package on the designated THESIS_SSD; no historical archive retransmission.

Implementation plan: authenticate/import the original ZIP; run supplied unit tests and main experiment once; implement the four-component neural model, deterministic matched tree, one-shot adapter, controls, mock collector and independent checker; execute focused contract tests and fixed synthetic training; reconcile metadata-only roles; verify the five named primary-method leads; propose one finite source-disjoint developmental pilot; commit, push/read back and verify small backup.

The available local Python has NumPy but no PyTorch. Use a fully trainable NumPy neural implementation with explicit analytic reverse-mode gradients, Adam, gradient checks and save/load tests. No installation is needed. This is a neural mixture, not a relabelled table. The original table and Gaussian modules remain analytical/artificial references; Gaussian compression is excluded from the neural model.

Terminal-prefix handling is made explicit: a three-class head estimates terminal-success, terminal-failure and active-prefix probabilities before execution. The four-component response density is conditional on an active prefix. Thus unconditional value is P(terminal success) + P(active) E[max continuation success | active response]. Terminal records carry no fictional response or suffix labels. This necessary schema extension will be tested, not hidden by filtering survivors.
