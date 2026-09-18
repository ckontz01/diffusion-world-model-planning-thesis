# LGP1 one-time action-guard recovery launch

Published source/approval commit
`8db1d26f5889e8bdfaff323658914b1b25121965` was pushed and remotely read back
before launch. All35 synthetic tests passed in checkout and in the immutable
export; the package seal was checked before/after exported tests. The original
failed source/output/approval/ledger were preserved, not overwritten.

## Identity

- Source manifest: `b96b797315320184c3289e09d7a5c43f898ef2432ba57deb86b1a8094fb7653a`.
- Unchanged input lock: `b21bac97520696b8bb2008a3cfef3f5188d4c59dd117bc158cc2fe2e86ff5aaa`.
- Source tar: `a9342a060657c29f916f136c25d1025a84e61525434016f4d24c5883027feb9c`,1024000bytes.
- Actual uploaded recovery approval: `60d92b0ae4fa70d930a8ee602face7b957e0daf34859ed197fd954f47bc94468`.
- Source directory:975556bytes. Designated THESIS_SSD GUID unchanged,331261349888
  bytes free before packaging. Export and member-verified archive retained at
  `D:/THESIS-BACKUPS/local-goal-proposals-20260918/preparation-action-recovery-20260918`
  and its adjacent `.tar`. This is source preservation, not final output backup.

Under `/lustreFS/data/superworld/ckontzias/thesis/`:

- Source: `snapshots/local-goal-proposals-20260918-b96b797315320184`.
- Control: `staging/lgp1-action-recovery-b96b797315320184`.
- Run: `experiments/local-goal-proposals-20260918/run-b96b797315320184`.

## Preflight and launch

Host Python3.9.6 imported the controller without NumPy, authenticated the full
source, approval and preserved failed-cache seal. The actual exported
`LanceReader` plus `aligned` read the exact known failing P1_train window:
episode12540,t39,delta15. Its packed[3,10] action bytes retain SHA-256
`058fb23a28b0525a8de861fdc23e45aba6093d81fbbb3984f416413175ac71ea`.
This check used no model, physics or GPU allocation and is recorded in
`EXACT-WINDOW-READER-CHECK.json`. It confirms the identified fault is corrected,
not that the complete research runtime has already passed.

The exclusive controller launch is recorded in `LAUNCH-INTENT.json` and
`CONTROLLER-PROCESS.json`: PID2987558,start ticks851197901,
Unix1789755090.091316. The identity matched on read-back. The old controller
was absent and exact Slurm job301977 reconciled FAILED1:0/46seconds before
submission. No other prior or active LGP1 attempt was accepted.

Replacement cache job **301979**, submitted Unix1789755090.8209367, was read
back RUNNING at elapsed26seconds,239-minute limit,4CPUs,24GiB,oneGPU. Empty
controller logs and no STOP record at that check. The running0:0 field is not
a terminal-success assertion. Partial scientific output remains unopened.

## Unchanged study and honest accounting

There are still6fits/72000updates,8technical and384main episodes, with the
same targets, sources, roles, normalizers, model definitions, refinement,
decoder, online support, initialization, seeds and endpoints. Recorded targets
are not clipped or filtered. Six models freeze before evaluation as before.

The user-authorized replacement means204GPU attempts including preserved
failure301977, plus oneCPU attempt. The failed46seconds are charged from the
start;239-minute replacement cache plus all remaining maximum reservations
total335986GPU-seconds including failure, below336000. The same12GBtotal,
5.9GBworker,200MBsource/control and10MBepisode caps include preserved failed
artifacts. Final preservation explicitly includes both run/source/control
histories. No automatic second retry or further study is authorized.

The controller is detached on Prometheus and owns serial waits/dispatch;
laptop/SSD connectivity is not a compute gate. Final complete-grid seals,
physical endpoint evidence, accounting and member-verified SSD backup are
still pending; no result or model promotion is claimed.
