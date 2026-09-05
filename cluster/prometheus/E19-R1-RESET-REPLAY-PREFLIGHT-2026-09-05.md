# E19-R1 reset-and-fixed-action replay: source preflight, not a result

Date: 5 September 2026. Outcome-informed engineering follow-up requested
after E19-L1. E19, D2, L1 and historical E18 artifacts remain unchanged.
No simulator execution or new planner call has been performed by R1.

## Requested check

Check the SAGE and E18 evaluation interfaces separately on a small explicit
set of already-exposed records. Observe reset inputs/RNGs, state after reset
and every dataset state/target hook, fresh observations versus supplied
observations, primitive actions entering the base environment, and state
after each primitive step across fresh processes. Compare by episode/start
identity. Distinguish restoration, action delivery, stepping and observation
construction. Do not compute a benchmark success table.

The actual complete integration/controller state matters, not just the
dataset-overlaid first image or low-dimensional observation. Read-only
instrumentation must itself be checked for state/RNG side effects. Do not
add seeds or repair state setters without a demonstrated technical basis.

## Missing historical executed-action values

The pinned diagnostic source at
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/trace_gdp_cem_e19_discrepancy.py`
was inspected directly. Its parent source-manifest SHA-256 is
`e347bc087381ecf0902581e8225165dbd64c887eba661b74b064c09d4e13d7fa`.

- `TraceRecorder.end_plan` stores `value_record(output['actions'])`: dtype,
  shape and SHA-256, **not the action tensor values**.
- `capture_bank` stores the first CEM iteration's candidates, costs, elite
  indices, actual local goal and input dictionary. It does not store the
  final CEM mean/selected action chunk after all 30 fitting rounds.
- `capture_top_bank` does store `top_actions`. Thus the PushT prior-top
  sentinel has the actual returned action values; this exception does not
  supply the missing Cube/CEM returned action values.
- Historical E18's evaluator writes episode identities/outcomes and planner
  diagnostics; the inspected planner diagnostic payload does not save the
  returned action sequence. Its returned `actions` are consumed by the
  scheduled policy rather than persisted as a replay tensor.

The existing first-call equality conclusions are valid hash comparisons.
They do not mean all compared tensor values were archived. Reconstructing a
missing final CEM action chunk would require new planner execution, which
the new request expressly forbids. A stored first-round candidate must not
be presented as the action that was historically executed.

## Choice required before the complete replay scope can be frozen

Either use a saved candidate sequence as an explicitly labelled fixed
engineering stimulus for records lacking executed action values, or limit
those records to restoration checks. Both can avoid new planning; neither
may be labelled exact historical action replay. The authentic saved PushT
prior-top action chunk remains available as a control.

The user has been asked whether the candidate-stimulus substitution is
acceptable. No choice is inferred from a preselected UI option. No R1
snapshot, scheduler job, new simulation, or runtime correction is authorized
by this preflight note itself.

## Preserved boundaries

No full SAGE grid, E20, E18-versus-SAGE performance comparison, confirmation,
training, author contact, or protected D5/D3/D4 metrics/P3/P4/C1/I1 access.
No confirmation-readiness conclusion is established by this source preflight.
The diffusion planner remains unchanged. Greedy-64 has been added only to
the [unfrozen confirmation outline](E18-CONFIRMATION-OUTLINE-2026-09-05.md),
with exact shared first-proposal-bank identity and prospective inferential
role requirements.
