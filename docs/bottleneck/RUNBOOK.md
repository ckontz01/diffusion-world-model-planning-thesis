# Bottleneck package: execution and recovery

## What is and is not done

The files in this patch were prepared and tested in the current ChatGPT sandbox. They have not been pushed to GitHub or installed on Prometheus. The live GitHub experiment branch was read at commit `001aad99a2e2e6a141797e0c516604e7188d706a`. An attempted new-branch action was blocked before execution. Desktop Commander reported the registered desktop offline, last seen 11 September 2026.

There is no new cluster job or background monitor. No planner was modified or trained. The existing summary and full outcome tensor were analyzed locally after their archived SHA256 values matched. Their arm means, original primary differences and standard errors reproduced. All 15 method pairs and 20 diagnostic contrasts were rechecked by a separate standard-library implementation. Raw-trajectory reduction and backup revalidation remain unrun on real data; the simulator-intervention runner is not implemented. Synthetic unit tests do not change those limitations.

## Patch application

The patch only adds new files. It does not alter the old README, historical reports, model code, or data. Apply it to a clean checkout of the experiment branch after inspecting local changes. Do not reset or force-push a checkout, and do not add unrelated E12 drafts.

```bash
git switch -c diffusion-bottleneck-analysis independent-pusht-benchmark
git apply --check diffusion-bottleneck.patch
git apply diffusion-bottleneck.patch
PYTHONPATH=cluster/prometheus python -m unittest discover -s cluster/prometheus -p 'test_diffusion_*.py'
```

These are handoff instructions, not commands already executed on the user's computer. A future authorized connector/CLI session can make focused commits of these new paths and read back their GitHub identities. No claim that commit access has been repaired is made here.

## Local summary or outcome analysis

The base repository already contains the completed `look-0` archive. Separate exact copies of `SUMMARY.json`, `EPISODE-TENSOR.npz` and `INDEPENDENT-VERIFICATION.json` are included under `inputs/look-0/` outside the patch. These support standalone reproduction without cluster access.

```bash
python cluster/prometheus/diffusion_bottleneck.py \
  --summary cluster/prometheus/independent-pusht-evidence/look-0/SUMMARY.json \
  --out /tmp/diffusion-bottleneck-summary.json

python cluster/prometheus/diffusion_bottleneck.py \
  --archive cluster/prometheus/independent-pusht-evidence/look-0 \
  --bootstrap 10000 --bootstrap-seed 20260913 \
  --out /tmp/diffusion-bottleneck-paired.json

python cluster/prometheus/verify_diffusion_bottleneck_outcomes.py \
  --archive cluster/prometheus/independent-pusht-evidence/look-0 \
  --report /tmp/diffusion-bottleneck-paired.json \
  --out /tmp/diffusion-bottleneck-independent-recheck.json
```

Both commands refuse an existing output file. They verify fixed input digests, not merely filenames. Summary mode cannot bootstrap or reconstruct pair overlaps. Outcome mode requires the exact tensor and historical independent-verification file. Optional `--bootstrap 10000` is exploratory reference-cluster resampling, not a new confirmatory test.

The analysis depends only on Python and NumPy. Development tests ran with Python 3.13.5 / NumPy 2.3.5. The existing cluster environment uses another pinned runtime; this package has not passed its remote tests yet. Do not silently upgrade that environment.

## Backup recovery after the desktop reconnects

Use the established Windows → `Thesis-Ubuntu` user `chris` → SSH alias `prometheus` route with noninteractive authentication and strict host-key checking. Do not copy private keys into this chat, weaken host verification, or infer a new WSL disk failure from an offline device status.

First check WSL filesystem health read-only and check the recovery repository without changing its branch. If I/O or read-only errors recur, leave bulk writers stopped. Do not run an unrequested destructive repair.

The existing incremental copier skips previously indexed shards. Restarting it is therefore NOT a revalidation of bytes after the earlier disk incident. The new verifier rehashes every indexed shard:

```bash
python cluster/prometheus/verify_diffusion_backup.py \
  --local-study /home/chris/thesis-artifacts/independent-pusht/final-20260906-4a608e5 \
  --out /mnt/c/Users/Chris/thesis-recovery/bulk-recheck-new.json
```

Return 0 means all 450 local shards match their local seals, 3 means an internally consistent but incomplete local copy, and 2 means a validation/read failure. Without `--source-study` pointing to an accessible canonical filesystem, it is NOT a canonical-source match certificate. The 6,000 reference files and the compact analysis archive need separate verification. This command does not certify or repair them.

After confirming destination free space and filesystem health, the unchanged copier can make a fresh independent copy using its supported flags:

```bash
python cluster/prometheus/backup_completed_independent_pusht.py \
  --study /lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-4a608e5 \
  --destination /mnt/c/Users/Chris/thesis-recovery/independent-pusht-bulk \
  --once
```

Do not delete or overwrite unreadable old copies to make this look successful. A fresh destination avoids trusting the old index. Rehash the copied files afterward and retain the authenticated canonical-source receipts. Hashing reference bytes for backup is not permission to inspect unused test outcomes for tuning.

## Read-only analysis on Prometheus

The provided launcher reproduces the image/environment paths from the existing run wrapper and requests no GPU. It only executes explicitly; it does not submit itself. After remote tests, invoke it inside an ordinary site-approved CPU allocation, not as a heavy login-node job:

```bash
bash cluster/prometheus/run_diffusion_bottleneck_readonly.sh outcomes /absolute/new/output-outcomes
bash cluster/prometheus/run_diffusion_bottleneck_readonly.sh traces /absolute/new/output-traces
```

`traces` validates the complete fixed stage-0 grid, reads only its completed trajectories, and writes an external new report. It cannot read later-stage evaluation payloads. It is not an implementation of simulator counterfactual interventions.

## After analysis

Review all diagnostic categories and method pairs, including unfavorable findings. Then implement the simulator branch-point replay and same-bank controls in PLAN.md. Do not launch the expensive intervention grid before the branch-point and baseline replay checks work. That dependency concerns interpretability, not a new requirement that an imitation proxy must already look favorable.
