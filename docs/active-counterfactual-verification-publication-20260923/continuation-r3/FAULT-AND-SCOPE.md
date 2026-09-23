# ACV0 R2 status fault and narrowly authorized R3 continuation

The user directly requested **FIX IT AND RESUME IT** after the reported R2 stop. This authorizes repairing the documented control-status problem and resuming the unsubmitted remainder under the original scientific settings/caps. It does not authorize repeating successful work, research-data access expansion, new models, retries, hardware pilots or a new experiment.

## Observed fault

R2 controller788617/start893946619 exited on `ValueError('Unambiguous scheduler columns')`, recorded at Unix1790185866.1308615 (2026-09-23 17:51:06UTC). STOP-R2 SHA256 is `8211155b7883dd28a857f66d014ac2605ef54fccd348550972acb3c282742796`. Controller traceback points to the strict row parser called before checking active state. R2 did not preserve the offending raw accounting response. The exact transient missing field cannot be asserted retrospectively.

The parser stripped trailing separators and therefore removed empty final fields. R3 tests explicitly reproduce that structural failure and verify preservation of field positions, delayed accounting and fail-stop handling for contradictory records. Slurm's [official sacct documentation](https://slurm.schedmd.com/sacct.html) distinguishes parsable output with and without an extra trailing delimiter. No numeric defaults or relaxation of terminal worker acceptance are introduced.

## Exact read-only reconciliation

`BASELINE-CAPTURE.json` retains the successful configured-SSH-stdin observation and all technical metadata, hashes and prior controller traceback. No scientific outcomes were decoded. Both prior controllers were inactive by PID and start_ticks. All25 allocations were terminal with no live/unknown campaign jobs;24 unique scientific tasks succeeded. Original failed304189 remains charged23seconds. Original successful304193 remains80seconds. All original and R2 source/control/run bytes were inventoried and authenticated.

The last allocation304220 (collect-fit-1342, attempt1) completed0:0 in160seconds even though the controller had stopped. Its SEAL SHA256 is `df758217cca95caedeb5912a3770bb48f9367bd26e0bcab077188693e55c2a04`. Complete worker seal, original source/approval/spec and TECH/HARDWARE checks passed. It is not retried. The old missing acceptance event remains missing in the immutable R2 ledger; a new dated R3 acceptance resolves it in the combined view. No backdating.

Charges are3015GPU-seconds and0CPU-stage seconds.315 tasks have never been submitted; the next is collect-fit-505, attempt1, original1800-second limit. The original included490/545 tranche already passed and is not repeated or rewritten. Collection, two192-update CPU fits, model freeze,256 evaluations and oneCPU analysis retain the original order, input roles, settings, seeds and specifications. Successful final counts remain339 scientific tasks and340 allocations—not341—with only the original failure and replacement.

## Separate control namespace and preservation

R3 is frozen outside the executed R1 and R2 closures. Its approval binds the exact direct instruction, baseline, original scientific identity, old R2 identity and both historical STOP hashes. Only315 new submissions are permitted; all24 successful keys are blocked from every new submission path. No original controller is restarted. New R3 ledgers, logs, identity and stop resolution are separate append-only/exclusive records.

Original GPU/CPU/storage caps are unchanged; all R2 and R3 additions are counted. Tests share the original R2 cumulative two-hour local ceiling, four CPU threads,8GiB and250MB artifacts. One synthetic test fixture initially lacked AllocTRES in a failed-row mock; that test-only deficiency and its failed receipt are retained, and the fixture is corrected before the final full suite. No failed research task or successful output is rerun during preparation.

Commit/push with remote readback and verified designated-SSD backup of only the new small R3 package precede staging/launch. Final scientific aggregates remain unread until complete acceptance and verified new-study archive preservation. The final adapter includes all original R1/R2/R3 source, authority, stops/resolutions, ledger segments and successful outputs. Historical studies, monitors and E12 drafts remain unchanged. A new unresolved technical failure still stops dispatch; this is not blanket retry authority.
