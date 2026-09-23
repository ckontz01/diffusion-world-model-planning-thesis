# ACV0 bindings-v2: launch occurred; first allocation failed; fail-stop preserved

## Status

**Not complete. No research work is currently running.** The technical prelaunch repairs passed local and host checks, but the included first collection allocation failed an incorrectly specified GPU-name check. The controller stopped and submitted no second job. No retry, resumed controller, replacement source or mutation of the launched source occurred.

Preparation/correction commit `5d382ddf294ee711d21e137091c59fe3a57a05df` was pushed and read back from the exact remote branch. The designated THESIS_SSD backup verified29 new package files /791,461 bytes; receipt SHA256 `40b8821be386c9a69af799e2fa93346a7ac74bef2367ab82fb1d71037e6bc45a`. The receipt lives at `bindings-v2/DELIVERY.json`; its byte hash is authoritative. Historical backups and the v1 source closure were not rewritten. The v2 test ledger subsequently contains one additional appended candidate-test receipt, not part of that earlier backup snapshot.

## Authenticated launch

- Manifest: `5630b222e8a88d0eaa45408876929724734d1f992afa657131ac770fb0400fa9`.
- Thin archive:542,720 bytes /39 members / SHA256 `ef5343b6cf1a686585987f99dccc8789612418c08ac30f99b9680a78a7566d5e`.
- Remote extracted members:508,560 bytes; all member bytes read back and authenticated.
- Enabled approval: `7ea5f67225ee1bff091e705e7515a4ed8f3589694e6093f1c2e7c607d27a6a88`.
- Instruction byte hash: `e6f0a90b53f902bf7b65cacb39ca330043aa6cd5a2cb857b881375c61f30fe1f`.
- Source: `/lustreFS/data/superworld/ckontzias/thesis/snapshots/active-counterfactual-verification-bindings-v2-5630b222e8a88d0e`.
- Control: `/lustreFS/data/superworld/ckontzias/thesis/staging/active-counterfactual-verification-bindings-v2-5630b222e8a88d0e`.
- Run: `/lustreFS/data/superworld/ckontzias/thesis/experiments/active-counterfactual-verification-pilot-v1/run-5630b222e8a88d0e`.
- Controller: PID550069, Linux start_ticks892062738, launch Unix1790163738.4587762, host pinned `/usr/bin/python3.9 -B -S`. The process had exited at Unix1790163789.6052873.
- Submission: job304189, `collect-fit-490`, Unix1790163741.2795682.

## Exact reconciliation and charge

One claim, one submitted allocation, one terminal row, zero successful jobs and zero unresolved submissions. Job304189 ran on gpu09 in partition a6000, account superworld/QOS normal-a6000:4CPU,24GiB,oneGPU,1,800-second cap. Terminal FAILED /1:0 /23 allocated seconds. Charged GPU-allocation seconds:23. CPU-stage allocation seconds:0. Scheduler TotalCPU14.193 seconds and batch MaxRSS608480K are retained with their scheduler scopes; worker process CPU9.235697017 seconds and worker wall15.399683655 seconds are separate measurements. No queue time is charged. No retry or requeue occurred. The exact job had no live queue row at reconciliation Unix1790163825.1672149.

The controller wrote STOP.json and no technical-tranche gate or COMPUTE-COMPLETE. No job for545 or any later source was submitted. No model fitting/evaluation/analysis stage ran. All partial files, failed source snapshot, log bytes and ledgers remain in place.

## Fault and evidence boundary

The worker raised `ValueError('Exact GPU class; no substitution')` at the check `torch.cuda.is_available() and 'A6000' in torch.cuda.get_device_name(0)`. This check follows successful loading of the authenticated Le-WM checkpoint onto CUDA and its tensor fingerprint, but precedes `source_factory`. Therefore one authorized checkpoint load occurred, while no reference payload was read and no simulator episode, branch, fit or scientific outcome was produced. No scientific outputs have been inspected.

Scheduler metadata places the failed job on gpu09, but does not record its runtime CUDA device-name string. Existing source-only hardware specifications (`cluster/prometheus/gdp_cem_e11_specs.py`, lines35–36, and `gdp_cem_e12_specs.py`) identify gpu09 as **NVIDIA RTX6000 Ada Generation**, while the site's scheduler partition is named **a6000**. The actual spelling in those files is `NVIDIA RTX 6000 Ada Generation`, which does not contain `A6000`. The name/partition conflation is a concrete code defect; the exact device name in job304189 is an inference from existing metadata, not a fresh runtime measurement. Do not claim an independently recorded hardware identity that the failed code did not save.

## Tested correction candidate, not a launched revision

`../recovery-candidate-r1/hardware.py` verifies the exact historically specified device name, one visible device and CUDA availability; it always records observed identity before any model/reference load. The candidate `worker.py` moves this gate before `load_backend` and records hardware in technical projections. It changes no action, prediction, training, sampling, data role, source ID or analysis rule. Three stdlib CPU regression tests passed in0.007 test seconds /0.329 bounded wall seconds,29,229,056 peak Job Object bytes, four-core affinity. They check exact-name acceptance, rejection of other hardware/unavailable CUDA/multiple visible devices, and gate-before-payload call order. These are synthetic tests, not verification of the live hardware.

The candidate has no enabled approval, source manifest, run namespace or submission path. The executed v2 source remains unchanged. The first two included sources must still pass their actual technical gates if a scoped recovery is authorized.

## Remaining authorization boundary

The user's direct technical-fix instruction authorizes this repair work, but the original execution contract explicitly forbids automatic retries/additional allocations and fixes339 attempts. Completing339 successful jobs after this failed allocation would require340 total attempts. Reserving all original remaining per-job maxima plus the23-second failed charge would also total220,823 GPU-seconds, above the220,800 cap. Charges cannot be reset or hidden.

A scoped decision must explicitly resolve the replacement attempt and full-future reservation, without touching prior artifacts. One possible finite option is340 total attempts including304189, exactly one replacement of490 capped at1,740 seconds (120-second preservation margin), then the original338 remaining jobs unchanged:23+1,740+79×1,800+256×300 =220,763 maximum GPU-allocation seconds. This is a proposed resource-recovery contract, **not** authority to execute it. No further retry, source replacement or allocation would follow any new failure. The selected reasoning conversation may instead direct stop or specify another valid bounded recovery under the user's delegation.

The designated reasoning conversation was opened at its exact URL but is blocked by a Cloudflare “Verify you are human” check. No CAPTCHA action, login, security bypass or message submission was attempted. A ready-to-paste scoped report is preserved. The old LGP monitor remains PAUSED and historical lines remain closed; it was not repurposed or reactivated while no research is running.
