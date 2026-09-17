# SI1 resource and launch envelope

Preparation only. No real-data fit, optimizer step, simulator call or Slurm submission has been made for SI1.

| Quantity | Fixed allocation |
|---|---:|
| Source references / folds | 192 / 4 |
| Fitting / held-out sources per fold | 144 / 48 |
| Conditions × folds × seeds | 2 × 4 × 3 = 24 fits |
| Updates per fit / total | 1,800 / 43,200 |
| Parameters per fit | 87,937 |
| Existing banks / candidate rows / binary records | 1,426 / 11,408 / 22,816 |
| New labels / GPU allocations / full-data fits | 0 / 0 / 0 |
| CPU reservation | 4 CPUs, 8 GiB, 120 allocation-wall minutes |
| New artifacts including source, logs, failures | 1,000,000,000 bytes |

The 120-minute ceiling is allocation wall time (maximum eight CPU-core hours), not two CPU-core hours. It includes source checks, saved-data reads, preprocessing, all fits, forward evaluation, aggregation, serialization and failed/technical work. One job only; no retries or additional allocation are authorized by this proposal. No queue-time billing is assumed; record queue time separately.

The accepted BP1 job used 356 allocation seconds for 18 fits and 133 for analysis. A crude 24/18 scaling gives 475 fit seconds plus analysis, about ten minutes before reader and host variability. Plan approximately 10–30 minutes, not a guaranteed runtime: new fold sizes and CPU contention differ. No real-data timing fit is performed during preparation. Each fit has a conservative 180-second stop guard (24 × 180 = 4,320 seconds); the worker has a 6,600-second total alarm and scheduler 7,200-second limit. Time is not expanded or settings reduced if a guard is exceeded.

Raw float32 weights total 8,441,952 bytes; four mean/scale pairs 19,872 bytes. Expanded full training matrix is about 57 MB; each fold about 43 MB before temporary float64 normalization arrays. Expected peak is below 3 GiB based on array sizes and the accepted roughly 2 GB CPU-job peak; 8 GiB is a hard reservation, not an empirical measurement for this unrun study. Expected new output under 100 MB; worker payload limit 900 MB reserves 100 MB for source/control/logs. The package must be under 20 MB. No saved input banks are copied into it. Final resource report must include actual allocation elapsed time, process CPU time, peak RSS and all output/log/source bytes.

## Preparation and future execution

1. Run synthetic tests with the existing Python/NumPy/PyTorch environment: `python -B -m unittest test_score_information -v` from `cluster/prometheus`. No test calls the optimizer.
2. Build to an explicitly chosen new directory: `python -B cluster/prometheus/package_score_information.py --output <new-package-directory>`. This generates a manifest, hashes every packaged dependency, and writes `APPROVAL-TEMPLATE.json` with execution disabled. It does not read numerical banks, invoke SSH or submit jobs.
3. After separate launch approval only: transfer that exact package into a new Prometheus snapshot, validate its manifest, create a source-hash-bound execution approval with the exact caps, and submit ONE CPU job with `--cpus-per-task=4 --mem=8G --time=02:00:00`, no GPU/GRES. Use the site's accepted CPU partition/account (verify availability at launch; do not substitute a GPU allocation). Invoke `bash <snapshot>/cluster/prometheus/run_score_information.sh <snapshot> <approval> <new-output>`.
4. The runtime is the existing py311 `hi-lewm-artifact-py311-cu121-swm006` environment inside `pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif`, without GPU passthrough. Runtime versions are recorded in output; approval binds the existing runtime paths. No installation or environment mutation. Inputs bind read-only, output parent writable. Record package SHA and scheduler allocation externally. Launch must check that total new source/control/logs stay inside the reserved 100 MB and no prior attempt exists; no automatic retry.

Keep completed and failed outputs in the new run namespace. Final transfer may use the designated external thesis SSD after its identity is verified, never an implicit laptop-bank backup. This preparation contains metadata/source only and does not copy research payloads.
