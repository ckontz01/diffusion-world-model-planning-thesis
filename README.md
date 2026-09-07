# Diffusion proposals for world-model planning

**Christoforos Kontzias · University of Cyprus**

Thesis code and experiment records. Updated 7 September 2026.

This project asks whether diffusion can generate useful action sequences for a learned world model, and whether looking beyond the first sequence helps the planner choose better actions. The world model, Le-WM, stays fixed; the learned action proposer is the part being studied.

The latest PushT experiment is complete. **Continuation-aware diffusion improved on greedy diffusion and Gaussian continuation, but SAGE achieved higher success.** Diffusion used less time per solver call. The results below include both sides of that comparison.

The latest experiment code is on [`independent-pusht-benchmark`][code]. Result and source links point to recorded versions so they work from `main` as well.

## How the planner works

The short-horizon method generates 300 complete, 25-action sequences from noise, conditioned on Le-WM's representations of the current observation and goal. Le-WM predicts where each sequence leads, and the planner chooses the one with the lowest predicted goal cost. There is one candidate-selection stage, not an iterative cross-entropy method (CEM) search. The world model still has to roll out each sequence.

The longer-horizon version adds a second action sequence before making that choice. It generates 64 possible first chunks, each 15 actions long, and predicts the state after each one. A learned state adapter supplies the ordinary state-vector inputs needed to generate eight continuations from each predicted state. The planner scores each first chunk by the mean cost of its two best continuations, executes the selected first chunk, and replans.

The code calls the proposer **VAD**, for variable-duration action diffusion. This continuation planner was first tested in **E18 (the exploratory continuation study)**. It uses diffusion to propose actions, not to add a feasibility penalty to CEM. The [planner implementation][planner] and [E18 protocol][e18-protocol] give the details.

## Latest results: independent PushT evaluation

The study compared six methods on **1,600 independent reference trajectories**, with two goal offsets and three seed blocks: **57,600 individual evaluation runs**. Results were analyzed with repeated horizons and seeds grouped within each reference episode, rather than counted as independent samples.

**H75 and H150** mean that the goal comes from the reference state after 75 or 150 actions. They do not mean that reaching the goal necessarily requires that many actions. Each evaluated planner had a budget of at most twice that offset.

| Method | H75 success | H150 success | Overall success |
|---|---:|---:|---:|
| VAD continuation | 21.19% | 11.42% | 16.30% |
| Greedy VAD-300 | 20.54% | 7.65% | 14.09% |
| Gaussian continuation | 17.44% | 9.29% | 13.36% |
| Greedy VAD-576 | 21.44% | 8.81% | 15.12% |
| GMM continuation | 19.38% | 11.23% | 15.30% |
| Released full SAGE | 26.48% | 15.60% | 21.04% |

The greedy controls rank 300 or 576 first chunks without looking at a second chunk. The Gaussian and Gaussian mixture model (GMM) controls use the continuation structure with different learned proposal distributions. Overall success gives equal weight to both horizons and the three seed blocks.

VAD continuation improved on greedy VAD-300 by **2.21 percentage points** and Gaussian continuation by **2.94 points**. Both comparisons passed their prespecified superiority tests. It trailed SAGE by **4.74 points**. That comparison crossed the predeclared adverse-signal stopping boundary, so the study ended at its first planned analysis rather than continuing to 3,200 or 6,000 episodes. There were no recorded planner failures.

The median timed solver call was **129.7 ms for VAD continuation** and **963.9 ms for SAGE**, a ratio of about **7.43**. This is solver time, not full end-to-end latency. It is a speed–success trade-off, not evidence that diffusion matches SAGE's success rate.

The evaluation data are new trajectories from a fixed block-near random controller, with future states used as reachable goals. All 6,000 collected references passed validation, including 12,000 goal-specific action replays; only the first 1,600 entered the comparison. This is a different population from the earlier expert-data evaluations, so their absolute success rates should not be compared directly.

Read the [full result][latest], [protocol][protocol], or [data card][data-card]. The [result archive][results] contains the exact summary, all 57,600 outcome rows, the episode tensor, checksums, and independent verification. The first-look bounds use the registered allowance for repeated analyses and three primary comparisons; they are not ordinary post-hoc 95% intervals.

## Earlier experiments

Experiment labels such as E11 and E18 identify studies, not software releases. The earlier evaluations used different task populations and, in some cases, a different initialization interface.

### E11 — short-horizon diffusion proposals

On held-out starts from PushT, Reacher, and Cube, velocity diffusion reached **93.39%** equal-task success, compared with **90.64%** for a matched Gaussian proposer and **83.31%** for the ACID reconstruction.

The diffusion–Gaussian difference was **+2.75 percentage points**, with a 95% paired start-cluster interval of **[+1.64, +3.89]**. PushT and Reacher supplied most of that separation; both methods were near-perfect on Cube. The larger gap against reconstructed ACID also includes the benefit of learned proposals over iterative search, so it should not all be attributed to diffusion. [E11 results][e11].

### E13 — comparison with the PRISM-DP reconstruction

At 300 candidates, diffusion reached **93.53%** and the disclosed PRISM-DP reconstruction reached **92.97%**. The difference was **+0.56 points**, with a 95% interval of **[−0.47, +1.58]**: no demonstrated superiority. Diffusion met the prespecified three-point margin and used less time and memory, with fewer learned parameters in the measured comparisons.
The task effects were mixed: diffusion was lower on PushT, higher on Reacher, and tied on Cube. A separate Gaussian-control comparison also failed its proposal-boundary check on Reacher, so E13 is not a clean repeat of E11's diffusion-specific result. [E13 results][e13].

