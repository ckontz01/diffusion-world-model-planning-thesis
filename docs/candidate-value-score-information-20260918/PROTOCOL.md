# SI1 — access to saved lookahead information

Status: executable preparation only; no training or launch authorized. Historical baseline: continuation. CVL-BP1 at `05973d5932e21c13b86cd95307dc055bba646255`, all prior decisions and artifacts remain unchanged. This is not a novel-method claim or a correction of an implementation fault.

## 1. Question and authenticated inputs

Does adding the already available immediate and continuation costs improve source-held-out candidate selection? The original omission was intentional. The original 619 fields are current/goal/first-terminal latents (192 each), current physical state (7), 15 actions (30), and clock (6). Neither cost was included.

`LINEAGE.json` pins 384 accepted training roots, their seals, reports and bank hashes. A metadata/header-only probe verified 1,426 available banks with `x: (64,619)` and both score arrays `(64,)`, float32. It did not run a model, decode numerical feature/cost arrays, or inspect protected payloads. Original training registry and the accepted BP1 terminal preservation record authenticate the roots. The certificate SHA-256 is `633be15376a195ee35ef33b72694638b20967ecb82be2658f1eb0367c9aee8c5`.

The authenticated hook saves immediate squared LeWM first-terminal-to-goal distance. Where the local schedule supports a second rollout, continuation is the mean of the two lowest goal costs among eight predicted continuations; otherwise it equals immediate. These are inference-available predictions, not actual future states or success labels. The accepted reader negates costs for ranking; SI1 reverses that sign to use the original saved costs as numeric inputs. No recomputation or resimulation is performed. The lineage certificate also identifies the authenticated hook, feature and reader source bytes.

## 2. Data and fixed folds

Use only the 192 B-training sources: original 96 plus BP1 breadth 96. Use their original two binary tail outcomes, never the precision extension. Whole sources remain together across horizons, anchors, candidates and draws. There are 1,536 possible source/horizon/anchor slots, 1,426 available, 110 unavailable; 11,408 sampled candidate-index rows and 22,816 binary outcome records. These are not 22,816 independent sources or necessarily unique action chunks. Preserve unavailable anchors and deterministic-tail repetitions as recorded.

Sort references by SHA-256 of UTF-8 `candidate-value-score-information-20260918|fold|<decimal reference>`, breaking any digest tie by reference. Divide into four consecutive groups of 48; `FOLDS.json` fixes the IDs and grid. For each fold fit on the other 144 and evaluate the 48 held out. All 192 receive exactly one out-of-fold prediction. No BP1 evaluation-set comparison or optional full-data fits: exactly 24 fits. Reserved closed-loop sources and 1600–5999 remain unopened.

## 3. Fixed paired models and preprocessing

Control: 619 standardized original fields plus two exactly zero inputs. Treatment: the same 619 plus standardized saved immediate and continuation costs. Both networks are 621→128→64→1, ReLU, 87,937 parameters. Three seeds 8201/8202/8203 define each fixed ensemble; average their sigmoid probabilities, never select a seed.

Refit weighted mean/standard deviation for all 621 fields on fitting references only. Reusing the old 96-source scaler would leak some held-out sources. Use the accepted normalization routine: population weighted variance; standard deviation below 1e-6 becomes 1. Control score inputs are zeroed AFTER normalization. The original 619 transformed fields are identical between conditions. This control is not a bit-identical replay of a historical model: fold-specific fitting and two zero-input weights are deliberate, shared comparison choices.

Within each fold and seed, both conditions start from identical weights and use identical shuffled minibatch order. BCE on both binary draws separately, original equal-reference/equal-horizon/equal-available-anchor/equal-candidate/equal-draw weights. AdamW lr 0.0003, weight decay 0.0001, batch 256 (retain short last batch), gradient clipping 1, exactly 1,800 updates per fit. Total 43,200 optimizer updates. No early stopping, checkpoint choice, thresholds, mixture search, feature search or calibration fit. No IDs or candidate indices enter the model; they only support grouping and deterministic ties.

## 4. Selection and analysis

Select on the existing eight-index sampled subset, which includes continuation. For learned-score ties retain continuation if tied, otherwise lowest original candidate index, using the unchanged accepted tie implementation. Fixed immediate/continuation controls use their original lowest-index cost rules. Complete both three-model ensembles for a fold before evaluating it. Individual seed probabilities are retained only for transparency; ensemble selection is the endpoint.

Primary descriptive quantities: each condition's selected empirical native success minus continuation, and paired treatment-minus-control, using equal source, then horizon, then available-anchor weighting. Outcomes average the two saved draws, without majority rounding. Report all 192 source effects, all four folds, horizon/anchor strata, selected success, gained/lost outcomes and override frequency. Also report ties, concordance, Brier and log loss. Better probability error alone does not establish better selection. Bank-level records preserve the chosen original index and all fixed model probabilities.

Use the accepted objective-capacity metric/aggregation implementation, pinned SHA-256 `d54f2826a82af210d4148486f4a465e247f63ac7a8b8df54aa57cac839d166c5`. Reference bootstrap intervals are descriptive: overlapping fold training sets and historical development exposure prevent a claim of untouched confirmation. Report every source and condition, not favorable subsets. No new pass/fail advancement gate or automatic model promotion.

## 5. Execution boundary and artifacts

`score_information.py` implements authenticated saved-data reading, fitting, ensemble inference and reporting. `run_score_information.sh` is a CPU-only runtime wrapper, not a dispatcher. `package_score_information.py` builds a closed source package and a disabled approval template. No execution approval is generated by preparation. A later explicit approval must bind the source manifest, lineage and exact caps before the worker can read numerical data or create an optimizer.

One sequential CPU allocation, no GPU request and no Apptainer `--nv`. Outputs are exclusive-create in a new SI1 run directory. Preserve normalization, all 24 weights, fold freeze records, ensemble and seed predictions, bank/source summaries, fit/update accounting and checksums. No automatic retries or resumption after a partial fit. Charge failures against the same ceiling; stop and report a technical fault without altering the scientific comparison.

## 6. Interpretation

This tests whether access to two existing lookahead summaries helps this fixed BCE evaluator on source-held-out development banks. It does not isolate which of the two costs matters, establish a deployable closed-loop gain, demonstrate general superiority, measure true candidate values, or show that diffusion itself is responsible. Candidate-bank selection is not an exhaustive oracle. Continuation remains the working baseline regardless of whether loss improves. Any subsequent study requires a separate decision.
