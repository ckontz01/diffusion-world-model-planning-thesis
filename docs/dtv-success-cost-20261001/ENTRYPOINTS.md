# Executable path and exact remaining live-runtime uncertainties

All research entry points enforce the new capability before payload/inference/physics. Checked-in `EXECUTION-APPROVAL.json` is false. Future enabled approval and matching explicit authority record must bind `PACKAGE-MANIFEST.json`, `BINDINGS.json`, `COHORT.json` and `DTV-EFF1-P2-320-per-task`; they are separate files outside the immutable package. Do not overwrite the false template.

On the future staged POSIX package, with configured environment and approved capability:

```text
python -m dtv_success_cost.campaign                         # dry plan only
python -m dtv_success_cost.campaign --submit --approval <new-authority-bound-approval>
python -m dtv_success_cost.worker --job preflight --output <exclusive-run/preflight> --approval <approval>
python -m dtv_success_cost.worker --job <source-block-id> --output <exclusive-run/id> --approval <approval>
python -m dtv_success_cost.worker --job analysis --run <run> --output <exclusive-run/analysis> --approval <approval>
python -m dtv_success_cost.accept --run <run> --approval <approval>
python -m dtv_success_cost.preserve archive --approval <approval>
python -m dtv_success_cost.preserve backup --request <exact-remote-POSIX-BACKUP-REQUEST.json> --approval <local-authority-bound-approval>
python -m dtv_success_cost.preserve report --approval <approval> # refuses before actual SSD ACK
```

The dispatcher owns the worker invocations, order and unique allocation IDs; these individual examples are **not** permission to submit extra duplicate jobs. Supervisor deadlines start before child startup; journals/failed output remain. Dry planning never starts a scheduler command. Prometheus account `superworld`, GPU `a6000/normal-a6000/gpu09`, CPU `defq/normal` are the existing approved routes. Do not change bastion/key configuration or repair WSL/dependencies.

Control corrections inherited from accepted implementations include integer-minute reservations, bounded initial sacct visibility, exact allocation/name/terminal accounting, an eight-poll grace restricted to the exact GPU pending placeholder, persistent raw trigger evidence and charges before terminal-fault rejection. Exclusive namespaces reject reentry, including success/live/ambiguous work. No automatic recovery loop exists. Independent acceptance requires the complete exact grid and raw terminal records; unknown STOPs cannot be ignored.

After complete compute and actual whole/member SSD preservation, read the sealed CPU report and publish complete results, source effects, fixed blocks, costs and limitations. There is no automatic following stage or model promotion.

## Uncertainties deliberately not tested with research payloads

Artificial tests validate the scientific callable wiring, policy cadence/decoder, prospective native reset options, endpoint reconstruction, orchestration, accounting and preservation. They cannot establish actual GPU runtime throughput, HDF5 hash wall time, target-frame dtype/dimensions for every proposed source, physical initialization tolerance/contact behavior at every new source, EGL rendering availability, or performance under current site queue/I/O load. These are included-tranche technical checks inside the authorized future grid, not permission for a separate research pilot now.

No real model deserialization, Le-WM inference, simulator instantiation, training, evaluation payload access, Slurm job, dependency change or automation occurs in preparation. CPU artificial tests run in the existing WSL Python3.10/Torch2.13 CPU environment, not a claimed reproduction of CUDA 2.5.1 execution. World/scorer byte identities and native source text are authenticated; exact real interfaces remain fail-closed at launch. Any cohort conflict or exhausted preparation envelope is a blocker rather than authority to choose other IDs/settings.