### E18 — the continuation pilot

This smaller development study used 12 starts per task on PushT and Cube. VAD continuation reached **72.92%**, compared with **66.67%** for greedy VAD-300. The intervals against greedy VAD-300 and Gaussian continuation still included zero, and Cube was close to saturated. It motivated the larger independent study above; it was not itself confirmation. [E18 results][e18].

## Baselines and evaluation details

**ACID and PRISM-DP are reconstructions in this repository.** Their numbers should not be presented as results from the authors' official implementations. The experiment reports document the implementation choices and remaining fidelity limitations.

**The latest SAGE comparison uses the released code and checkpoints under a common evaluation protocol.** It is separate from **E19 (the SAGE paper-reproduction study)**. E19 did not reproduce the complete released table within its tolerance, and its paper manifests overlapped the diffusion models' training episodes. The [E19 report][e19] records that outcome; the new benchmark does not resolve the historical reproduction discrepancy.

The latest comparison preserves SAGE's native handling of finite actions outside its declared action bounds. Those excursions are counted in the result archive; SAGE was not silently clipped or treated as failed for producing them. SAGE uses one released trained model with three evaluation-seed blocks, while the diffusion methods use their three fixed training checkpoints. The results do not establish how either method would behave across arbitrary retraining runs.

During the reproduction work, a PushT state setter was found to advance physics after assigning the requested state, sometimes carrying reset-dependent contact corrections into the starting pose. **R3 (the fresh-state initializer)** removes that hidden initialization step by constructing fresh physics before assigning the start. Missing block dynamics use documented defaults, not a claim of recovering the full historical simulator state. The independent study uses this [initialization interface][initializer]; earlier results retain their original setup.

## Finding the code

Most scripts live in `cluster/prometheus/`. The directory grew around individual experiments and still uses their original filenames so recorded commands and source hashes remain meaningful.

| What to inspect | Entry point |
|---|---|
| Continuation planning and action selection | [`gdp_cem_e18_closed_loop.py`][planner] |
| Independent reference-trajectory collection | [`independent_pusht_collect.py`][collector] |
| Checkpoint loading and model-specific interfaces | [`independent_pusht_runtime.py`][runtime] |
| Common six-method evaluation | [`independent_pusht_evaluate.py`][evaluator] |
| Statistics and result checks | [`analyze_independent_pusht.py`][analyzer] and [`verify_independent_pusht_analysis.py`][verifier] |

## Running and checking the experiments

This is a research repository, not a packaged library. To get the latest experiment code:

```bash
git clone --branch independent-pusht-benchmark https://github.com/ckontz01/diffusion-world-model-planning-thesis.git
cd diffusion-world-model-planning-thesis
```

The full evaluations use pinned Python environments and Apptainer containers on the CYENS Prometheus cluster. The scripts contain cluster-specific paths; cloning the repository alone does not supply the checkpoints, dependencies, or datasets. The [run wrapper][runner], [checkpoint manifest][pins], and [execution notes][recovery] record the setup used for the latest study. The older [workstation setup](REPRODUCIBILITY-SETUP.md) is retained as historical documentation.

Reading the results does not require cluster access. The compact outcome table and analysis files are committed in the [result archive][results]. Large reference and evaluation trajectories, model weights, latent caches, and container images are kept outside Git; their locations and hashes are recorded in the experiment documents. The latest results have a verified Windows recovery copy. Recovery of the older WSL bulk backups is a separate, unfinished operational task, not a missing analysis result.

## Research history

The project started with a different idea: use diffusion denoising error to judge whether imagined transitions were feasible. Those scores did not give reliable planning gains, which led to action proposal generation instead. Later studies tested action bounds, goal conditioning, continuation scoring, and simulator initialization. Several approaches failed their planned checks; those reports remain part of the repository.

The [archived research log][history] preserves the detailed chronology and earlier instructions. It is a historical snapshot, not the current project status. The latest result is the completed PushT study above: positive gains over the two main internal controls, lower solver time than SAGE, and lower success than SAGE on this evaluation population.

[code]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/tree/independent-pusht-benchmark
[latest]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PUSHT-RESULT-2026-09-07.md
[protocol]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PUSHT-PROTOCOL.md
[data-card]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PUSHT-DATA-CARD.md
[results]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/tree/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/independent-pusht-evidence/look-0
[e11]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-RESULT-2026-08-18.md
[e13]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-RESULT-2026-08-22.md
[e18]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-RESULT-2026-08-28.md
[e18-protocol]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-PROTOCOL-2026-08-27.md
[e19]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-NATIVE-REPRODUCTION-RESULT-2026-08-29.md
[initializer]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/PUSHT-FRESH-INITIALIZATION-INTERFACE.md
[planner]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/gdp_cem_e18_closed_loop.py
[collector]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/independent_pusht_collect.py
[runtime]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/independent_pusht_runtime.py
[evaluator]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/independent_pusht_evaluate.py
[analyzer]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/analyze_independent_pusht.py
[verifier]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/verify_independent_pusht_analysis.py
[runner]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/run_independent_pusht.sh
[pins]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PINNED-INPUTS.json
[recovery]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/cluster/prometheus/INDEPENDENT-PUSHT-RECOVERY.md
[history]: https://github.com/ckontz01/diffusion-world-model-planning-thesis/blob/f0cabb92d4b4214f3d423d9d19c77d3083d547da/README.md#historical-development
