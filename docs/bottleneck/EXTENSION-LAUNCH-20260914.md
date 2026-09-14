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
