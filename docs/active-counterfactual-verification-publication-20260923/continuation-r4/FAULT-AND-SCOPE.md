# R3 accounting-placeholder fault and finite R4 recovery

The two-hour monitor observed R3 controller940709/start_ticks894795578 exited, with STOP-R3 and no computation-complete marker. This is a controller/accounting issue, not a failed scientific worker. The exact R3 snapshot is retained as continuation-r3/HEARTBEAT-20260923T212620Z.json. New read-only BASELINE-CAPTURE.json reauthenticated the old closures, all completed workers and every allocation without decoding research outcomes.

## Exact diagnosis

At Unix1790193211.049551 the first accounting poll for newly submitted304237/collect-fit-1207 returned:

```
304237|allocation|PENDING|0:0|0|0||gpu09||Unknown|superworld|
```

R3 checked `allocation` against `acv0r3-collect-fit-1207` and stopped with `ValueError('Wrong scheduler task identity')` at1790193211.075619. This raw response was preserved in SCHEDULER-OBSERVATIONS.jsonl, unlike the prior R2 fault. Later authenticated accounting names the intended task correctly and records COMPLETED0:0/157seconds on gpu09. R3's terminal ledger has12 new completions and one unaccepted successful allocation; its last recorded4705GPU-seconds must not omit304237's157seconds.

## Reconciled boundary

-37 successful logical tasks,38 historical allocations including failed304189/23seconds. All37 seals, original approvals, technical checks and exact hardware associations pass.
-13 actual R3 submissions,12 R3 terminal records;304237 is authenticated now, never resubmitted. Existing304220's original acceptance in R3 remains historical fact.
-4862 charged GPU allocation-seconds;0 CPUstage seconds. No live, unknown or ambiguous allocations; all three prior controller identities inactive.
-302 never-submitted tasks, beginning collect-fit-256; no model, preanalysis, completion or final-preservation directory exists yet. Included initial tranche remains unchanged.
-R3 STOP SHA256 `6bbed51c09ce10dbbdf8430173f5a889f6eb9682cb2c7a7fa2abb01c97f2cb1c`; full baseline SHA256 `a66a398bb11ab71ac4c0191d9fdd54c5fc29aca1cc7962f36e1d608642394476`.

## Authority and correction

Use the direct advance monitoring/technical-recovery instruction committed at ace242ee5ea14af284401ad857fc3a49b30e1b58. No redundant approval is requested. R4 is a separately frozen, exclusive control source/approval/ledger/finalizer, not a patch to R1/R2/R3. It grants no scientific or resource/data expansion.

The scheduler parser treats only the exact observed incomplete GPU pending placeholder, with the exact submitted ID, as an incomplete status observation. It shares the existing finite eight15-second waits; the ninth incomplete observation stops. A completed row still must identify the exact task and pass complete numeric/resource accounting and original worker authentication. No missing field is turned into a terminal zero charge, no worker is retried and no arbitrary mismatched name is waived. Raw observations remain bounded/preserved.

R4's finite contract is37 reused tasks plus302 new original tasks; zero new replacements or automatic retries. Expected complete accounting remains339 successful unique observations and340 total allocations. Historical charges4862 plus full remaining GPU reservation154200 equal159062, within220800. CPUstage cap21600 and all original resource/storage/worker caps remain unchanged. R1/R2/R3 test usage and all new test attempts count against the existing7200second ceiling. Scientific aggregates remain unopened until complete acceptance and designated-SSD preservation.

Finalization authenticates both old unresolved-observation events by their dated resolutions, all339 suppliers/gates/models,340 allocations, exact charges and all nine original/recovery source/control/run roots. Old STOPs and evidence are retained, never deleted. Final archive creation is one-shot when absent; partials require separately diagnosed bounded technical handling under the same authority. AV1, historical decisions/studies and E12 drafts are unchanged.

This document records the recovery plan and diagnosis, not an assertion that R4 has launched. LAUNCH and observation receipts, once present, establish actual execution.
