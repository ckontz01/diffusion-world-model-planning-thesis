# Native chart and historical origin: source evidence, not physics validation

All inspection was source/configuration/metadata only. No HDF5 frame/action/state payload, checkpoint execution or simulator instance was opened.

## Reacher coordinates and permitted information

Live custom ReacherQPosMatchTask.get_termination (SHA256 e5e2e82c0621efca7b4c3c194f422c946db59edb12db7735fbe8bdcf12e37e7c) uses each raw abs(qpos-target_qpos)<.05. Revised S1 predicts TWO raw coordinates with the frozen ridge; both candidate and visual goal are decoded by that SAME own-backbone readout. No wrapping/clipping, true goal-state substitution, angle sensor or winding counter.

Live dm_control/suite/reacher.py SHA256 ee829f7f1130664f650144188ddefb7349d74e3102ac6337b37bac7d23612a78 calls randomize_limited_and_rotational_joints. randomizers.py SHA25601a4621e187040054b1dedf8fa0e58508bf416fc6db23c76aca17b9ecc5ed351 initializes unlimited hinges uniformly[-pi,pi], limited hinges uniformly within their limits. The native XML SHA256849e1e3dd8e79b8f5796bd6e32b0d7a51b916355584402d8f803d74ad35ad193 leaves shoulder unrestricted and wrist limited[-160,160]degrees. A reset chart is not a global episode chart: native raw shoulder qpos need not remain in[-pi,pi]. No normalization/clamp was found in the inspected task/wrapper paths. No claim is made about the frequency of winding in selected parents.

stable_worldmodel Reacher wrapper SHA25605bbf859383a047b92598dc0553a9e917193a732f065d2ed05c31005d03ba2cb modifies colors, light, densities, target shape/visibility, not these joint limits. DMControlWrapper SHA25613d55bf73f9b7f8a9b5a2b380e12750e253a391716e64e65f795b1c9fff8bc08 exposes qpos/qvel in info, but those fields are NOT deployment inputs here. Native render defaults224×224, camera0, RGB physics renderer. Le-WM policy uses one visual context, native predictor history_size3 rollout semantics. DINO context remains unbound.

Physical geometries separated by an entire shoulder turn can give identical images. A finite visual history without an authenticated chart origin does not universally identify that raw coordinate. The artificial identical-feature/two-target fixture predicts one identical value for both targets and retains nonzero raw error; it does not leak targets to pass. Future authorized validation must report held-out realized raw-coordinate MAE/RMSE without tuning. Poor performance qualifies THIS score, not all possible scoring interventions. No chart exclusions or task substitution.

## What exact historical replay requires

The current COHORT metadata contains task, parent ID, partition, length, row offsets and prior source index. These are not full physical-origin receipts. Live DMControl reset accepts a seed and optional state=[qpos,qvel]; set_state assigns those arrays and calls forward(). It does not authenticate full original model variation, target randomization, RNG history, time/actuator/integrator state, or prior hidden dynamics. A mid-episode call to this API is therefore NOT an accepted historical reconstruction.

Needed before production: authenticated native root construction and seed/RNG/variation/render/physics settings; complete action dtype/normalization/repeat history; root and every replay observation identity; correct original dynamic state/history; native target installation only at the diagnostic origin (without changing historical replay or adding physics); branch-owned warm-start/history/tail streams. Check root data actually available under future payload authority; do not assume seed or complete hidden state exists because a loader exposes qpos/qvel. No newly collected root is to be described as historically identical.

The artificial SourceHistory/factory runner checks complete replay action and observation hashes, original50-action diagnostic clock, terminal/truncation and branch tail ownership. It is mocked, not native replay certification. Native goal-state endpoint supervision may be used by the independent physical checker when eventually authorized, never by the visual prediction/S1 inputs.

Reacher wrapper action_repeat2 and XML timestep.02 are source facts; actual control_timestep/environment kwargs and reset recompilation behavior still require a runtime contract. PushT inspected native10Hz controller/.01s step gives10 physics substeps/action. Physical controller-step counts are not automatically equal simulator-step counts across tasks.
