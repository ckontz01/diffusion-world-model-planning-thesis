# R3 sealed engineering evidence

`core/` contains the inventory and complete24-scenario audit from each pinned
runtime. `arms/` contains all ten checkpoint-backed arm/batch audits. Every JSON
has its original adjacent `sha256.txt`. The three source manifests identify the
core, successful arm harness and preserved failed arm harness; failed logs remain
on Prometheus rather than replacing any successful evidence.

Run `python cluster/prometheus/verify_gdp_cem_e19_r3_result.py` from the repo.
It verifies seals, identities, flags, counts, reset independence, within-stack
cross-arm/slot/input equality, and fixed-action agreement with singleton/core
references. No simulator, model, dataset or protected artifact is loaded.

These are technical hashes/invariants, not success/reward metrics. E18 audits
explicitly say its non-action scaler coefficient values were not checked; raw
lowdim equality and native image/action preprocessing were checked instead.
No zero-default dynamic field is represented as recovered historical state.

The core has48 scenarios/96 fresh resets/144 actions. The complete arm gate has
560 initializations/885 actions and zero solver invocations. The failed first
arm harness is separately disclosed in the implementation record, not reused.
