# README history source audit — 7 September 2026

This is a documentation review, not a new experiment or an independent rerun of the historical results.

## Coverage

The earlier-experiments section now contains 61 entries. They cover the original hierarchical-planning pilots and M1/M2/M3 studies, the E0/E1 rescoring diagnostics, residual-diffusion v2/v3, E2–E19 and their named variants, the E19 diagnostic/reset follow-ups, study-design audits, and independent-data collection/evaluation. The count includes diagnostics and engineering checks; it is not a claim of 61 independent confirmatory experiments.

The inventory was checked against the tracked report/protocol filenames, the archived README, and the implementation-amendment log. Training/setup checks, invalid runs and abandoned plans are labelled separately from efficacy results. Individual scheduler retries and filesystem/backup repairs are not presented as new scientific experiments.

## Evidence used

The result/protocol links are pinned to commit `f0cabb92d4b4214f3d423d9d19c77d3083d547da`, which predates this documentation edit. The old full README and `PROTOCOL-IMPLEMENTATION-AMENDMENTS-2026-08-08.md` retain the early chronology. `checks.json` records the paths and content hashes of the linked files.

The E16/E17 and E12–E15 transcripts supplied in the conversation were used as corroboration. The README links to the repository records so readers do not need access to that private conversation. Past instructions to stop a research branch are described as historical decisions, not permanent prohibitions on later separately documented studies.

## Important qualifications retained or corrected

- E0 is listed because the following protocol identifies its completed artifact and checksum. This edit did not read its raw result or find a standalone numerical E0 table in those linked reports. It therefore does not invent an E0 score or pass/fail verdict.
- E1 and the residual-diffusion v2 model are separate steps. E1 rescored existing predictions; v2 trained a changed model.
- E4's outcome is recorded in E5; E5/E6 outcome summaries are supported by the archived chronology and later protocol context. Their specification files alone are not presented as proof of their outcomes.
- E9 has no valid independent efficacy result. E12's failed Reacher components prevented its planned matched closed-loop stage, but its earlier native PRISM sanity evaluation did run.
- E14 VAD and coupled subgoal/action diffusion are both listed. E17's Cube adapter failure remains a failure even though E18 later tested the unchanged adapter in a separately specified development study.
- E19's initial invalid diagnostic is distinguished from the valid D2 reanalysis and L1's later localization. Hash differences and encoding sensitivity are not called proven causes of the SAGE paper discrepancy.
- The earlier PushT reset audit's limited no-label-flip finding is not used to dismiss the later R1/R2 restoration counterexamples.
- The continuation description now states its immediate-cost fallback at the last local stage of a planning cycle, as implemented in `gdp_cem_e18_closed_loop.py`.
- ACID and PRISM-DP comparison arms remain labelled reconstructions. E12's separate official PRISM artifact check is explicitly distinguished.
- E11's diffusion–Gaussian difference is not conflated with its larger ACID comparison. E13 retains the uncertainty around PRISM-DP and the separate Gaussian-boundary failure.
- E18 remains exploratory. The independent PushT study retains its lower success than SAGE, internal-control gains, registered stopping decision and solver-only timing scope.
- E20, D5 confirmation and PLDM transfer are not invented as completed experiments. The independent benchmark keeps its own name.

## Checks

`verify.mjs` checks reference definitions, existence of pinned Git files, the linked historical heading, a source link on every history row, and coverage of the named study labels. It also compares all 18 percentages in the latest result table with the archived summary, checks the three primary differences and solver-time ratio, and checks a few specific wording corrections.

Run from a checkout containing the pinned source commit:

```bash
node docs/readme-audit-2026-09-07/verify.mjs .
git diff --check
```

The verifier writes `checks.json`; it does not access the cluster, inspect additional dataset outcomes or execute a planner. Source hashes refer to committed UTF-8 text. The README hash normalizes CRLF to LF, so it can be checked from either Windows or Linux.

Link checks and numerical consistency checks do not prove that every sentence is correct. The prose review relied on the reports' stated methods, scope, results and later qualifications; it did not reconstruct every historical raw array or certify undocumented experiments. Future corrections should preserve the original reports and explain the narrower or corrected interpretation.

Only the README and this documentation-audit directory are changed. No experimental source, model, dataset, historical result, analysis decision or E12 draft is edited.
