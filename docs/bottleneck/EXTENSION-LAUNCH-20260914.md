# Extension launch chronology

The user approved the exact additional28 design. Scientific runner source differs
from the pilot only in the fixed allowlist and corresponding SHA-order length.
No completed pilot source/output is edited or reused as a new execution.

Initial freezebcf573a passed99 local tests, shell syntax and all56 manifest entries:
snapshot `/lustreFS/data/superworld/ckontzias/thesis/snapshots/diffusion-bottleneck-extension-bcf573a`;
manifest `36bd7b43ff3f33a5f103c3564750204b03f86d1506056761429b85f0586158ac`;
contract `7ad78113edc32053890bf2ec22dc4f2127aa79cd85bb21c9b893fd17ff74123a`.

The lightweight dispatcher then failed before its first subprocess was created:
login-node Python3.6 rejects subprocess.check_output(text=True). No sbatch command
or model execution occurred. The empty run-root DISPATCH.jsonl and frozen source
remain preserved. This is execution compatibility, not a scientific failure.
The sole correction uses universal_newlines=True (equivalent text decoding,
supported by Python3.6), with a regression that checks the exact call signature.
Scientific code, contract, data, seeds, models, limits and analysis are unchanged.
A separately frozen corrected source/run root is required; no in-place amendment.

## Corrected launch

Source54e3acf passed100 local tests and shell syntax. All57 frozen manifest entries
verified. Contract SHA unchanged. Snapshot:
`/lustreFS/data/superworld/ckontzias/thesis/snapshots/diffusion-bottleneck-extension-54e3acf`.
Manifest `94a57124ca1b5dbf311023869d618377de978856cc3ef4b25de007c16b6a9565`;
tar `bf69afa64526c51fcd320eace7659f6634123b21664c327ea980f8fe398a92f6`.
Run root:
`/lustreFS/data/superworld/ckontzias/thesis/experiments/diffusion-bottleneck/extension-20260914-54e3acf`.

Dispatcher submitted301003 for index8/ref567/repeat0 at2026-09-14T09:27:03Z.
First observed scheduler state PENDING(Resources), not running. Subsequent exact
job IDs and terminal allocation sizes are in append-only DISPATCH.jsonl. No
second job is submitted until a successful terminal state. No new scientific
artifact was opened at launch. Unrelated E14 pending jobs are unchanged.

Combined report runner is frozen in the same snapshot. New backup verification
is byte-only and will run after combined acceptance, alongside rechecking the
eight pilot copies rather than rewriting them. Completion/results remain pending.
