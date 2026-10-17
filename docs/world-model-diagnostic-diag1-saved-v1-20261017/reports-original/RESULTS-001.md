# WM-DIAG1-SAVED — complete outcome-informed saved-data discovery

The original completed study, estimates and intervals are unchanged. These are 64 physical source parents shared across backbones (32 per task), not 128 independent sources. Candidates and two recorded evaluation draws add no independent parents. Reacher motivated this follow-up; PushT is an exposed contrast. Both new corrections are privileged diagnostics, not deployable repairs.

## Fixed four-setting results

New columns show success; difference vs P0 [descriptive paired 95% interval]; parent gains/losses/ties. Seed 20261017, 10,000 task-paired resamples shared across backbones/corrections. No confirmatory, multiplicity-controlled or independent-training-seed claim.

| Setting | Original P0 | Original O0 | A: remove common error | B: remove candidate-specific error | A / B agreement with O0 |
|---|---:|---:|---|---|---:|
| pusht|dinowm_noprop | 76.562% | 73.438% | 78.125%; +1.562 pp [-4.688 pp, +9.375 pp]; 1/1/30 | 67.188%; -9.375 pp [-21.875 pp, +0.000 pp]; 1/4/27 | 15.625% / 34.375% |
| pusht|lewm | 50.000% | 59.375% | 51.562%; +1.562 pp [-10.938 pp, +14.062 pp]; 3/2/27 | 45.312%; -4.688 pp [-14.062 pp, +1.562 pp]; 1/3/28 | 12.500% / 15.625% |
| reacher|dinowm_noprop | 73.438% | 95.312% | 75.000%; +1.562 pp [-9.375 pp, +14.062 pp]; 4/5/23 | 90.625%; +17.188 pp [+4.688 pp, +31.250 pp]; 8/1/23 | 12.500% / 37.500% |
| reacher|lewm | 71.875% | 92.188% | 71.875%; +0.000 pp [-17.188 pp, +17.188 pp]; 6/6/20 | 78.125%; +6.250 pp [-3.125 pp, +17.188 pp]; 4/2/26 | 15.625% / 18.750% |

Original intervals below are copied verbatim, not re-estimated. Energies are descriptive latent units; no error-energy fraction is a fraction of task failures caused. Raw latent units must not be compared across backbones.

### pusht|dinowm_noprop

Original P0 interval: [0.609375, 0.90625]; O0 interval: [0.578125, 0.875]; O0−P0: -3.125 pp [-12.500 pp , +6.250 pp].
Changed original action choices: 26; changed mean outcomes: 3; changed choices with tied outcomes: 23.
Equal-parent mean coordinate MSE: 0.710988757; common energy / coordinate: 0.526421906; specific energy / coordinate: 0.184566852.
Raw mean L2 error energy: 53511.8578; common: 39620.6183; specific: 13891.2395. Mean nonzero-parent common-energy fraction: 0.7440337535071806 (not failure attribution).
Selected-pair mean saved relative ordering error: 0.191471027; signed goal-direction difference: 0.143051655; squared-error difference: 0.0484193757.
Post-stop absorbed oracle terminal candidates: 174/512; selected P0/O0 absorbed parents: 15/15.

| Selection | Prefix-success draws | Tail-success draws | Failure draws |
|---|---:|---:|---:|
| A | 42 | 8 | 14 |
| B | 40 | 3 | 21 |
| O0 | 44 | 3 | 17 |
| P0 | 32 | 17 | 15 |
| native | 36 | 7 | 21 |

Recorded success differences vs P0, split into disjoint outcome categories (not a causal partition):

- A: prefix +15.625 pp; tail -14.062 pp.
- B: prefix +12.500 pp; tail -21.875 pp.
- O0: prefix +18.750 pp; tail -21.875 pp.

P0→O0 draw-phase transitions: `{"failure -> failure": 13, "failure -> prefix_success": 2, "prefix_success -> failure": 4, "prefix_success -> prefix_success": 28, "tail_success -> prefix_success": 14, "tail_success -> tail_success": 3}`.

Original gain/loss/tie strata (all parents retained):

| Stratum | Parents | Mean common energy | Mean specific energy | Mean goal-direction pair term | Mean squared-error pair term |
|---|---:|---:|---:|---:|---:|
| gain | 1 | 17701.147867832475 | 11774.3346304063 | -0.2326768329436835 | 1.337870935852635 |
| loss | 2 | 52413.343925941124 | 26262.594966261116 | 0.6961898325651172 | -0.1742530387514844 |
| tie | 29 | 39494.20518623101 | 13111.039319066427 | 0.11786034908468854 | 0.01931224699293562 |

### pusht|lewm

Original P0 interval: [0.328125, 0.671875]; O0 interval: [0.4375, 0.75]; O0−P0: +9.375 pp [-3.125 pp , +23.438 pp].
Changed original action choices: 31; changed mean outcomes: 8; changed choices with tied outcomes: 23.
Equal-parent mean coordinate MSE: 0.169964366; common energy / coordinate: 0.102063702; specific energy / coordinate: 0.067900664.
Raw mean L2 error energy: 32.6331583; common: 19.5962308; specific: 13.0369275. Mean nonzero-parent common-energy fraction: 0.6051273018852747 (not failure attribution).
Selected-pair mean saved relative ordering error: 21.6782217; signed goal-direction difference: 30.2465284; squared-error difference: -8.56830695.
Post-stop absorbed oracle terminal candidates: 119/512; selected P0/O0 absorbed parents: 9/15.

| Selection | Prefix-success draws | Tail-success draws | Failure draws |
|---|---:|---:|---:|
| A | 22 | 11 | 31 |
| B | 22 | 7 | 35 |
| O0 | 34 | 4 | 26 |
| P0 | 22 | 10 | 32 |
| native | 18 | 13 | 33 |

Recorded success differences vs P0, split into disjoint outcome categories (not a causal partition):

- A: prefix +0.000 pp; tail +1.562 pp.
- B: prefix +0.000 pp; tail -4.688 pp.
- O0: prefix +18.750 pp; tail -9.375 pp.

P0→O0 draw-phase transitions: `{"failure -> failure": 23, "failure -> prefix_success": 6, "failure -> tail_success": 3, "prefix_success -> prefix_success": 22, "tail_success -> failure": 3, "tail_success -> prefix_success": 6, "tail_success -> tail_success": 1}`.

Original gain/loss/tie strata (all parents retained):

| Stratum | Parents | Mean common energy | Mean specific energy | Mean goal-direction pair term | Mean squared-error pair term |
|---|---:|---:|---:|---:|---:|
| gain | 6 | 15.523884671594054 | 11.74111002723903 | 31.31171380130769 | -4.056663084981214 |
| loss | 2 | 9.813438297126076 | 13.430980700073459 | 2.4524392043541345 | 1.0970860752361817 |
| tie | 24 | 21.429550024679184 | 13.328044074492007 | 32.29640612626371 | -10.501667338052371 |

### reacher|dinowm_noprop

Original P0 interval: [0.609375, 0.859375]; O0 interval: [0.875, 1.0]; O0−P0: +21.875 pp [+10.938 pp , +34.375 pp].
Changed original action choices: 28; changed mean outcomes: 10; changed choices with tied outcomes: 18.
Equal-parent mean coordinate MSE: 0.573230374; common energy / coordinate: 0.389301208; specific energy / coordinate: 0.183929165.
Raw mean L2 error energy: 43143.6108; common: 29300.3661; specific: 13843.2447. Mean nonzero-parent common-energy fraction: 0.6876199070476723 (not failure attribution).
Selected-pair mean saved relative ordering error: 0.324076566; signed goal-direction difference: 0.257475274; squared-error difference: 0.0666013028.
Post-stop absorbed oracle terminal candidates: 116/512; selected P0/O0 absorbed parents: 11/19.

| Selection | Prefix-success draws | Tail-success draws | Failure draws |
|---|---:|---:|---:|
| A | 30 | 18 | 16 |
| B | 46 | 12 | 6 |
| O0 | 50 | 11 | 3 |
| P0 | 26 | 21 | 17 |
| native | 26 | 24 | 14 |

Recorded success differences vs P0, split into disjoint outcome categories (not a causal partition):

- A: prefix +6.250 pp; tail -4.688 pp.
- B: prefix +31.250 pp; tail -14.062 pp.
- O0: prefix +37.500 pp; tail -15.625 pp.

P0→O0 draw-phase transitions: `{"failure -> failure": 3, "failure -> prefix_success": 11, "failure -> tail_success": 3, "prefix_success -> prefix_success": 26, "tail_success -> prefix_success": 13, "tail_success -> tail_success": 8}`.

Original gain/loss/tie strata (all parents retained):

| Stratum | Parents | Mean common energy | Mean specific energy | Mean goal-direction pair term | Mean squared-error pair term |
|---|---:|---:|---:|---:|---:|
| gain | 10 | 29734.26126159325 | 15424.391463230908 | 0.2961782099417664 | 0.20913136565032103 |
| loss | 0 | None | None | None | None |
| tie | 22 | 29103.14108209986 | 13124.541626115197 | 0.23988303111634934 | 0.0018149105602152887 |

### reacher|lewm

Original P0 interval: [0.578125, 0.84375]; O0 interval: [0.828125, 1.0]; O0−P0: +20.312 pp [+7.812 pp , +34.375 pp].
Changed original action choices: 26; changed mean outcomes: 11; changed choices with tied outcomes: 15.
Equal-parent mean coordinate MSE: 0.323748685; common energy / coordinate: 0.174557993; specific energy / coordinate: 0.149190692.
Raw mean L2 error energy: 62.1597475; common: 33.5151347; specific: 28.6446129. Mean nonzero-parent common-energy fraction: 0.5463462585867598 (not failure attribution).
Selected-pair mean saved relative ordering error: 47.3032604; signed goal-direction difference: 39.9243386; squared-error difference: 7.37892238.
Post-stop absorbed oracle terminal candidates: 114/512; selected P0/O0 absorbed parents: 13/23.

| Selection | Prefix-success draws | Tail-success draws | Failure draws |
|---|---:|---:|---:|
| A | 30 | 16 | 18 |
| B | 30 | 20 | 14 |
| O0 | 54 | 5 | 5 |
| P0 | 26 | 20 | 18 |
| native | 18 | 27 | 19 |

Recorded success differences vs P0, split into disjoint outcome categories (not a causal partition):

- A: prefix +6.250 pp; tail -6.250 pp.
- B: prefix +6.250 pp; tail +0.000 pp.
- O0: prefix +43.750 pp; tail -23.438 pp.

P0→O0 draw-phase transitions: `{"failure -> failure": 4, "failure -> prefix_success": 12, "failure -> tail_success": 2, "prefix_success -> prefix_success": 26, "tail_success -> failure": 1, "tail_success -> prefix_success": 16, "tail_success -> tail_success": 3}`.

Original gain/loss/tie strata (all parents retained):

| Stratum | Parents | Mean common energy | Mean specific energy | Mean goal-direction pair term | Mean squared-error pair term |
|---|---:|---:|---:|---:|---:|
| gain | 10 | 43.156826144670426 | 28.228131817686922 | 81.9498441067013 | -17.721179532185232 |
| loss | 1 | 37.71729835632246 | 18.271785440101787 | 5.9175219029283355 | -1.9764851760129432 |
| tie | 21 | 28.723749968125194 | 29.336881345632356 | 21.531565379984045 | 19.776847467029285 |

## Every parent — unchanged choices, gains, losses and ties included

Costs/ranks below are authoritative saved S0 costs; ranks use exact cost then lowest index. P0 is not assumed to be the native return. Draw labels: prefix_success, tail_success or failure, with actual success/action clocks. Absorbed identifies the selected oracle terminal feature strictly after a recorded prefix stop. Every candidate, native feature/representation identity, prefix/branch flags, float64 terms and roundoff residual remains in DERIVED-RESULTS.json.

### pusht / lewm / source 0 (WM-DIAG0-A2-v1:pusht:root-000)

Original stratum: loss; action-choice changed: True; O0−P0: -50.000 pp. Source `ef3891216941f610eaa89ba077d55175e22f5a0af51d16cb764be92cad759ef3`; accepted output seal `02a967cc1f360554ddfb27826f16a33f5abf4adeb342f26730825960cc6bee20`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `4aeac1053a334c0fe92d60fbfaf92b5d32293a4fd6cc5349bf9869f563b8d108` | 19.0615616 / 1 | 17.6595154 / 5 | [0, 1] | failure @ None (elapsed 50); tail_success @ 29 (elapsed 29) | False |
| O0 | 2 / `a656563d711d95352484cd247ae1c9053530b445b7f262de9307037f22ea855d` | 19.1228104 / 2 | 15.2646971 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `aec7ea40e1b283fed40117da7e22a0d893cc00eb46455954126e24459de9eece` | 19.2448654 / 6 | 17.6618576 / 6 | [0, 1] | failure @ None (elapsed 50); tail_success @ 35 (elapsed 35) | False |
| A | 8 / `1bacafd0815acea117c1500b80fca753a1f45485ab68ed4ffebc539c67cf4b24` | 19.3480587 / 9 | 17.1035614 / 4 | [1, 1] | tail_success @ 30 (elapsed 30); tail_success @ 35 (elapsed 35) | False |
| B | 2 / `a656563d711d95352484cd247ae1c9053530b445b7f262de9307037f22ea855d` | 19.1228104 / 2 | 15.2646971 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 2.45606709 / 2.45606425; goal-direction term 2.03351848; squared-error term 0.422545774; algebra residual -3.55271368e-15; saved-minus-float64 2.83081617e-06.
Mean squared error energy 30.926734 = common 11.7095569 + specific 19.2171771; coordinate MSE 0.161076739; energy identity residual 3.55271368e-15.

### pusht / lewm / source 1 (WM-DIAG0-A2-v1:pusht:root-001)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `a1aa5c2785cf03951da9abe934acc38ef0cbec76f04e3540e3b4718be9663937`; accepted output seal `384dff6f50ebef509058c637c1d03e6166013724c514c4569484fd9478a4b108`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 0 / `1eaebdaaec183b3f9daa024ecc59f4b48ae6f691c4a60098ece9057496d819bd` | 4.43576097 / 1 | 6.63683748 / 5 | [1, 0] | tail_success @ 43 (elapsed 43); failure @ None (elapsed 50) | False |
| O0 | 12 / `66d25954bfa810ca16a0556857bf9ca867893fd2c8037423e5c172bfd74f6127` | 7.41967106 / 13 | 4.19765663 / 1 | [1, 0] | tail_success @ 27 (elapsed 27); failure @ None (elapsed 50) | False |
| native | 0 / `1eaebdaaec183b3f9daa024ecc59f4b48ae6f691c4a60098ece9057496d819bd` | 4.43576097 / 1 | 6.63683748 / 5 | [1, 0] | tail_success @ 43 (elapsed 43); failure @ None (elapsed 50) | False |
| A | 14 / `8a0bbe7f26ad95261c4f952c1347eedd0ddb10c32b874b3a18d5407decf4e58f` | 13.1194477 / 15 | 62.1784897 / 15 | [1, 0] | tail_success @ 28 (elapsed 28); failure @ None (elapsed 50) | False |
| B | 3 / `f454d68a480e3cf18b237650be09e41e2ab66002e20cfacca7704270f15bd15d` | 4.44740629 / 4 | 6.32541037 / 2 | [1, 1] | tail_success @ 47 (elapsed 47); tail_success @ 40 (elapsed 40) | False |

Selected-pair ordering error (saved / float64): 5.42309093 / 5.423091; goal-direction term 5.50688175; squared-error term -0.0837907479; algebra residual -1.77635684e-15; saved-minus-float64 -6.82427448e-08.
Mean squared error energy 15.0682181 = common 10.6867976 + specific 4.38142045; coordinate MSE 0.0784803024; energy identity residual 0.

### pusht / lewm / source 2 (WM-DIAG0-A2-v1:pusht:root-002)

Original stratum: gain; action-choice changed: True; O0−P0: +100.000 pp. Source `7e35579dbc3390fd438c61dd041066c96115209a86b5d9906b56ca2ea35d9128`; accepted output seal `7f6e4930620c8c112ed7bdceb593710670b9d756b7b3eb5aa4aaedb8fbc055a1`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `19a8df7eae372daa83a56d1f10728c8c6b3266eee20f7ef9dc562e92bdcbbcd4` | 7.13604164 / 1 | 45.5605354 / 12 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 5 / `d61b7f40a218f353cd8dd40d1e7926775b84baf4556779d86a9119cade785a0b` | 7.29171228 / 6 | 10.4969721 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `0471a00b79c5fddbcc2cea42f2a6d3dc6212ee88529209135b884e117a8de681` | 7.23583889 / 5 | 28.5940094 / 7 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 1 / `19a8df7eae372daa83a56d1f10728c8c6b3266eee20f7ef9dc562e92bdcbbcd4` | 7.13604164 / 1 | 45.5605354 / 12 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 7 / `f6f91c5fad0cbb33b956a373420855523bd61865464b7330ea98e5473e5372d2` | 7.31624222 / 8 | 28.4766426 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 35.219234 / 35.2192328; goal-direction term 68.3940509; squared-error term -33.1748182; algebra residual 0; saved-minus-float64 1.23049912e-06.
Mean squared error energy 37.0614331 = common 13.8202585 + specific 23.2411746; coordinate MSE 0.193028297; energy identity residual -7.10542736e-15.

### pusht / lewm / source 3 (WM-DIAG0-A2-v1:pusht:root-003)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `229830e3cb13dfdc839aeda26bbd1dfd6cd0dd72a63eaa159f6db8837c9f5102`; accepted output seal `ee274caf17ccdfb8bd48e210ed2d574e25d8220974f5c615cf33a1b9d6d888ac`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `79420201d24b893e6e55dbcd917f05dbe2983d31182b08129cf46412d93ceb11` | 7.71718454 / 1 | 3.60573649 / 10 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| O0 | 4 / `f9e17f484166b9776265becb95e721bedf1c2832b6a8e4081473d0b6b37f06d1` | 7.78270149 / 4 | 1.85182798 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `6fc5d1228399b8cbd442700900c83abf28874a93a45fa105fff451d43605a82b` | 7.79760075 / 6 | 3.21893573 / 6 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| A | 3 / `444d2c49aa6c44e73ca12203b2f34f8215bf3c601e1bf001f6e89b752ed0b50c` | 7.77010918 / 3 | 3.3992238 / 7 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| B | 0 / `6fc5d1228399b8cbd442700900c83abf28874a93a45fa105fff451d43605a82b` | 7.79760075 / 6 | 3.21893573 / 6 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 1.81942546 / 1.81942504; goal-direction term 4.6432532; squared-error term -2.82382816; algebra residual -1.77635684e-15; saved-minus-float64 4.19446156e-07.
Mean squared error energy 15.9416366 = common 11.1705068 + specific 4.77112986; coordinate MSE 0.0830293574; energy identity residual 0.

### pusht / lewm / source 4 (WM-DIAG0-A2-v1:pusht:root-004)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `b314e45de061671cb3d0d51db2fe77d75d7c6df80febfad28ee5153082f1d0bd`; accepted output seal `64269e16530265bab285c1151acd50b54ba28f76152ff3287e356ced1f1dcff8`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 0 / `44529acb5375fca35bace8cebd6d6baccdceaf253487b28f1ac6b6507f800aa5` | 15.7656631 / 1 | 135.793884 / 5 | [1, 1] | tail_success @ 28 (elapsed 28); tail_success @ 27 (elapsed 27) | False |
| O0 | 11 / `f18024d33517c7db10dd49fe1cc4e3cf9a5a6c2707ab1f4d351beca10fd90e00` | 39.2240601 / 12 | 27.97155 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| native | 0 / `44529acb5375fca35bace8cebd6d6baccdceaf253487b28f1ac6b6507f800aa5` | 15.7656631 / 1 | 135.793884 / 5 | [1, 1] | tail_success @ 28 (elapsed 28); tail_success @ 27 (elapsed 27) | False |
| A | 11 / `f18024d33517c7db10dd49fe1cc4e3cf9a5a6c2707ab1f4d351beca10fd90e00` | 39.2240601 / 12 | 27.97155 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| B | 7 / `2491109585919262c6696ef4f52d3c10202bcb260c4d334d15699fac0c8cc2a4` | 16.0251961 / 8 | 125.935165 / 3 | [1, 1] | tail_success @ 27 (elapsed 27); tail_success @ 28 (elapsed 28) | False |

Selected-pair ordering error (saved / float64): 131.280731 / 131.280746; goal-direction term 175.308621; squared-error term -44.0278753; algebra residual 0; saved-minus-float64 -1.47789383e-05.
Mean squared error energy 133.148523 = common 102.816068 + specific 30.3324553; coordinate MSE 0.693481891; energy identity residual 2.84217094e-14.

### pusht / lewm / source 5 (WM-DIAG0-A2-v1:pusht:root-005)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `cbad940d675663b7e3f12912d299c38a652c6387db3c33e910dc5a201167df3d`; accepted output seal `250e5bf56f1bc22f7bbde0e8d5763bf4650c98fa6ee61a8320339c30f50990bf`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `c25e061ff8887d7830ab551c07165281ff405bfdbf3b9b20d09d7d4efd707109` | 7.60116243 / 1 | 66.7888107 / 10 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 9 / `73fc2deddfaf381371fd971b514b857667f7724d358982295405d8adaff5ded8` | 7.94251585 / 10 | 33.7256775 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `ab049b768dd256a2fdd3f82bf6c0ead052e2ecf55152126e8652c785c31cec8a` | 7.60459185 / 2 | 57.693512 / 7 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 1 / `c25e061ff8887d7830ab551c07165281ff405bfdbf3b9b20d09d7d4efd707109` | 7.60116243 / 1 | 66.7888107 / 10 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 0 / `ab049b768dd256a2fdd3f82bf6c0ead052e2ecf55152126e8652c785c31cec8a` | 7.60459185 / 2 | 57.693512 / 7 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 33.4044867 / 33.404486; goal-direction term 70.0087788; squared-error term -36.6042928; algebra residual -1.42108547e-14; saved-minus-float64 6.18459325e-07.
Mean squared error energy 90.1183166 = common 64.3743954 + specific 25.7439212; coordinate MSE 0.469366232; energy identity residual -2.84217094e-14.

### pusht / lewm / source 6 (WM-DIAG0-A2-v1:pusht:root-006)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `90ea55d0948950ecf9b97ac4154b227acd6d597d27a9301719cfe6113c73445f`; accepted output seal `fe2581451fdcadf6719d5644a557adeaad696db73c0fae8355084943aeda5e23`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `251e5f0750aa4a148a30799c994a48079fe2cabc5669eafd55160a5d5a3378f9` | 5.21147442 / 1 | 4.8999939 / 2 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| O0 | 8 / `8d5daa99e2756619e61f014df3085d82580414b5d82815bf00fa3a0bb71011df` | 5.25284958 / 9 | 4.45893383 / 1 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| native | 0 / `11d70a909d4a47e7f2d7f60e990ae2e87968b4ac803e6174eccda2a8fecab2ef` | 5.22274733 / 3 | 5.64444494 / 3 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| A | 1 / `251e5f0750aa4a148a30799c994a48079fe2cabc5669eafd55160a5d5a3378f9` | 5.21147442 / 1 | 4.8999939 / 2 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| B | 1 / `251e5f0750aa4a148a30799c994a48079fe2cabc5669eafd55160a5d5a3378f9` | 5.21147442 / 1 | 4.8999939 / 2 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |

Selected-pair ordering error (saved / float64): 0.482435226 / 0.48243583; goal-direction term 2.52449179; squared-error term -2.04205596; algebra residual -8.8817842e-16; saved-minus-float64 -6.03288204e-07.
Mean squared error energy 9.79667824 = common 7.29108179 + specific 2.50559645; coordinate MSE 0.0510243658; energy identity residual -1.77635684e-15.

### pusht / lewm / source 7 (WM-DIAG0-A2-v1:pusht:root-007)

Original stratum: gain; action-choice changed: True; O0−P0: +100.000 pp. Source `97e8c042a40e170abbce6c74bc471899b45e867de703845b0a45b25d5db63f83`; accepted output seal `df8efef721fc5c84479df7bf28830dcc80a841dfe55e93bd4dc5295c59c2c0c0`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `efffe5b2834d01c4fcc5791b8c4f94daaa106a52abb579dafa3f81f28e23f554` | 14.1669159 / 1 | 24.9218998 / 12 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 2 / `7e9b688f22db08246cdb34e58b7c34934aee14810ce545687c99c6c10ee22069` | 14.1864214 / 3 | 10.0311308 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `287db5e32304f08610563167c88e76b526cc86a5ba079ae308e9e4db00000155` | 14.1783867 / 2 | 18.3929443 / 8 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 2 / `7e9b688f22db08246cdb34e58b7c34934aee14810ce545687c99c6c10ee22069` | 14.1864214 / 3 | 10.0311308 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| B | 3 / `690e7970d493cb82bb13c996819be9148b803c976551c9f1bdb30dd8fe4cd14b` | 14.2236366 / 4 | 17.4127655 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 14.9102745 / 14.9102738; goal-direction term 30.2786912; squared-error term -15.3684174; algebra residual 1.77635684e-15; saved-minus-float64 6.71170108e-07.
Mean squared error energy 31.506644 = common 20.5152642 + specific 10.9913798; coordinate MSE 0.164097104; energy identity residual 3.55271368e-15.

### pusht / lewm / source 8 (WM-DIAG0-A2-v1:pusht:root-008)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `28a0a990e504170b4fb1ce994a4da7efe22da784b0620b5bb59585467bbdb07d`; accepted output seal `35d1e850933a8775eb8a643cf509f86cc63e2cd7a647893be6b0d4c391333062`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `b7cab97b3e24ee08044b6a96082453b8e11ee0c3f3b8f2ab852379ec507038a1` | 3.22419143 / 1 | 1.67926979 / 8 | [1, 1] | prefix_success @ 17 (elapsed 17); prefix_success @ 17 (elapsed 17) | True |
| O0 | 5 / `5ffbed6c798e437f509680f6130fd7c5302810dcce66633a98f614db3d17be64` | 3.26282907 / 6 | 0.735109687 / 1 | [1, 1] | prefix_success @ 17 (elapsed 17); prefix_success @ 17 (elapsed 17) | True |
| native | 0 / `b6696683885454fede494e5b1335e77fd2587341b9d8686cc039a666a09dd263` | 3.24218893 / 2 | 1.47509134 / 6 | [1, 1] | prefix_success @ 17 (elapsed 17); prefix_success @ 17 (elapsed 17) | True |
| A | 10 / `5b9ed4bbb94c80d638be048e320c3184663b50dee65325eaba95680557fb37eb` | 4.42589283 / 11 | 6.55383301 / 12 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 4 / `f67700913dc5dfc7af2f6dd55ff6a98f3fd86454d19ccf75b018b42ceb506f5a` | 3.26235461 / 5 | 1.63002098 / 7 | [1, 1] | prefix_success @ 17 (elapsed 17); prefix_success @ 17 (elapsed 17) | True |

Selected-pair ordering error (saved / float64): 0.982797742 / 0.982797735; goal-direction term 1.855756; squared-error term -0.872958268; algebra residual 7.77156117e-16; saved-minus-float64 6.90190538e-09.
Mean squared error energy 9.9853326 = common 5.64571643 + specific 4.33961617; coordinate MSE 0.0520069406; energy identity residual 1.77635684e-15.

### pusht / lewm / source 9 (WM-DIAG0-A2-v1:pusht:root-009)

Original stratum: loss; action-choice changed: True; O0−P0: -100.000 pp. Source `ad7d433ba817e2f0d0c56c28a6978b88f55e4d81e3f59b1bf27aa768a22e2c64`; accepted output seal `4e9646e8621e9c0d2bfb2d15365e8288d261a47d286cfbd407156d7000bb4d30`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `39d3b71961b63095d587dd1d1d6df70e4b26c4b6b671e0174194359d1aaea645` | 3.58244419 / 1 | 2.13043356 / 7 | [1, 1] | tail_success @ 49 (elapsed 49); tail_success @ 49 (elapsed 49) | False |
| O0 | 11 / `339e51fc26f80ec7eaf6e545f45247323ca8ddc978d60fc368490bb007737842` | 7.40329647 / 12 | 1.30830061 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `e9929006553769051a256b6d94cd673d1a6daca729007c96fcc1e8fd174f85d1` | 3.59618831 / 2 | 38.7043457 / 14 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 9 / `f7df5c0b716e4fee6c55fff4135667bb2dbe0510e79366af89edde3619e78e41` | 4.73967648 / 10 | 1.55964899 / 3 | [1, 1] | tail_success @ 49 (elapsed 49); tail_success @ 49 (elapsed 49) | False |
| B | 2 / `2687ce4c32d0951d9e470d9d2d11a0a4e46ab3147c09950ad0a293b902946967` | 3.60234022 / 3 | 1.78265178 / 4 | [1, 0] | tail_success @ 49 (elapsed 49); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 4.64298522 / 4.6429863; goal-direction term 2.87135993; squared-error term 1.77162638; algebra residual 0; saved-minus-float64 -1.08000687e-06.
Mean squared error energy 15.562104 = common 7.91731967 + specific 7.64478435; coordinate MSE 0.0810526251; energy identity residual 0.

### pusht / lewm / source 10 (WM-DIAG0-A2-v1:pusht:root-010)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `404f609dee183630eb1946f0d5cc2d9383250c8bf9c98872d1694ec6387fa4a6`; accepted output seal `89ad4ffb30a717a66fb88a9ba6136cd6ca45cdfaba8d8b857af588b2ea6f83c7`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 0 / `ee3d9bfb39a75c01b6c9476b67dcece941bb8280da3f1e64db196403ea88807b` | 21.6317081 / 1 | 22.7134056 / 3 | [1, 1] | prefix_success @ 3 (elapsed 3); prefix_success @ 3 (elapsed 3) | True |
| O0 | 13 / `10cd7b8427dfc363cfc1ce95d765433d5a893eab32f6b6c0c9a2495fc4c293cc` | 54.1900253 / 14 | 14.3597918 / 1 | [1, 1] | prefix_success @ 5 (elapsed 5); prefix_success @ 5 (elapsed 5) | True |
| native | 0 / `ee3d9bfb39a75c01b6c9476b67dcece941bb8280da3f1e64db196403ea88807b` | 21.6317081 / 1 | 22.7134056 / 3 | [1, 1] | prefix_success @ 3 (elapsed 3); prefix_success @ 3 (elapsed 3) | True |
| A | 3 / `1899002e90d3858124c17ae0068040329ca861bd68346ffb6e60f526169eb972` | 21.7678661 / 4 | 26.1021461 / 10 | [1, 1] | prefix_success @ 3 (elapsed 3); prefix_success @ 3 (elapsed 3) | True |
| B | 5 / `87295d0d8e9c286247fae983b5c86ce8b657c21ef0913f3eef470cd8fd18a4c4` | 21.8034115 / 6 | 19.5298729 / 2 | [1, 1] | prefix_success @ 3 (elapsed 3); prefix_success @ 3 (elapsed 3) | True |

Selected-pair ordering error (saved / float64): 40.911931 / 40.9119309; goal-direction term 28.4605744; squared-error term 12.4513565; algebra residual 1.42108547e-14; saved-minus-float64 1.42255303e-07.
Mean squared error energy 39.4791434 = common 29.7866574 + specific 9.692486; coordinate MSE 0.205620539; energy identity residual 0.

### pusht / lewm / source 11 (WM-DIAG0-A2-v1:pusht:root-011)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `8c01b6e7a4d3950e23e5e93c6031138521743fabde6e8b02b234f801dff00d8b`; accepted output seal `fc57fb6d5a06e86d9762509220b0124153417bb23f7690711c589447758aaaca`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `48c9a45d7ee88f848a1452c40d644b1832d63c0fa07f640ca87f07be7c52f6ca` | 8.19909191 / 1 | 7.12580204 / 3 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| O0 | 11 / `290c45d54a7633824340c968288a812e1e4400a83e33bfd63a982954a7e74e30` | 21.5080833 / 12 | 3.00284457 / 1 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| native | 0 / `2a2f4f4abaa1c516a7bef73f5cd14b29b4ae717864eb5b2a782a658c5d60ef60` | 8.56023026 / 7 | 11.3844004 / 7 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| A | 4 / `7aec2442e0ec60da764b8a24c235e05f3d7aeccea57782a5cce12640ee695700` | 8.48564911 / 4 | 15.130147 / 9 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| B | 8 / `fd5ed322d2de5e6e3c2503c1165287430f79582d26171fd03de38cc8ac8c3eaf` | 8.61412811 / 9 | 15.2844715 / 10 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |

Selected-pair ordering error (saved / float64): 17.4319489 / 17.4319482; goal-direction term 10.5459214; squared-error term 6.88602679; algebra residual 7.10542736e-15; saved-minus-float64 6.78908691e-07.
Mean squared error energy 26.3991269 = common 17.517851 + specific 8.88127583; coordinate MSE 0.137495452; energy identity residual 3.55271368e-15.

### pusht / lewm / source 12 (WM-DIAG0-A2-v1:pusht:root-012)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `a2f3bb93a6c7ae3f70ee9d5218af1d52a9f13e08d71ad3bfa8cf2c6db7bcee9a`; accepted output seal `04850a89607c20d1a4a9fa9b5b9968ac57474d14a73f0baefe26dcf75aa23470`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `1b4b8b78034ed3bc00135ecddd68536a40a589a3d3bf81a61a2c88c9fa63e5ea` | 6.11216736 / 1 | 5.15775394 / 13 | [1, 1] | prefix_success @ 1 (elapsed 1); prefix_success @ 1 (elapsed 1) | True |
| O0 | 13 / `e6047250a2d832dc1986569384ac749225ace821ba7eb32512701d8d29cb03a2` | 15.9847279 / 14 | 3.33546925 / 1 | [1, 1] | prefix_success @ 1 (elapsed 1); prefix_success @ 1 (elapsed 1) | True |
| native | 0 / `029c0bbcb76698bacfbe5a2b96106cc230fbd9441f5ce067f71504d2b979bea4` | 6.12563515 / 3 | 4.20456314 / 6 | [1, 1] | prefix_success @ 1 (elapsed 1); prefix_success @ 1 (elapsed 1) | True |
| A | 1 / `1b4b8b78034ed3bc00135ecddd68536a40a589a3d3bf81a61a2c88c9fa63e5ea` | 6.11216736 / 1 | 5.15775394 / 13 | [1, 1] | prefix_success @ 1 (elapsed 1); prefix_success @ 1 (elapsed 1) | True |
| B | 2 / `74db54c8bcdecce1301028bf41ed3b5f6c3530f4cda1eec255f4f0851470b035` | 6.12059879 / 2 | 3.83484554 / 3 | [1, 1] | prefix_success @ 1 (elapsed 1); prefix_success @ 1 (elapsed 1) | True |

Selected-pair ordering error (saved / float64): 11.6948452 / 11.6948445; goal-direction term 9.76487793; squared-error term 1.92996653; algebra residual -1.77635684e-15; saved-minus-float64 7.43537765e-07.
Mean squared error energy 18.1412597 = common 7.20869915 + specific 10.9325606; coordinate MSE 0.0944857278; energy identity residual -3.55271368e-15.

### pusht / lewm / source 13 (WM-DIAG0-A2-v1:pusht:root-013)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `6335ad64ea4e26c68928527ce5601b2edb5a277538f8a5cc0873c35c80b881c9`; accepted output seal `7730fd497c26bf5f14ae94e9e832dca4ae24b298a1d07013f9506bd1c7e499b4`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 0 / `69059b1eb489ccac2a6ec2430a8cb4ebcf729a2a367b1083a8ed7b3ed0fe28bf` | 18.9548264 / 1 | 31.0964394 / 8 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| O0 | 5 / `877ab5f801f02f8416a606472434ae68130f2ab27187102796c95d31fde39be2` | 19.8145714 / 6 | 24.9423218 / 1 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| native | 0 / `69059b1eb489ccac2a6ec2430a8cb4ebcf729a2a367b1083a8ed7b3ed0fe28bf` | 18.9548264 / 1 | 31.0964394 / 8 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| A | 3 / `b2e25100295541f665518ecfba1d24ac9c850ae16b2e6660980e4737976a1e80` | 19.694458 / 4 | 27.4632988 / 4 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| B | 5 / `877ab5f801f02f8416a606472434ae68130f2ab27187102796c95d31fde39be2` | 19.8145714 / 6 | 24.9423218 / 1 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |

Selected-pair ordering error (saved / float64): 7.01386261 / 7.01386346; goal-direction term 11.5981368; squared-error term -4.58427337; algebra residual 3.55271368e-15; saved-minus-float64 -8.49790315e-07.
Mean squared error energy 39.9517958 = common 25.3429549 + specific 14.6088409; coordinate MSE 0.20808227; energy identity residual 0.

### pusht / lewm / source 14 (WM-DIAG0-A2-v1:pusht:root-014)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `9e10176e8b36301702365f9248c4cefd16e1798bbbed722b41a0f17507bed7d3`; accepted output seal `3ea17adba9a4a119900695786e6e3157529bf1f5be7f5ddacfe9febb5ffc5664`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 0 / `d002d9fbdbc111ad5d2e3b43bc8e98edbdba6089bd6ec8185b86cac31088b04a` | 6.67459869 / 1 | 8.65595245 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 6 / `bee25aaf1054eceb5fec10977d6f7771e25b57340e6d430a166462333437e8b4` | 6.77232838 / 7 | 5.50965452 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `d002d9fbdbc111ad5d2e3b43bc8e98edbdba6089bd6ec8185b86cac31088b04a` | 6.67459869 / 1 | 8.65595245 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 9 / `67c4db685657c843aac9879febacb0b0aa60d151215d949503ddab4143af7138` | 7.96192837 / 10 | 9.89062119 / 7 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 2 / `0b1d748c053ed3c2c1eb472b4ed68aedb45779de019f9facf319048a29f0d9eb` | 6.71916771 / 3 | 5.81545448 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 3.24402761 / 3.24402799; goal-direction term 5.84612213; squared-error term -2.60209414; algebra residual 0; saved-minus-float64 -3.74052306e-07.
Mean squared error energy 16.3325825 = common 7.2963421 + specific 9.03624037; coordinate MSE 0.0850655337; energy identity residual 3.55271368e-15.

### pusht / lewm / source 15 (WM-DIAG0-A2-v1:pusht:root-015)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `7f1f3d08887ecad26b3ff3517ce8c4656a8f23c92f0a9c87f5ef9073d0b98b9e`; accepted output seal `a68fa6b0d81fe86f8d7104f918b2ce3e39ec89bce23a42b7f2408f8330977b12`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 0 / `4649bd91e1f3be7b768c6e4155346aa074b0d02d38be4ed710f807f6c5a90e33` | 5.07925701 / 1 | 10.1761398 / 8 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 14 / `274ad396eae41e7cd4f0c6a46daba13578dd3486415ab51b5c8531e0ae596c1b` | 16.1393051 / 15 | 4.08993721 / 1 | [1, 0] | tail_success @ 32 (elapsed 32); failure @ None (elapsed 50) | False |
| native | 0 / `4649bd91e1f3be7b768c6e4155346aa074b0d02d38be4ed710f807f6c5a90e33` | 5.07925701 / 1 | 10.1761398 / 8 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 2 / `7eb80042a1b86c917832f28dc41021086669cb9e1554ae8997164f282a282661` | 5.09134722 / 3 | 13.3291349 / 12 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 5 / `882949dc1794b995f2c0bc31b43de03c3f0dbb45e63d60ca073fe69edcbef7b8` | 5.10612822 / 6 | 9.20541382 / 5 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 17.1462507 / 17.1462518; goal-direction term 14.986255; squared-error term 2.15999676; algebra residual 3.55271368e-15; saved-minus-float64 -1.03914397e-06.
Mean squared error energy 17.1129596 = common 7.35961891 + specific 9.75334067; coordinate MSE 0.0891299978; energy identity residual -3.55271368e-15.

### pusht / lewm / source 16 (WM-DIAG0-A2-v1:pusht:root-016)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `c74559aac8288c690c71cc0feabbefbce73454cb34fb1e2c2bd449c90a1eaf7b`; accepted output seal `5b2acd66a0398748266f5056909d3445be60a3b74b9252fd8bc18a2d63079d69`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `793eb56856979e610eb4a73bc055ac509f344cf8056ad09c45b0d3325e07c1ca` | 5.74150562 / 1 | 6.78227091 / 9 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| O0 | 3 / `92d06509021ed48182e921136e2c47364cfc48369756615de0b9d0c2624a94ad` | 5.79361677 / 4 | 2.24503851 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `4a9b67285dd5a640f39329f02ce81ea4f3159adda90210107402fa543c7f9fec` | 5.78354263 / 3 | 7.65574026 / 12 | [1, 1] | tail_success @ 46 (elapsed 46); tail_success @ 26 (elapsed 26) | False |
| A | 6 / `0677defdd3502a873875449ddf85db5ece06247df0dcbefa99512b656a6ae798` | 5.8104701 / 7 | 8.49993896 / 13 | [1, 1] | tail_success @ 45 (elapsed 45); tail_success @ 45 (elapsed 45) | False |
| B | 3 / `92d06509021ed48182e921136e2c47364cfc48369756615de0b9d0c2624a94ad` | 5.79361677 / 4 | 2.24503851 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 4.58934355 / 4.58934342; goal-direction term 7.71079528; squared-error term -3.12145185; algebra residual 0; saved-minus-float64 1.25328701e-07.
Mean squared error energy 12.3498894 = common 7.89768902 + specific 4.45220037; coordinate MSE 0.0643223406; energy identity residual 0.

### pusht / lewm / source 17 (WM-DIAG0-A2-v1:pusht:root-017)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `0bfbbb08785c3c1d9e9a856935f1f30f1416a7e9cfbe9de60ad39b4fbbaedea6`; accepted output seal `545a66cbfd883809a5d619b746aaf917f103245484ad4708507aabb44ae1fa69`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `a9ca2a9984e60a0f0ac361ad4de739dbcc48987f9181cf3054360cacfd5c125b` | 22.9320278 / 1 | 16.4112682 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 4 / `39cde36ae1fff2857a6ef5a0494de070a03045509d9371c501161763b2731845` | 23.7653961 / 5 | 14.9953566 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `48f03c731a82e5eb77f9b5e7159ffa301fc3fc4cbcef54f06a6c586780307284` | 23.6570396 / 4 | 18.8551311 / 8 | [0, 1] | failure @ None (elapsed 50); tail_success @ 49 (elapsed 49) | False |
| A | 4 / `39cde36ae1fff2857a6ef5a0494de070a03045509d9371c501161763b2731845` | 23.7653961 / 5 | 14.9953566 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 8 / `16ffc01e789d1ac9b7c42a91bc09522972fe77d6407e4b036553d9e1337c2ec7` | 24.1851101 / 9 | 15.7341423 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 2.24927998 / 2.24927979; goal-direction term -1.72523187; squared-error term 3.97451166; algebra residual 0; saved-minus-float64 1.86650318e-07.
Mean squared error energy 29.254408 = common 12.7277161 + specific 16.5266919; coordinate MSE 0.152366708; energy identity residual 7.10542736e-15.

### pusht / lewm / source 18 (WM-DIAG0-A2-v1:pusht:root-018)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `54699d2425e452df185760d0d8a5cc327cecb229b645db709b40adecd149eb95`; accepted output seal `44355c9f04863cb6ead15a2142e31370e887ad28f5175401a35c6337dc12ecb9`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `fc6efe49107f0172eaaab95356a4884f9d2e26574ad88243bf608a79f10335fb` | 5.33943176 / 1 | 2.82166839 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 8 / `b22abe7f7378d3d876a9364719b544811f9ce791b8507eefd99f1c35a6dd9876` | 5.3946681 / 9 | 2.51071525 / 1 | [1, 0] | tail_success @ 50 (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `5b879e48aa5272c3c90abb91ce09faece13973e6d7e7e0bade06088bf1e0a745` | 5.35800648 / 4 | 3.42766857 / 9 | [1, 1] | tail_success @ 50 (elapsed 50); tail_success @ 44 (elapsed 44) | False |
| A | 1 / `fc6efe49107f0172eaaab95356a4884f9d2e26574ad88243bf608a79f10335fb` | 5.33943176 / 1 | 2.82166839 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 6 / `fb2ca12c139765edecac80d1bf0cc534defe47e7d5ae4836eb90867b941de563` | 5.38459492 / 7 | 3.72652721 / 11 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0.36618948 / 0.366189773; goal-direction term 1.18225232; squared-error term -0.816062544; algebra residual 0; saved-minus-float64 -2.9364901e-07.
Mean squared error energy 9.84483562 = common 8.23405051 + specific 1.61078512; coordinate MSE 0.0512751855; energy identity residual 0.

### pusht / lewm / source 19 (WM-DIAG0-A2-v1:pusht:root-019)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `59c08c0dedb62cb6a09ee3715024ada0c70b6cf07411c82196911b84a196cbb2`; accepted output seal `b4ef61903c6b6795a5343d7060ff3b7658f4187ee9a921d5c492275b1863fb40`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `015818bed3bbdabdb14fcd87c88480af5786cbdfad7357657e01d8467fa6d25e` | 7.44569874 / 1 | 116.754822 / 9 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 11 / `1bd6b571aa80786a73c1d15c152308ba1abcbc8c6e076de33d16e2b6d6516f4c` | 11.9759369 / 12 | 3.30389977 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `14f44a73a736d70608862f9f8eed5136867fdb32e74bcc94f4dabd4566c51dcd` | 7.45472383 / 2 | 131.212677 / 11 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 4 / `27c7f4ef7a1fc0a7e3acd541f02f3208e09882cd88799cd3c9cd791ada1efa2e` | 7.50125122 / 5 | 145.323227 / 14 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 8 / `ac21b37b0abc8d999191e01add078bad7f0645d6b783adab96c20a0f781efe7c` | 7.52729177 / 9 | 38.598568 / 5 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 117.98116 / 117.981149; goal-direction term 231.431465; squared-error term -113.450316; algebra residual -4.26325641e-14; saved-minus-float64 1.10728882e-05.
Mean squared error energy 96.5366816 = common 34.2668905 + specific 62.2697912; coordinate MSE 0.502795217; energy identity residual -1.42108547e-14.

### pusht / lewm / source 20 (WM-DIAG0-A2-v1:pusht:root-020)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `f618a4af897922a7196836e5e9064c57c95302b658cdd9e2f6e239b0cb91b4a7`; accepted output seal `7205700dd8d41ea28f98a07f5a3706ab075fd1c8aeac92ecf0b87a585c1ea747`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 0 / `64a461175a109770d6e31db825c1343bccae45c66e79fe3b48c07626bc33f1be` | 14.2409325 / 1 | 3.71372151 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 4 / `7c200e38e9574c8ce4c90a5774841af34d9f7517232ca71c19edf5501d08784e` | 14.253582 / 5 | 2.55008864 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `64a461175a109770d6e31db825c1343bccae45c66e79fe3b48c07626bc33f1be` | 14.2409325 / 1 | 3.71372151 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 9 / `f8403776d149971914807b445332903af425a1ccd91e7831fea0a596203325b2` | 14.7575588 / 10 | 2.85057068 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 8 / `ebafb216c7eda298686fccccf5ef6bb3468f4069f5880c0a598490dc3cd5f499` | 14.2870369 / 9 | 4.99909449 / 12 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 1.17628241 / 1.1762815; goal-direction term 2.50948407; squared-error term -1.33320257; algebra residual -4.4408921e-16; saved-minus-float64 9.0525701e-07.
Mean squared error energy 17.8626836 = common 15.2614834 + specific 2.60120017; coordinate MSE 0.0930348103; energy identity residual 0.

### pusht / lewm / source 21 (WM-DIAG0-A2-v1:pusht:root-021)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `ddee2491568bb49b2f671265adb6066052d1e1cfa332e0ae6c7958f41c2bb156`; accepted output seal `a083651adf4aa1458606c922e0389b1bc6c1b754231850b17fcb050ec829967b`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `757b5858deb53834b6fd688eec55b8e82f02f5250563aced2dec505f34e88e5d` | 12.6728306 / 1 | 33.4132843 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 4 / `ac3ca401da2aba9a7752a1d9c752944d1d2297196cb15c5f2eae5d80d435f969` | 12.6948643 / 4 | 30.7313461 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `23a7f458da437e02a1efcb7d8b5d400fc877590489e8d7cc6b9512fb0b298309` | 12.7218561 / 5 | 36.1346283 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 3 / `2d3ffb409e562e64993f6796ff8dcabe30fd703e5449b2a3be3b6a9b628e0da6` | 12.6926374 / 3 | 34.4655457 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 4 / `ac3ca401da2aba9a7752a1d9c752944d1d2297196cb15c5f2eae5d80d435f969` | 12.6948643 / 4 | 30.7313461 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 2.70397186 / 2.70396822; goal-direction term 7.54215481; squared-error term -4.83818659; algebra residual 0; saved-minus-float64 3.64622753e-06.
Mean squared error energy 38.4340643 = common 25.679889 + specific 12.7541753; coordinate MSE 0.200177418; energy identity residual -7.10542736e-15.

### pusht / lewm / source 22 (WM-DIAG0-A2-v1:pusht:root-022)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `b0f058f270ddc7cef39159212a12c660eb4c62db6e143c72d3a81b11d2cd014d`; accepted output seal `6dc0a58b038dc0feed8e9bc7928c7804f5f84b765dac50871d6b903cb914e6c5`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `e09ac424c869acbeda9bc90e948a4abc95a765fa00dd49dcfd28b792f01dd760` | 12.4101152 / 1 | 25.0165863 / 9 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 6 / `339851b68dee8268011a5b56285e7f157325819ed7fc636e4055e076f282ed59` | 12.5854635 / 7 | 19.8647881 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `f8ae683f529fce6e2bd1661606c0c498298b38f5370a72c507aa0c09fcc0fb86` | 12.4325075 / 2 | 24.3788147 / 7 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 9 / `7008b0d6eb2a76093b1c7e680f68ee4decdd534889bd8e5c85ae861eccd53268` | 16.5177956 / 10 | 33.7060165 / 13 | [1, 1] | tail_success @ 27 (elapsed 27); tail_success @ 26 (elapsed 26) | False |
| B | 6 / `339851b68dee8268011a5b56285e7f157325819ed7fc636e4055e076f282ed59` | 12.5854635 / 7 | 19.8647881 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 5.32714653 / 5.32714576; goal-direction term 8.9476457; squared-error term -3.62049994; algebra residual -1.77635684e-15; saved-minus-float64 7.66141783e-07.
Mean squared error energy 44.5240628 = common 24.0459041 + specific 20.4781587; coordinate MSE 0.23189616; energy identity residual 0.

### pusht / lewm / source 23 (WM-DIAG0-A2-v1:pusht:root-023)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `5e1dfe0f7557e0c55d0971f4ccb4b596343dd2140a8823e81bdfcad8a8d08829`; accepted output seal `b977151becfa7d01b2958acb2466ee15bc1fc5996d69d0b9b96df89eb249f5b3`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `c3bace9fa870b18154350e6c337eceeff5718313705c231fed84db8b9cd7ad00` | 10.5295143 / 1 | 29.0469971 / 12 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 13 / `fb0b52b4b9c77c9a8663ae6e94751e56ad3f4e27392e19a2095f1897c46936ad` | 25.5612373 / 14 | 6.17741013 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `45eb772185225409acdc00469d5bddaceefbfb5f92a0d4d9c133f772b5a8d6ee` | 10.5352306 / 2 | 25.6342525 / 5 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 9 / `1ebf3840d3ef02772506ef68cfbfbf46656697f8135ea90e5f4f9afc93dfcdbb` | 11.4004841 / 10 | 22.683363 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 11 / `db6b9d360de5bfb54da2d2ad5c8718a3c59c231152a7c13284017fc67cf82941` | 14.4015665 / 12 | 10.5035229 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 37.90131 / 37.9013075; goal-direction term 53.7824461; squared-error term -15.8811386; algebra residual -7.10542736e-15; saved-minus-float64 2.44787545e-06.
Mean squared error energy 29.8262663 = common 22.2706414 + specific 7.55562491; coordinate MSE 0.155345137; energy identity residual 0.

### pusht / lewm / source 24 (WM-DIAG0-A2-v1:pusht:root-024)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `a8d41906da3976dc6fca3bae336c50c563a3f720929ba0708542a98e8aab4362`; accepted output seal `df69bcd8779b9217c4acecc4159c77183cd21a6a67c941ef97412a1a930ed5af`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `5e2f5d0302d9d54791f63ae6263c8d77ae6ed41c2b6fd7499316ad7e59fd415a` | 12.1687775 / 1 | 9.84583473 / 9 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| O0 | 13 / `bdb7612ff3915af0bee8aa77e763c2c1882049c31a3d1d67b4d7168c77a4a0d7` | 28.2548409 / 14 | 7.06415987 / 1 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| native | 0 / `9886076b7931daac3bde93deec367f86c8f48c8b9735c6a5129164749af8473c` | 12.2413483 / 2 | 9.64424324 / 6 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| A | 3 / `9f29263058e2f95adb19e24abdb89152d4356385b230d9bfddd53d3c82d2c068` | 12.282814 / 4 | 9.86058235 / 11 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| B | 9 / `3db4b56a705de9a760ffc93381cf66f916a69f2fad7873d77a42adb3c2303ee7` | 14.0229464 / 10 | 7.31311321 / 2 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |

Selected-pair ordering error (saved / float64): 18.8677382 / 18.8677394; goal-direction term 19.173423; squared-error term -0.305683603; algebra residual -3.55271368e-15; saved-minus-float64 -1.14016784e-06.
Mean squared error energy 17.4353706 = common 10.9463455 + specific 6.48902515; coordinate MSE 0.0908092219; energy identity residual 0.

### pusht / lewm / source 25 (WM-DIAG0-A2-v1:pusht:root-025)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `0cf16389e845e5673cf3ad856d282652339a865c54f1c46cca51d61018991c8b`; accepted output seal `1fe34d7743d6d9a886ed02e0ccf54e86534098878f4a67e47c989aba5b84aa00`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `7e99417217da1c4b2093d49c31ea552d648200ee0e09602829a45a26fa40289e` | 4.55075502 / 1 | 5.43577862 / 1 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| O0 | 1 / `7e99417217da1c4b2093d49c31ea552d648200ee0e09602829a45a26fa40289e` | 4.55075502 / 1 | 5.43577862 / 1 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| native | 0 / `cd0ba453c263e21a62e833280e814848bdf8b82c8bcd6788a3b2be734770cc9f` | 4.58539629 / 4 | 6.49387646 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 3 / `ba9a46520dbdb429f10e04aad1c3439be75fb92000ae4c8615ecf966075b6d0f` | 4.58427382 / 3 | 6.79859734 / 5 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 0 / `cd0ba453c263e21a62e833280e814848bdf8b82c8bcd6788a3b2be734770cc9f` | 4.58539629 / 4 | 6.49387646 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 11.4597191 = common 8.93526053 + specific 2.52445856; coordinate MSE 0.0596860369; energy identity residual 0.

### pusht / lewm / source 26 (WM-DIAG0-A2-v1:pusht:root-026)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `658511c3eda6bee1eb23cd780cec1d46e6a1945721e7f3f096df7ed4a3561887`; accepted output seal `7cbfe171bab1ac6559166e77028e71b3e3472247d4cc62e7e95d3df20420ed0a`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `bbf928254d845f3580a3321430faecc8f121152f97fba59761d13f5500f03af9` | 10.5366182 / 1 | 27.5477791 / 9 | [1, 1] | tail_success @ 44 (elapsed 44); tail_success @ 46 (elapsed 46) | False |
| O0 | 7 / `995c7d087aa21908febd5d5eee321b6f2e1a8f1b24e430f355cf1fe3ef243aaa` | 10.9359379 / 8 | 4.02852011 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `5e87df66fd8bd26cff81531d8eab9bb55db2e44de46cef1a9a2cb6cd662d916c` | 10.8592005 / 5 | 15.6839142 / 4 | [1, 1] | tail_success @ 45 (elapsed 45); tail_success @ 46 (elapsed 46) | False |
| A | 7 / `995c7d087aa21908febd5d5eee321b6f2e1a8f1b24e430f355cf1fe3ef243aaa` | 10.9359379 / 8 | 4.02852011 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| B | 4 / `ee68736da263d741d04e3ab42a63e559cc54a25ffa705f3cb5d3500c51bc6bc1` | 10.7869473 / 4 | 7.1220355 / 3 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |

Selected-pair ordering error (saved / float64): 23.9185786 / 23.9185792; goal-direction term 44.7415154; squared-error term -20.8229362; algebra residual -7.10542736e-15; saved-minus-float64 -5.4915046e-07.
Mean squared error energy 39.980527 = common 18.8144873 + specific 21.1660397; coordinate MSE 0.208231912; energy identity residual -7.10542736e-15.

### pusht / lewm / source 27 (WM-DIAG0-A2-v1:pusht:root-027)

Original stratum: gain; action-choice changed: True; O0−P0: +100.000 pp. Source `ce652a8a82ac35fa9eedb3f74a1883a14e20bcc5133e0f626176c14d12dd460e`; accepted output seal `64531296f167329329226251568fdf34420ebe3664b8dc2f50485b0761dc7c0b`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `679a07047e701f8d4acaf2718d1e3ba0c0e1c4f8227b3c8dd81954ee0d438670` | 6.40911579 / 1 | 45.6276207 / 11 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 13 / `8d268dca1d9d29ac05eb76aa52af3fb7010211a898dc243360f35c77c4c904ae` | 34.9907722 / 14 | 9.763237 / 1 | [1, 1] | prefix_success @ 18 (elapsed 18); prefix_success @ 18 (elapsed 18) | True |
| native | 0 / `14aca1023f96f1210ac54d95486dea3961e9c72fc678501ff390006fe32c5943` | 6.5955019 / 3 | 42.2926445 / 9 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 11 / `083360b43da9c7331368668274d8b15406fa44095f7473e7da862c57a6bf7eff` | 16.0411301 / 12 | 15.1641693 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 3 / `165daa9ce6613080c3d66d3b4670020e61044e857a6d25b1886b237d15346e47` | 6.64401913 / 4 | 31.0872688 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 64.4460402 / 64.4460393; goal-direction term 74.4466029; squared-error term -10.0005636; algebra residual 0; saved-minus-float64 8.25912451e-07.
Mean squared error energy 43.5386066 = common 31.5972818 + specific 11.9413247; coordinate MSE 0.226763576; energy identity residual 0.

### pusht / lewm / source 28 (WM-DIAG0-A2-v1:pusht:root-028)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `fe5c75414d70b2c6a2c8482c63d95f1e79992f8da20dd10bd358c0ef4a1fe9a9`; accepted output seal `1138f24fb380a0bf254feeed18dba2df6bcdcc691ddf816a2f241178a0966a19`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `2aa860807860b2672178792a35dd54105fa89aad37d68a1e357a8aac7e9cc9ee` | 7.07951736 / 1 | 0.208544806 / 4 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| O0 | 11 / `0a3e2b8e465c4e8dda43794beed219db6199d0a416e5f1c493e2a2fffa9b965b` | 12.1299753 / 12 | 0.129968315 / 1 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| native | 0 / `d9a2b756a3ba582ef93e0503f328eedbf44dff2cde7e637090fe1a386e41790a` | 7.1030941 / 3 | 0.225421309 / 6 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| A | 4 / `8b3b9d0ee96a38019c8a4a49c13961fb645a18b2522a222e731836c64628aae2` | 7.12528419 / 5 | 0.224359989 / 5 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| B | 10 / `822dd135ef5754aad40ab21c880bbf0bdabe74e6e443b2ec2811755afb90b5a0` | 10.1715965 / 11 | 1.09181631 / 11 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |

Selected-pair ordering error (saved / float64): 5.12903444 / 5.12903413; goal-direction term 0.283474918; squared-error term 4.84555921; algebra residual 1.77635684e-15; saved-minus-float64 3.14325939e-07.
Mean squared error energy 18.8173558 = common 8.46986765 + specific 10.3474881; coordinate MSE 0.0980070613; energy identity residual 0.

### pusht / lewm / source 29 (WM-DIAG0-A2-v1:pusht:root-029)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `3fc331b6d1762bc829c6af87bfba8e5cf308acbcb717c94a473fe88b19807cff`; accepted output seal `270f3132f60311a32fda7f0a3c18ee123cf6a0b0e8187a21edc8ba574ecb44a0`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `5bf5cbf71b3ee9e42f080487c6e77397bca977b63b92ecc01cc4ad1fa54455fd` | 9.73043728 / 1 | 60.1515427 / 5 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 10 / `cc85dd5e8820f1f450430bec4b6ff14106f9166aa9666b4b4d839a959b916ccf` | 15.9606199 / 11 | 23.7882919 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `86254d4bd8ad776207bd7f7f8ec15d1e04049957397bb05226bc165a80a351a4` | 9.7417984 / 2 | 63.4041977 / 10 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 6 / `6603cb7a8b3853731738da3bdfc63f7bdaa27d3fe9df5dc87aaa98e8e06661e8` | 9.92331123 / 7 | 49.9641151 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 6 / `6603cb7a8b3853731738da3bdfc63f7bdaa27d3fe9df5dc87aaa98e8e06661e8` | 9.92331123 / 7 | 49.9641151 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 42.5934334 / 42.5934325; goal-direction term 62.5431012; squared-error term -19.9496688; algebra residual -7.10542736e-15; saved-minus-float64 8.94428986e-07.
Mean squared error energy 49.126718 = common 24.1118736 + specific 25.0148444; coordinate MSE 0.255868323; energy identity residual 0.

### pusht / lewm / source 30 (WM-DIAG0-A2-v1:pusht:root-030)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `dbf67d4d203157425761d2b88ce0efddf3987051e1939656aa05fd16928315cd`; accepted output seal `77e98d7c81ced72eb5be07df89b7d7f1a38e267d75afd108bc51bfb82c390734`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `ce722b19aa3906819ef2b5f57fb7de7df096d617428da50223b35f794d5cc9e5` | 5.03293037 / 1 | 17.2991028 / 5 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 13 / `ee2f3cbf7a9bc1aa57efec25e05c3eab21fbef8f9f973c0cedc3c55f00b8ab51` | 27.9446201 / 14 | 8.76847649 / 1 | [0, 1] | failure @ None (elapsed 50); tail_success @ 50 (elapsed 50) | False |
| native | 0 / `0acdfba9c28f2d960f248c5ddd9d750879c2c75aa8a47f577f77c9e5cde9227f` | 5.08833218 / 3 | 16.0811005 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 7 / `6dce513b3c247c1f6cbcce48d6363837b1ceabeeb7c4aafd02fa26bb14f240da` | 5.11359024 / 8 | 15.1307964 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 7 / `6dce513b3c247c1f6cbcce48d6363837b1ceabeeb7c4aafd02fa26bb14f240da` | 5.11359024 / 8 | 15.1307964 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 31.4423161 / 31.4423168; goal-direction term -1.41756954; squared-error term 32.8598864; algebra residual 1.0658141e-14; saved-minus-float64 -7.83995155e-07.
Mean squared error energy 24.5254893 = common 11.616834 + specific 12.9086553; coordinate MSE 0.127736924; energy identity residual 0.

### pusht / lewm / source 31 (WM-DIAG0-A2-v1:pusht:root-031)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `52c1a8639b9ad8aea8f694c904e91c707e975bda79cea9ec827751559b90b183`; accepted output seal `cc5cb24903653872e5c799a78783a359b99bd0f5b1588124a95849776991cf2d`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `ddab319edf0cce35aac0b70ab71dd5f66546ddcb738391c29a6522d3883721d3` | 14.8974247 / 1 | 13.218544 / 5 | [1, 1] | tail_success @ 32 (elapsed 32); tail_success @ 26 (elapsed 26) | False |
| O0 | 9 / `5927e66a2a7cf0a68c872cec76c8509db40cc395066489c2d5e86fbaf0432c25` | 18.8150215 / 10 | 10.1892662 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `be9bf33a30ddfd0477ac3093e347c482b31cc0f044504b6798b6a53da36ed770` | 15.2491474 / 4 | 13.4913416 / 7 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 45 (elapsed 45) | False |
| A | 1 / `ddab319edf0cce35aac0b70ab71dd5f66546ddcb738391c29a6522d3883721d3` | 14.8974247 / 1 | 13.218544 / 5 | [1, 1] | tail_success @ 32 (elapsed 32); tail_success @ 26 (elapsed 26) | False |
| B | 7 / `e0c62979423b6f4e498f6fcc03e2ff7e393c4da7694e772c2503ea67368643c6` | 15.375268 / 8 | 13.0886097 / 3 | [1, 1] | tail_success @ 32 (elapsed 32); tail_success @ 26 (elapsed 26) | False |

Selected-pair ordering error (saved / float64): 6.94687462 / 6.94687379; goal-direction term 12.1100581; squared-error term -5.16318428; algebra residual 0; saved-minus-float64 8.32633722e-07.
Mean squared error energy 14.2118985 = common 11.7440823 + specific 2.46781619; coordinate MSE 0.0740203044; energy identity residual 0.

### pusht / dinowm_noprop / source 0 (WM-DIAG0-A2-v1:pusht:root-000)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `d1a5c3494e3e76079237400cf6b0e4c93adedb04e1e2e6ab639fb8b6d369f530`; accepted output seal `85684771836724e0c0f8fa1b178d508a850af961f28c7c55fec0bdc8d371fb65`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `5107fc30eecf223c9a783fc34d93a57a6cb13d5d1b96f2ecd56f129610a11eb3` | 0.841311276 / 1 | 0.222003698 / 6 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| O0 | 9 / `7b4869748da4616c457f879fa8bd901bec53cdcdcb4e195dd7f78a280b146bf8` | 0.91288954 / 10 | 0.108198956 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `d216317018f9d8633f48d6d2a0be32721b93f91b09eaf5240565f73eaf276340` | 0.843290746 / 3 | 0.22055614 / 4 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| A | 4 / `eca445ea023f546a6db161d1cc9cd4d0cae987718e0dc4768a385bb9c10339cf` | 0.843972147 / 5 | 0.209945112 / 3 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| B | 5 / `7b74460124e9a09dd611840fc29e51ee47b42f2977880a82885645dbc298be24` | 0.844328701 / 6 | 0.207073003 / 2 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |

Selected-pair ordering error (saved / float64): 0.185383007 / 0.185382942; goal-direction term 0.169926937; squared-error term 0.0154560055; algebra residual -1.94289029e-16; saved-minus-float64 6.48516995e-08.
Mean squared error energy 77520.9663 = common 57400.7849 + specific 20120.1814; coordinate MSE 1.02998733; energy identity residual 0.

### pusht / dinowm_noprop / source 1 (WM-DIAG0-A2-v1:pusht:root-001)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `d5d72c1fadee52b73324ff7b892136fed3d73b2579e6f895c87fbd0f236f58a0`; accepted output seal `9a0020b6f72be2e524fb7d874a57e2181f4cdc6efb1f35596cc476b9473ef294`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `c7f08f14478015c7547810a673b5978cf7ef95e12f27c2c050016d34290529cf` | 0.412157118 / 1 | 0.216427758 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| O0 | 1 / `c7f08f14478015c7547810a673b5978cf7ef95e12f27c2c050016d34290529cf` | 0.412157118 / 1 | 0.216427758 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `0fc5153ccfa7c01180423d21385c4f18af6175101e866e944fbafabab32efa82` | 0.412983209 / 5 | 0.285782278 / 7 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| A | 2 / `b8f8389733fc3cc9ba215b073595057f1ba919e8de2ea140fdf99eb249671ab0` | 0.412788689 / 2 | 0.257353842 / 3 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| B | 1 / `c7f08f14478015c7547810a673b5978cf7ef95e12f27c2c050016d34290529cf` | 0.412157118 / 1 | 0.216427758 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 35880.268 = common 25839.2422 + specific 10041.0258; coordinate MSE 0.476725499; energy identity residual 0.

### pusht / dinowm_noprop / source 2 (WM-DIAG0-A2-v1:pusht:root-002)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `54d0f297a58e539ec34065307473d24162e9b6096b756cf06608c04c319b17f6`; accepted output seal `36266fbe43f23eb4d4970eca7bf2c3eb396a02ebcb54ead93894708fbe2c720e`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `ad92658fe3fb4f502d9ef2409db6a9836c958b688848849fddd2568499f17594` | 0.70439142 / 1 | 0.301475614 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 1 / `ad92658fe3fb4f502d9ef2409db6a9836c958b688848849fddd2568499f17594` | 0.70439142 / 1 | 0.301475614 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `3f62272fb9e9db9a36df2addc0066fb08521382e514dc21f377bf1c0fec6b4ae` | 0.718881726 / 9 | 0.304845542 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 4 / `a0159dcf45d874d7fecc35356829358f0921764eedf9a30351f8857aeca34a45` | 0.706123471 / 4 | 0.356641591 / 8 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 2 / `8fd52a0e9fddaee4faf799445642e0a8a458e571113d60bf832d6bb715dabed5` | 0.704500258 / 2 | 0.321055174 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 45273.605 = common 34743.0031 + specific 10530.6019; coordinate MSE 0.601530679; energy identity residual 7.27595761e-12.

### pusht / dinowm_noprop / source 3 (WM-DIAG0-A2-v1:pusht:root-003)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `b2a83c1e38c126aa8c6a1a220c264fc6985dd934da4266987fd5c2cdbf4177cf`; accepted output seal `a246f8a103ee75b66905979c4dbd4d4ab57cec4e239c3a65e390b05ff3cb488b`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `574eeb35ff1e78f4f43078edcb1f1fe8442c2b07d7599bf90ef544da3a11ed77` | 0.344602525 / 1 | 0.237797588 / 8 | [1, 1] | tail_success @ 47 (elapsed 47); tail_success @ 49 (elapsed 49) | False |
| O0 | 13 / `e5380f4869fcafd95a8723a3213cffbc58c04764b916faa7106e013dc73babda` | 0.47080785 / 14 | 0.0561926812 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| native | 0 / `8d5a3acee53312598a05ecfa3800280b09c5a4366b64ac910da8b6072eb253a1` | 0.380227834 / 9 | 0.151943147 / 4 | [1, 0] | tail_success @ 47 (elapsed 47); failure @ None (elapsed 50) | False |
| A | 10 / `6f4fdd15cdf459e3bf49c80261c3df6a33bde0f460374ece5a618249493dca82` | 0.412904471 / 11 | 0.0638686717 / 2 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| B | 0 / `8d5a3acee53312598a05ecfa3800280b09c5a4366b64ac910da8b6072eb253a1` | 0.380227834 / 9 | 0.151943147 / 4 | [1, 0] | tail_success @ 47 (elapsed 47); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0.307810232 / 0.30781023; goal-direction term 0.208915689; squared-error term 0.0988945416; algebra residual -5.55111512e-17; saved-minus-float64 1.59769031e-09.
Mean squared error energy 35203.318 = common 26703.1201 + specific 8500.1979; coordinate MSE 0.46773116; energy identity residual 0.

### pusht / dinowm_noprop / source 4 (WM-DIAG0-A2-v1:pusht:root-004)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `948749939d46174c13be80bfd4e2ed6a286b84c0c971040feec24358aa29ce59`; accepted output seal `5194681e3776efbd363482704da982b235807142080a19025ad3fb9f5fe9b24a`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `160a482266b0ac40b66aeefeccde8158702a4116010cb9563b250892acde0c78` | 0.451826125 / 1 | 0.0797468275 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| O0 | 1 / `160a482266b0ac40b66aeefeccde8158702a4116010cb9563b250892acde0c78` | 0.451826125 / 1 | 0.0797468275 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `44a0215827989f59e5182d68522948751ff5a3f5d2c7b39356ecb41a708f2f9e` | 0.462835193 / 9 | 0.21716927 / 8 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| A | 7 / `cd14980a9b1d589fc720512ca979b1a52c8f23dd8515fc83c3e829d23fe84d64` | 0.455823243 / 7 | 0.267954558 / 11 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| B | 1 / `160a482266b0ac40b66aeefeccde8158702a4116010cb9563b250892acde0c78` | 0.451826125 / 1 | 0.0797468275 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 36520.7924 = common 25654.7852 + specific 10866.0072; coordinate MSE 0.485235869; energy identity residual -7.27595761e-12.

### pusht / dinowm_noprop / source 5 (WM-DIAG0-A2-v1:pusht:root-005)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `535042f40203b10edf2b204ca62d26de19e3d7bda2babf136f1a473565415ae4`; accepted output seal `5cd2c64672bfbbd95da9dfee99260b888a85119163fb3c131b6ad5540da68ff7`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `5e33dc0e86acc850d98e9cf49aef81bee52b452d7634b4aa3afba140d9322986` | 0.922653675 / 1 | 0.48070702 / 13 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 11 / `719e205365e6b27fbc20300cb7dd2525eec5572a9d43507068a2d21f3d31d300` | 1.03035271 / 12 | 0.354925871 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `6daf41e899d111d665849503e64038bcfe5be737b6992861aa7cfdeab0a06a1c` | 0.925520182 / 3 | 0.468762338 / 8 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 8 / `e228996f5b49195e4abf998e3bc8c60233a8b8209f9fd07509d7c6be836ec667` | 0.928421915 / 9 | 0.450445265 / 7 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 7 / `aa656c2aef61125a4dac21c01c446e8ca42c0e7c8c55db1c624097539ccc9535` | 0.927713394 / 8 | 0.44238165 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0.233480185 / 0.233480167; goal-direction term 0.110457471; squared-error term 0.123022696; algebra residual -1.94289029e-16; saved-minus-float64 1.78357395e-08.
Mean squared error energy 59874.6489 = common 51890.1927 + specific 7984.45616; coordinate MSE 0.795528392; energy identity residual 7.27595761e-12.

### pusht / dinowm_noprop / source 6 (WM-DIAG0-A2-v1:pusht:root-006)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `bda1cf4c0ea2b4c6e914095d51ceec295df053380549867bfbc66905f883f7b0`; accepted output seal `410fafcd339e3023e2fb611b62ce3c500e7753bf42d98f5287d2c75498203283`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `c419cc4e86047e4b75ae4c944f7825e1833dbd86919f09c2d23d438f491380b5` | 0.52671212 / 1 | 0.165357888 / 8 | [1, 1] | prefix_success @ 4 (elapsed 4); prefix_success @ 4 (elapsed 4) | True |
| O0 | 12 / `ead7db9e9faeb1e243dbf3045465a42932b08ec8c1a169101c9a76cb5b7fcfe8` | 0.667418003 / 13 | 0.133626074 / 1 | [1, 1] | prefix_success @ 4 (elapsed 4); prefix_success @ 4 (elapsed 4) | True |
| native | 0 / `80df3bc6b3589376f14c99a68b82144b2a7cf2f118ff4ed279a186ca2ef00000` | 0.529957712 / 2 | 0.174246132 / 9 | [1, 1] | prefix_success @ 4 (elapsed 4); prefix_success @ 4 (elapsed 4) | True |
| A | 8 / `d3e06712c2dd496130ab8b0f1b1b175d37c7317a7990fca43e22aaa5ec87a2c9` | 0.531583309 / 9 | 0.160773411 / 6 | [1, 1] | prefix_success @ 4 (elapsed 4); prefix_success @ 4 (elapsed 4) | True |
| B | 7 / `d7d5ba749b5c31dd924b6cbe1d2566950981affe59f8040ed477ccf42ca8a289` | 0.531552672 / 8 | 0.163551763 / 7 | [1, 1] | prefix_success @ 4 (elapsed 4); prefix_success @ 4 (elapsed 4) | True |

Selected-pair ordering error (saved / float64): 0.172437698 / 0.172437719; goal-direction term 0.0814087234; squared-error term 0.0910289956; algebra residual 8.32667268e-17; saved-minus-float64 -2.14175247e-08.
Mean squared error energy 50968.0513 = common 38046.1583 + specific 12921.893; coordinate MSE 0.677190307; energy identity residual -7.27595761e-12.

### pusht / dinowm_noprop / source 7 (WM-DIAG0-A2-v1:pusht:root-007)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `7699419198b50b76a2259ee4ed40a53718a9588ae1e88bef47eeb2ddc7f31d1e`; accepted output seal `8f8f7b44220ee2fecf499f29cf504031467c9e25794d02b6491efca60aea0243`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `7e22f6af7e146c9971b5f33be23b8435a201ebf784083c8620e3c0083fd8de42` | 0.572013497 / 1 | 0.316353559 / 11 | [1, 1] | tail_success @ 26 (elapsed 26); tail_success @ 27 (elapsed 27) | False |
| O0 | 9 / `ac55fa6f7ede978bb21c6dafdcbcf584dd6d3d060f6ef8db2e52cc98b16a085f` | 0.620747983 / 10 | 0.147381142 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `b67860c6c8c21f5dc5bda4f37bc2a3083915a634efffdba547f5225d4d3cb121` | 0.580490828 / 9 | 0.227126971 / 5 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| A | 4 / `a9f35fea3b47cc57ea8f75fa65fbedd83dfe0b523e5811c087be0dbae58c9b79` | 0.574948132 / 4 | 0.241275191 / 6 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| B | 2 / `391e9743e494ad8bb1bcc74cc1a3fc8496c307aacee01a641d0eb1310acd3125` | 0.573900044 / 2 | 0.177428097 / 2 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |

Selected-pair ordering error (saved / float64): 0.217706904 / 0.217706912; goal-direction term 0.167169459; squared-error term 0.0505374523; algebra residual -2.77555756e-17; saved-minus-float64 -8.01278852e-09.
Mean squared error energy 54808.6443 = common 39583.2781 + specific 15225.3662; coordinate MSE 0.728218594; energy identity residual 7.27595761e-12.

### pusht / dinowm_noprop / source 8 (WM-DIAG0-A2-v1:pusht:root-008)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `54bf04553219871f33d7e5aeb5c91bcc7347bf9fe5a48cdcfef102b831332f9c`; accepted output seal `6e45c43a910e81d300c5f97590b8621f286f4c6b4ede8589fb021498cbbe4c61`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `3842c4ee2693d3ab568e363714a4834a476ff7c52760eac05955ff7874930df7` | 0.869573236 / 1 | 0.220386714 / 5 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 48 (elapsed 48) | False |
| O0 | 3 / `bf36ae5f75387ba80e862e3cc6fdd5e59ad73620c287721da744c01a1f539e43` | 0.870872557 / 3 | 0.195244998 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `58facf3988f684414e51454050ce043848f655b73dc37b24caaa4c9fa46539e6` | 0.879766762 / 9 | 0.204445496 / 2 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| A | 0 / `58facf3988f684414e51454050ce043848f655b73dc37b24caaa4c9fa46539e6` | 0.879766762 / 9 | 0.204445496 / 2 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| B | 4 / `65f0f2b16002699a8c7a46ff1097da698180aaf46ca354ebb1b47e239b88dc87` | 0.873583376 / 4 | 0.210270241 / 3 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 0.0264410377 / 0.0264409955; goal-direction term 0.0457277794; squared-error term -0.0192867839; algebra residual 1.38777878e-16; saved-minus-float64 4.2184723e-08.
Mean squared error energy 75836.1254 = common 62842.5013 + specific 12993.6241; coordinate MSE 1.00760158; energy identity residual 0.

### pusht / dinowm_noprop / source 9 (WM-DIAG0-A2-v1:pusht:root-009)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `3fc3f6384f333ab5c535ee94248324315da7cd07d2faab908fd35557da3f66bf`; accepted output seal `1f2b27592b35accb140b0f2bb5e9207f8d5792f921f6dfc0d36d6c25ffe44362`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 0 / `ba801cfddb50d0a0a3e5d52f88728d2c442b4347d17f0e107b6588b565321d86` | 0.568889141 / 1 | 0.296082884 / 7 | [1, 1] | prefix_success @ 9 (elapsed 9); prefix_success @ 9 (elapsed 9) | True |
| O0 | 9 / `edcc9833d62532f58c4fbf4d2a1d231db39449f8937a37ead612da4b6d33e894` | 0.601680756 / 10 | 0.201404288 / 1 | [1, 1] | prefix_success @ 9 (elapsed 9); prefix_success @ 9 (elapsed 9) | True |
| native | 0 / `ba801cfddb50d0a0a3e5d52f88728d2c442b4347d17f0e107b6588b565321d86` | 0.568889141 / 1 | 0.296082884 / 7 | [1, 1] | prefix_success @ 9 (elapsed 9); prefix_success @ 9 (elapsed 9) | True |
| A | 6 / `520c6ade76dd461400e12967e441df026361754ae199b32d6577b9cfaab1571e` | 0.572001457 / 7 | 0.36280027 / 8 | [1, 1] | prefix_success @ 9 (elapsed 9); prefix_success @ 9 (elapsed 9) | True |
| B | 0 / `ba801cfddb50d0a0a3e5d52f88728d2c442b4347d17f0e107b6588b565321d86` | 0.568889141 / 1 | 0.296082884 / 7 | [1, 1] | prefix_success @ 9 (elapsed 9); prefix_success @ 9 (elapsed 9) | True |

Selected-pair ordering error (saved / float64): 0.12747021 / 0.12747026; goal-direction term 0.191324947; squared-error term -0.0638546873; algebra residual -2.22044605e-16; saved-minus-float64 -4.98080496e-08.
Mean squared error energy 61763.9033 = common 45816.0437 + specific 15947.8596; coordinate MSE 0.820630093; energy identity residual -7.27595761e-12.

### pusht / dinowm_noprop / source 10 (WM-DIAG0-A2-v1:pusht:root-010)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `f1782760f3c050760c98657979ecbb4462605d5e9ca86c28993178e2ddf746d4`; accepted output seal `cfb41ed1de4877e470dd6fc96e67c2556a76d9e601d315d23a1f54e317694022`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `335c10b867ed9b8892bf673a152520e30919d4e76b3d2031811067eab23cfd35` | 0.441121519 / 1 | 0.303977281 / 2 | [1, 1] | prefix_success @ 9 (elapsed 9); prefix_success @ 9 (elapsed 9) | True |
| O0 | 11 / `dd538699676f9fa6d110a6498bcc5f5dfce56df23759528d4ba58bbb904182c8` | 0.537384093 / 12 | 0.167826921 / 1 | [1, 1] | prefix_success @ 10 (elapsed 10); prefix_success @ 10 (elapsed 10) | True |
| native | 0 / `bc74242d97bc360724a84786ada5a9aacfc4476abdfad91cb566ce02d4cccedf` | 0.442124039 / 3 | 0.37467441 / 11 | [1, 1] | prefix_success @ 6 (elapsed 6); prefix_success @ 6 (elapsed 6) | True |
| A | 0 / `bc74242d97bc360724a84786ada5a9aacfc4476abdfad91cb566ce02d4cccedf` | 0.442124039 / 3 | 0.37467441 / 11 | [1, 1] | prefix_success @ 6 (elapsed 6); prefix_success @ 6 (elapsed 6) | True |
| B | 12 / `707c3bb060d7391da3ad1bdcfd611c77877053570f61163eb85ae5aaba0e7e81` | 0.584812045 / 13 | 0.350720942 / 7 | [1, 1] | prefix_success @ 7 (elapsed 7); prefix_success @ 7 (elapsed 7) | True |

Selected-pair ordering error (saved / float64): 0.232412934 / 0.232412959; goal-direction term 0.281676472; squared-error term -0.0492635136; algebra residual 2.77555756e-17; saved-minus-float64 -2.45240171e-08.
Mean squared error energy 51486.6494 = common 37854.776 + specific 13631.8734; coordinate MSE 0.684080694; energy identity residual 7.27595761e-12.

### pusht / dinowm_noprop / source 11 (WM-DIAG0-A2-v1:pusht:root-011)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `93e2c4fa59957e684682d5cddf6daba9fd645d49b595d0e7d81acc43e06573d3`; accepted output seal `49311262160304c69fd13dde534722f9831f0c4fedf97acff346f3b5b63135eb`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `3b92549762ffa1966985088c15d2a9efbac8c9e56ee3a0643e6a57f106595c99` | 0.642505765 / 1 | 0.311024785 / 9 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| O0 | 2 / `78c118e6d600c7888f0f875ea41e96946626f211bde0ea713dc58a2ec1107c2f` | 0.647011995 / 2 | 0.110397443 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `45907c8f5fabc6160023aaf1c06c142afa4ff7da6aaa1afec466d191a4db7486` | 0.647387862 / 5 | 0.261237353 / 5 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| A | 5 / `a26a5ef86df09dcf0a4e7e4ef78c7c87294aed7d62ca633612afff2e3d49769b` | 0.648033261 / 6 | 0.219334871 / 4 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| B | 8 / `3994152147c397a587ebd705af1248b0d70aa284c78bc3ca093e09761976b94c` | 0.648386896 / 9 | 0.150603503 / 3 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |

Selected-pair ordering error (saved / float64): 0.205133572 / 0.205133549; goal-direction term 0.38338222; squared-error term -0.178248672; algebra residual -2.77555756e-17; saved-minus-float64 2.35892412e-08.
Mean squared error energy 65066.2215 = common 46882.4282 + specific 18183.7934; coordinate MSE 0.864506557; energy identity residual 7.27595761e-12.

### pusht / dinowm_noprop / source 12 (WM-DIAG0-A2-v1:pusht:root-012)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `c7c95ad959ac93077274408571f81600641eb482073ff2b6f75799425c4d0a3f`; accepted output seal `bfb115f6035ec5d82ce54bc0c5a0a60fa0d63fa141fcda050e06583f20fe5a91`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `4cc6dc764f1a5af7b506802548fa5d61e588dc5020e483a976738d4cbf85529f` | 0.379651368 / 1 | 0.151949361 / 14 | [1, 1] | tail_success @ 49 (elapsed 49); tail_success @ 49 (elapsed 49) | False |
| O0 | 9 / `aab3b2befe4e8ffb63669ff87d3402530d829b9d01bf191d07722efc76a57477` | 0.398786098 / 10 | 0.111803532 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `a5f844519c5ed9fd6d0f5530f562ce3cd84880e37a7ee0fd6ed39fe72725f684` | 0.383317888 / 7 | 0.113379136 / 4 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| A | 7 / `3f9094bd6e42cb2106fdab458a3e31b5b8e5cf6dc59d1a8098292127f2205d0c` | 0.383603513 / 8 | 0.113379136 / 5 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| B | 9 / `aab3b2befe4e8ffb63669ff87d3402530d829b9d01bf191d07722efc76a57477` | 0.398786098 / 10 | 0.111803532 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 0.0592805594 / 0.0592805914; goal-direction term 0.0189429836; squared-error term 0.0403376078; algebra residual -4.16333634e-17; saved-minus-float64 -3.20132798e-08.
Mean squared error energy 32251.4578 = common 24814.3303 + specific 7437.1275; coordinate MSE 0.428511078; energy identity residual 0.

### pusht / dinowm_noprop / source 13 (WM-DIAG0-A2-v1:pusht:root-013)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `8ee5403bec122a6037a795c51813b437d5844333e0731872970fd32f02226f92`; accepted output seal `2d50646ee4b4f0266968c33111855094280e3fc247772ac66afffe735f4e619c`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `9404d565fbfe4a1be73427cc2b522184e41cf98828b140803fe095adcbebcd99` | 0.37475872 / 1 | 0.105216525 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| O0 | 1 / `9404d565fbfe4a1be73427cc2b522184e41cf98828b140803fe095adcbebcd99` | 0.37475872 / 1 | 0.105216525 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| native | 0 / `57d6a8dff36eeec7916086c010eb878abe8253b017f9c1adfa168c4e91a657fe` | 0.377655417 / 4 | 0.145239905 / 6 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| A | 4 / `0dddfefa4726af8115d2ec04456a7db3ae66e0e1baaec105e37db8dbfc67b184` | 0.378028661 / 5 | 0.123541459 / 3 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| B | 1 / `9404d565fbfe4a1be73427cc2b522184e41cf98828b140803fe095adcbebcd99` | 0.37475872 / 1 | 0.105216525 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 33052.3418 = common 23111.0435 + specific 9941.29826; coordinate MSE 0.439152075; energy identity residual 7.27595761e-12.

### pusht / dinowm_noprop / source 14 (WM-DIAG0-A2-v1:pusht:root-014)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `07f0b26727689cbba077041dfc815eb41cf6f03e86b7da595eb8950939067d5b`; accepted output seal `e93e7a1f364b3232437a7e6f579b85690059f9d92fcfd43be740bf6658997b57`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `ce60a8b822ed0ee927cd8ce2a0ef94cb90d2783ee708815e8087f8c61a74475d` | 1.21807396 / 1 | 0.583225191 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 9 / `b37886c885e3f7f7de879b259bcbf0a7e1d4cfe050f244795d589790ffe18a06` | 1.29830086 / 10 | 0.54760778 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `5f7926d930d694eb7e76af70227ae7ef1b04c7a845c8f9f753fff9dadda3fbad` | 1.22979319 / 4 | 0.577627718 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 0 / `5f7926d930d694eb7e76af70227ae7ef1b04c7a845c8f9f753fff9dadda3fbad` | 1.22979319 / 4 | 0.577627718 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 9 / `b37886c885e3f7f7de879b259bcbf0a7e1d4cfe050f244795d589790ffe18a06` | 1.29830086 / 10 | 0.54760778 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0.115844309 / 0.115844374; goal-direction term 0.0762603094; squared-error term 0.0395840649; algebra residual -1.11022302e-16; saved-minus-float64 -6.50284696e-08.
Mean squared error energy 137152.463 = common 86395.1793 + specific 50757.2841; coordinate MSE 1.82228507; energy identity residual 2.91038305e-11.

### pusht / dinowm_noprop / source 15 (WM-DIAG0-A2-v1:pusht:root-015)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `681672d6d14efd266c9e9f0068972f38f94b37a7345dd9d71c82653d7c6ac1a9`; accepted output seal `7e22225c8b23958a06ec2f0ba18464fb1d1fb0d952f0646464205cbfb825ea0a`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `1b10e96b267820ba4cb88ebbb842e9a59dec98c2b603d364e56fa9d56b0b4502` | 0.526886821 / 1 | 0.0849014223 / 3 | [1, 1] | prefix_success @ 15 (elapsed 15); prefix_success @ 15 (elapsed 15) | True |
| O0 | 8 / `0d8bd4cd59a5bec848208dcbe0b20e29d09a1fe218fae87af5e2e6b6af61ebf9` | 0.532448947 / 8 | 0.0750608072 / 1 | [1, 1] | prefix_success @ 15 (elapsed 15); prefix_success @ 15 (elapsed 15) | True |
| native | 0 / `4d184fd328dbdaaae1d881bacc69f58b7516a299e45f4c9130298cd7a2368f28` | 0.533427298 / 9 | 0.116201423 / 8 | [1, 1] | prefix_success @ 15 (elapsed 15); prefix_success @ 15 (elapsed 15) | True |
| A | 2 / `e8e217f7cb2d31920f48aed16d9b672add2e8f703cd69115e0f4999cff748348` | 0.529293358 / 2 | 0.0994976684 / 4 | [1, 1] | prefix_success @ 15 (elapsed 15); prefix_success @ 15 (elapsed 15) | True |
| B | 8 / `0d8bd4cd59a5bec848208dcbe0b20e29d09a1fe218fae87af5e2e6b6af61ebf9` | 0.532448947 / 8 | 0.0750608072 / 1 | [1, 1] | prefix_success @ 15 (elapsed 15); prefix_success @ 15 (elapsed 15) | True |

Selected-pair ordering error (saved / float64): 0.0154027417 / 0.0154027927; goal-direction term -0.040268638; squared-error term 0.0556714307; algebra residual -2.49800181e-16; saved-minus-float64 -5.09786345e-08.
Mean squared error energy 41668.2533 = common 35604.5468 + specific 6063.70644; coordinate MSE 0.55362794; energy identity residual 7.27595761e-12.

### pusht / dinowm_noprop / source 16 (WM-DIAG0-A2-v1:pusht:root-016)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `76fb90cccfc1d0005d511898eb6f2b794cd65b2bfdee0124250b46557ab718a2`; accepted output seal `325939ea3e0ae19d53e6bbdcb99349316dab878caccaae8dfea02c2ac9d23c43`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 0 / `ba8b21af9cac4d16ded22dddea37f9687ba8e54de46c8d3c499c4f76dc22a3b5` | 0.434396535 / 1 | 0.193392128 / 9 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| O0 | 8 / `6d8f207e4ade6c0b80c281d8eacd8d2b9bb3c7aada38802eab42cb953ac6506f` | 0.438296556 / 9 | 0.149213716 / 1 | [1, 1] | prefix_success @ 18 (elapsed 18); prefix_success @ 18 (elapsed 18) | True |
| native | 0 / `ba8b21af9cac4d16ded22dddea37f9687ba8e54de46c8d3c499c4f76dc22a3b5` | 0.434396535 / 1 | 0.193392128 / 9 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| A | 8 / `6d8f207e4ade6c0b80c281d8eacd8d2b9bb3c7aada38802eab42cb953ac6506f` | 0.438296556 / 9 | 0.149213716 / 1 | [1, 1] | prefix_success @ 18 (elapsed 18); prefix_success @ 18 (elapsed 18) | True |
| B | 8 / `6d8f207e4ade6c0b80c281d8eacd8d2b9bb3c7aada38802eab42cb953ac6506f` | 0.438296556 / 9 | 0.149213716 / 1 | [1, 1] | prefix_success @ 18 (elapsed 18); prefix_success @ 18 (elapsed 18) | True |

Selected-pair ordering error (saved / float64): 0.0480784327 / 0.0480784472; goal-direction term 0.0319948682; squared-error term 0.016083579; algebra residual -2.77555756e-16; saved-minus-float64 -1.45125855e-08.
Mean squared error energy 42907.3886 = common 34220.044 + specific 8687.34457; coordinate MSE 0.570091791; energy identity residual 7.27595761e-12.

### pusht / dinowm_noprop / source 17 (WM-DIAG0-A2-v1:pusht:root-017)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `12343cc5452c96e487860e89456e760d38ed4e0c3b916886af7920783b3e4eaf`; accepted output seal `13cdbebf0c41aee5c6ceee9834d8ebd9d6600aa56ead9aebbd9254cdc2ddec40`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `7112520c812899414d14b1a11d59e0cf17a47490940bf2623cc05fce038ab69b` | 0.922844291 / 1 | 0.835193157 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 3 / `e0301e6250150468662877d71aa70002f6e45eeecbfc393c20134992b1d70c6e` | 0.924774468 / 3 | 0.811634243 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `c3e66db0167fe366a54007e77aff0b4edfb156e905c461e392c2278a3da8c076` | 0.944577754 / 9 | 0.848633587 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 7 / `111edf02675b19e795d9695477f694a1d88ad997c285b509a9c9e97b224c6e0d` | 0.925399423 / 7 | 0.853571594 / 9 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 3 / `e0301e6250150468662877d71aa70002f6e45eeecbfc393c20134992b1d70c6e` | 0.924774468 / 3 | 0.811634243 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0.0254890919 / 0.0254890336; goal-direction term 0.00488418559; squared-error term 0.020604848; algebra residual -3.74700271e-16; saved-minus-float64 5.83016272e-08.
Mean squared error energy 15200.714 = common 8942.08956 + specific 6258.62444; coordinate MSE 0.201965269; energy identity residual 0.

### pusht / dinowm_noprop / source 18 (WM-DIAG0-A2-v1:pusht:root-018)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `48d6d738d0fa1b767e266b1ff1efa62307334876a28152e3bb2cce63708e4285`; accepted output seal `f6d47e60f4b13a1c66e05b79d1d10aab8bfd49fc64266019f6d576efa5bc6522`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `f6bba5c5ae3ea8d24c57980866e809e65f503d72318f22898884cbe6db447c2c` | 0.617152452 / 1 | 0.318706751 / 4 | [1, 1] | tail_success @ 35 (elapsed 35); tail_success @ 35 (elapsed 35) | False |
| O0 | 12 / `777a65fabf421e97ab96a4a6cfeca9db26accc2d44bd2091aefbc5fa6420f9d6` | 0.73323679 / 13 | 0.262409449 / 1 | [1, 1] | prefix_success @ 8 (elapsed 8); prefix_success @ 8 (elapsed 8) | True |
| native | 0 / `ea8c535ce6f871dd39267ada18b8cdc194c28d801cf883b286b8c7947f1f9256` | 0.618604898 / 3 | 0.337106913 / 8 | [1, 1] | tail_success @ 34 (elapsed 34); tail_success @ 35 (elapsed 35) | False |
| A | 12 / `777a65fabf421e97ab96a4a6cfeca9db26accc2d44bd2091aefbc5fa6420f9d6` | 0.73323679 / 13 | 0.262409449 / 1 | [1, 1] | prefix_success @ 8 (elapsed 8); prefix_success @ 8 (elapsed 8) | True |
| B | 12 / `777a65fabf421e97ab96a4a6cfeca9db26accc2d44bd2091aefbc5fa6420f9d6` | 0.73323679 / 13 | 0.262409449 / 1 | [1, 1] | prefix_success @ 8 (elapsed 8); prefix_success @ 8 (elapsed 8) | True |

Selected-pair ordering error (saved / float64): 0.172381639 / 0.172381733; goal-direction term -0.14106894; squared-error term 0.313450673; algebra residual -1.38777878e-16; saved-minus-float64 -9.35711175e-08.
Mean squared error energy 42164.5155 = common 35305.2811 + specific 6859.23437; coordinate MSE 0.56022156; energy identity residual 0.

### pusht / dinowm_noprop / source 19 (WM-DIAG0-A2-v1:pusht:root-019)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `f28141742dedf35397176c48fb02e7d740bff7714cfa99fb5bc63bc9495e14f3`; accepted output seal `49fbee44246c9ac7401d5a647cea15d9e0f29584c958890c86044e5bdcc47e6b`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `03040b9e42396ef1917be147f7cde7d7e073167347dd960b97967f844fcdfc44` | 0.839923263 / 1 | 0.784186482 / 12 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 14 / `4791d293b1cbe4b934d3e8372b7a59dda8b9896842f2d6ced8d01e41e5c92bbd` | 1.61629283 / 15 | 0.58435905 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `08b396f12f4a7b31c74810cb57241a0a08d660d3c3b4f77027920455706d94fd` | 0.851045072 / 8 | 0.671689153 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 0 / `08b396f12f4a7b31c74810cb57241a0a08d660d3c3b4f77027920455706d94fd` | 0.851045072 / 8 | 0.671689153 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 0 / `08b396f12f4a7b31c74810cb57241a0a08d660d3c3b4f77027920455706d94fd` | 0.851045072 / 8 | 0.671689153 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0.976197004 / 0.97619703; goal-direction term 0.637968205; squared-error term 0.338228824; algebra residual -2.22044605e-16; saved-minus-float64 -2.53916405e-08.
Mean squared error energy 91800.0839 = common 65233.1638 + specific 26566.9201; coordinate MSE 1.21970775; energy identity residual -1.45519152e-11.

### pusht / dinowm_noprop / source 20 (WM-DIAG0-A2-v1:pusht:root-020)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `6279b05490a6d94f423beeea39bba9905a43a3ade3ed2618b80887a98477ab3e`; accepted output seal `eb407b0e6e7b4422419d77dc673eef2f5a323e015b99bdeb90dda814d8ef31ed`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `ade82f791a635731b31e2fe40780b3564b822f3d884e9ba6128f36072f7d04c1` | 0.491463274 / 1 | 0.313368082 / 5 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| O0 | 11 / `b99577feb1db46890be38875cb5ddbd9083c42a2503542e03f71a1a295aa4672` | 0.587469399 / 12 | 0.258021772 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `fabc9c6c2e2b88094dbf83705bdf47d60bd9743be046e00ad1f7219c41a5cd2e` | 0.493783325 / 5 | 0.363617986 / 10 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| A | 2 / `7b0e7e72446fb535794258f033a69e53a08ba9f0349569afa1df04fda80f5304` | 0.492401212 / 2 | 0.292816132 / 2 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| B | 6 / `a3c656820711ce49516807832ee0d7231c5332c874296785e1951fd58614d414` | 0.494693667 / 7 | 0.368316323 / 11 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |

Selected-pair ordering error (saved / float64): 0.151352435 / 0.151352426; goal-direction term 0.0767108754; squared-error term 0.0746415507; algebra residual 1.11022302e-16; saved-minus-float64 9.31570232e-09.
Mean squared error energy 51566.8071 = common 40325.3221 + specific 11241.4849; coordinate MSE 0.685145715; energy identity residual -7.27595761e-12.

### pusht / dinowm_noprop / source 21 (WM-DIAG0-A2-v1:pusht:root-021)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `d78833b175edac0dee752b16163952bf138095068660208ec310050e93a25871`; accepted output seal `2c4a04c31816d8554fff7567f687c0ac7fc2d0b5351e806d6c60db253bcca050`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `21bccbe4530240bd57ba6ee084fd06b1542d7379fb085f8998db19f6c06b6af6` | 1.18166804 / 1 | 1.04646409 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 8 / `0f08ee977a6e42876cfd13eb2e48ed39d7bc90bf65e70d0734f1384f3e4028df` | 1.18407953 / 8 | 1.00671756 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `b609e8e6fd0ded1b1b666551a1e0d24f366893754b8357f1c92ef5ad467d906c` | 1.20761335 / 9 | 1.11595452 / 9 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 7 / `a9dba6e40bfd1394c8da5a918660c5da24ae6ea8a67d1c0113819a2bbdde37cf` | 1.18297172 / 7 | 1.03129339 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 9 / `b86fe593202748e052e13b6fad710da3a5d3dad5469d9efbb1e1c629dfbb4efc` | 1.22384191 / 10 | 1.0230037 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0.0421580076 / 0.0421582097; goal-direction term 0.0443171281; squared-error term -0.0021589184; algebra residual 3.88578059e-16; saved-minus-float64 -2.02102109e-07.
Mean squared error energy 25932.6058 = common 17586.559 + specific 8346.04682; coordinate MSE 0.344555243; energy identity residual 0.

### pusht / dinowm_noprop / source 22 (WM-DIAG0-A2-v1:pusht:root-022)

Original stratum: gain; action-choice changed: True; O0−P0: +100.000 pp. Source `ab63ccff0d32a8b0ba11e320982681e10940b306ee3ca290a32a5dc0ed55fd36`; accepted output seal `a63e9641e2c76b7e15de4f7170800401380b9a3a2709355eae8e971a9371ad14`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `7c6bde5b844fcfac650398dd829a4362bfe8c99c2de1118b654e2f1153818d19` | 0.453473449 / 1 | 0.376696467 / 9 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 15 / `611019066f9b86c2f5a51cd4b783211933b218356ab76684128b6dd56cc27116` | 1.44839418 / 16 | 0.266423076 / 1 | [1, 1] | prefix_success @ 5 (elapsed 5); prefix_success @ 5 (elapsed 5) | True |
| native | 0 / `ca8e2768beec8b4ec06367a931f9661a403bd5637f41e639423fd465251c1308` | 0.455920994 / 9 | 0.343710423 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 13 / `3d409e9ac5f72bf98b69cccd640aa8b944d39f3b649fb14c05552f4d62edb208` | 0.632876813 / 14 | 0.307841033 / 2 | [1, 1] | tail_success @ 27 (elapsed 27); tail_success @ 26 (elapsed 26) | False |
| B | 0 / `ca8e2768beec8b4ec06367a931f9661a403bd5637f41e639423fd465251c1308` | 0.455920994 / 9 | 0.343710423 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 1.10519412 / 1.1051941; goal-direction term -0.232676833; squared-error term 1.33787094; algebra residual 0; saved-minus-float64 1.86902458e-08.
Mean squared error energy 29475.4825 = common 17701.1479 + specific 11774.3346; coordinate MSE 0.391627903; energy identity residual 0.

### pusht / dinowm_noprop / source 23 (WM-DIAG0-A2-v1:pusht:root-023)

Original stratum: loss; action-choice changed: True; O0−P0: -100.000 pp. Source `5d306bc38e0417e90f143a8b4aa2213fc115a3dd084ac4a74ee3ac35699eacc3`; accepted output seal `e30bdccf3220c8957b6e138e6ea65195f1dcaa50068530656f60067fd0e3f67d`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `f60647e4c9b69e12ef22bfb21fd346fa082e523a22a9fa111b66d0ea0276c4a5` | 0.857242167 / 1 | 0.514228523 / 6 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| O0 | 10 / `540365c5c51268d53ddd695ae8d7faa74922bc44409465d2b504f268e5fc39c0` | 1.01387823 / 11 | 0.428058863 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `639f916885cd479bd1014e40dd6879eb676749d6fdddd07f2a157797fb6d4315` | 0.89386785 / 7 | 0.492830843 / 5 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 1 / `f60647e4c9b69e12ef22bfb21fd346fa082e523a22a9fa111b66d0ea0276c4a5` | 0.857242167 / 1 | 0.514228523 / 6 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| B | 5 / `880100632b6d4e3c67e5cfe95d1e97fbd99b958a931ec96e78343d5d96f290ad` | 0.8921296 / 5 | 0.491721004 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0.242805719 / 0.242805662; goal-direction term 0.244636025; squared-error term -0.00183036351; algebra residual 3.33066907e-16; saved-minus-float64 5.77749369e-08.
Mean squared error energy 76151.9991 = common 53609.936 + specific 22542.0631; coordinate MSE 1.01179846; energy identity residual 0.

### pusht / dinowm_noprop / source 24 (WM-DIAG0-A2-v1:pusht:root-024)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `6cc3f80cf25294875a1d7888785fe8c0e7be07a6e881818b415fb2c0ab25a058`; accepted output seal `3244fdbd802753a867c05f5b32e8c4338d2922df4afe3add5ec2090708db5d02`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `82204be2b37271a4bc95757436513f574bf6e90c0ca03d5a1c3701ea97e276a6` | 0.328352213 / 1 | 0.159906313 / 10 | [1, 1] | tail_success @ 47 (elapsed 47); tail_success @ 48 (elapsed 48) | False |
| O0 | 0 / `6ec9388f07bd054be9d71b48d094be7f5c31d9ceb578e01e1961c7c73b813e3b` | 0.332434744 / 9 | 0.109084859 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `6ec9388f07bd054be9d71b48d094be7f5c31d9ceb578e01e1961c7c73b813e3b` | 0.332434744 / 9 | 0.109084859 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| A | 0 / `6ec9388f07bd054be9d71b48d094be7f5c31d9ceb578e01e1961c7c73b813e3b` | 0.332434744 / 9 | 0.109084859 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| B | 13 / `58b4b18b2a130c96ef3fdf61d8d8bb0ba26415ffe9d878d6efefdde7a7f66074` | 0.442010045 / 14 | 0.123179093 / 2 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |

Selected-pair ordering error (saved / float64): 0.0549039841 / 0.0549039992; goal-direction term 0.0758902053; squared-error term -0.020986206; algebra residual 8.32667268e-17; saved-minus-float64 -1.51771022e-08.
Mean squared error energy 27419.3781 = common 23194.4069 + specific 4224.97118; coordinate MSE 0.364309339; energy identity residual 0.

### pusht / dinowm_noprop / source 25 (WM-DIAG0-A2-v1:pusht:root-025)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `b3a354f177aec535ad0cd5ed3669f35956c541f870521df9afb4395047121941`; accepted output seal `d8e18234bef4e690b170b985e4ccae77e1a50a05a677742f322b18862b036cb5`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `6152ded58353d57b00654a221a532a2b8322e8067ed96a63cd322974c5c95792` | 0.498266101 / 1 | 0.253368497 / 11 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| O0 | 2 / `ef928827848dbf4740d6c1a88ede6f59595f35185bc4204bcd8bc61c1020cd3a` | 0.500057638 / 3 | 0.172980815 / 1 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| native | 0 / `c1ed7354db6d5734c936ffe2d82b34d973df04236538551e7a99214dc0f02bd2` | 0.499803066 / 2 | 0.187050253 / 6 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| A | 6 / `4074fae0b2ba09420e03ab875124f974abcfe1a87acdb7a7648723dd70a2e535` | 0.501610696 / 7 | 0.276343524 / 12 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| B | 8 / `cf0ea0fac507094c90fe77a49f16c6ed8198ec79496d4f5a1cf32938084563c3` | 0.502034783 / 9 | 0.178533792 / 2 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |

Selected-pair ordering error (saved / float64): 0.0821792185 / 0.0821792362; goal-direction term 0.0857442346; squared-error term -0.00356499838; algebra residual 1.66533454e-16; saved-minus-float64 -1.77171443e-08.
Mean squared error energy 44230.8496 = common 38234.1398 + specific 5996.70977; coordinate MSE 0.587676041; energy identity residual 0.

### pusht / dinowm_noprop / source 26 (WM-DIAG0-A2-v1:pusht:root-026)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `23d1ea2c0648c2c99e90c2908e15996afa8a65763afc6b87d12a7f83badc2d60`; accepted output seal `581bb1deb4e6efac3dd8418fceed1695100a2b73f9b16072129630873c535174`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `d1e24264523e5637b581d4d0ab4f87c6ad1689024ecad834e30f48c7e12a79ae` | 0.691302538 / 1 | 0.290636003 / 3 | [1, 1] | tail_success @ 49 (elapsed 49); tail_success @ 26 (elapsed 26) | False |
| O0 | 6 / `3ac994c71831a4bf82d4dfba8799f8e353f38fd969a711f90433dd8fc49910d1` | 0.701150477 / 6 | 0.176478431 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| native | 0 / `9bd430dabd39e7fb43203521d8ae8cc870cacaf8a98e921ed1c812313fd63642` | 0.717518747 / 9 | 0.460525453 / 11 | [1, 0] | tail_success @ 50 (elapsed 50); failure @ None (elapsed 50) | False |
| A | 5 / `91cf300e3403465ba65ef4d85a084fefe06cbdb23d28b7560599b97f7eefde30` | 0.70001471 / 5 | 0.336040258 / 5 | [1, 1] | tail_success @ 50 (elapsed 50); tail_success @ 49 (elapsed 49) | False |
| B | 6 / `3ac994c71831a4bf82d4dfba8799f8e353f38fd969a711f90433dd8fc49910d1` | 0.701150477 / 6 | 0.176478431 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |

Selected-pair ordering error (saved / float64): 0.124005511 / 0.124005483; goal-direction term 0.21978296; squared-error term -0.0957774762; algebra residual -1.66533454e-16; saved-minus-float64 2.80009471e-08.
Mean squared error energy 66032.9351 = common 46514.9281 + specific 19518.007; coordinate MSE 0.877350859; energy identity residual 1.45519152e-11.

### pusht / dinowm_noprop / source 27 (WM-DIAG0-A2-v1:pusht:root-027)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `57c174b634b96b57bd5b834d8587d347eae3ea452b505b196ff0fc2b3f32ffb8`; accepted output seal `2c85382da97ea8c0b2d9ce1bffb7c035b2623740add21633177ff17a598e12ee`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `cdd42bc29d58b01eace009f123b4cf23dd60ed1a6f9a46df9c4e8af957974414` | 0.897635102 / 1 | 0.692096055 / 12 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| O0 | 7 / `ca0f0046909d5f6a1662de544159606656895e83b8c61e9713dacfc25dde7aca` | 0.911397278 / 7 | 0.326675355 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `5647417e60695525357e7b6f3b3d74a3e59ddda7cba1e484a4b59c227c1d9f18` | 0.928078532 / 9 | 0.455912322 / 5 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| A | 6 / `029849ac2bcda7acfee61efbcbff2e142690ab29e8394ca0c18c086f68c71dae` | 0.910429657 / 6 | 0.581369817 / 9 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| B | 3 / `a8d7c20fe04214525859d4fd5a35f5b8c491bde321d1868e787ed4566fabd044` | 0.90558672 / 3 | 0.386964589 / 3 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 0.379182875 / 0.379182732; goal-direction term 0.678205604; squared-error term -0.299022872; algebra residual 0; saved-minus-float64 1.43288668e-07.
Mean squared error energy 72838.6832 = common 57669.1138 + specific 15169.5695; coordinate MSE 0.967775872; energy identity residual 1.45519152e-11.

### pusht / dinowm_noprop / source 28 (WM-DIAG0-A2-v1:pusht:root-028)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `de3ba4db5e45cebc542aed121e7c65fd6afba7abc0e503d1889d285d44977778`; accepted output seal `a1e7d0f0a6974c50f248fa0ae4e791cc5ab58be173fafdcc285ac8f415736c35`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `8a1383ab400f5917be80574af597953fd02fc4e6c2fad2d6721bb3ec1218358b` | 0.29508695 / 1 | 0.0707240626 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| O0 | 1 / `8a1383ab400f5917be80574af597953fd02fc4e6c2fad2d6721bb3ec1218358b` | 0.29508695 / 1 | 0.0707240626 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| native | 0 / `7c2ab4eb38cc6162eeb36df1a420e7315d3037e0ae738a0b18c7944da9f04d62` | 0.297177345 / 9 | 0.108120963 / 9 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| A | 9 / `cc0c9f8e0ad03cb9b806c634656f2620102e9235664bb5fbff2eebb16b971c24` | 0.314347982 / 10 | 0.0999964476 / 7 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| B | 2 / `b75ab63b5d0e909034bd3312ec4b14d37c4ada2966c53375e52434544b94200e` | 0.295984119 / 2 | 0.112348765 / 10 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 34269.5151 = common 24766.984 + specific 9502.53104; coordinate MSE 0.455324127; energy identity residual -7.27595761e-12.

### pusht / dinowm_noprop / source 29 (WM-DIAG0-A2-v1:pusht:root-029)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `2c26572eb66d81044153612f6f65f1d19418bfd48b2b61dcdafd81142e003337`; accepted output seal `ddc968c9e40ba010426d611abef97f4ee50986c72528fa588421eb219330da99`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `165951c7c43c8c6a000d0d3f8c8e28849d72be97e4aeffe5fe024fde6d3c901b` | 0.552027404 / 1 | 0.387509644 / 5 | [1, 0] | tail_success @ 49 (elapsed 49); failure @ None (elapsed 50) | False |
| O0 | 7 / `3ad61e411f3e711d2716e0bae4954b24e46d35e463c47806ac96b8ccaa5b1572` | 0.554448962 / 8 | 0.366657734 / 1 | [1, 0] | tail_success @ 49 (elapsed 49); failure @ None (elapsed 50) | False |
| native | 0 / `3e51a24641434525f965b6a9ffb0a57ad0252755f26785cfb404ccbef134f86c` | 0.552815497 / 3 | 0.395240098 / 6 | [1, 1] | tail_success @ 49 (elapsed 49); tail_success @ 50 (elapsed 50) | False |
| A | 7 / `3ad61e411f3e711d2716e0bae4954b24e46d35e463c47806ac96b8ccaa5b1572` | 0.554448962 / 8 | 0.366657734 / 1 | [1, 0] | tail_success @ 49 (elapsed 49); failure @ None (elapsed 50) | False |
| B | 6 / `4c1e2a9298cacc109ff010c2287255921fccee87962c8b5906758a82382b3159` | 0.553895295 / 7 | 0.380390882 / 2 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 49 (elapsed 49) | False |

Selected-pair ordering error (saved / float64): 0.023273468 / 0.0232734639; goal-direction term 0.00859644417; squared-error term 0.0146770197; algebra residual -5.55111512e-17; saved-minus-float64 4.10076068e-09.
Mean squared error energy 53004.9031 = common 42177.0379 + specific 10827.8653; coordinate MSE 0.704253071; energy identity residual 0.

### pusht / dinowm_noprop / source 30 (WM-DIAG0-A2-v1:pusht:root-030)

Original stratum: loss; action-choice changed: True; O0−P0: -100.000 pp. Source `f8697cc45565d4a4718fe204412efab20e25a46eb0dbf6cf81d699993f8d1651`; accepted output seal `4489eb7fd0a8da57092b0349cc842efa8fec0e1dc09aad4cd2a47b9388f878b5`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `ec3355958c4d8ecfd97d5a1d0f38b5460e65d4903a9ab52ff928426de9c171ab` | 1.02578962 / 1 | 1.44999278 / 4 | [1, 1] | prefix_success @ 15 (elapsed 15); prefix_success @ 15 (elapsed 15) | True |
| O0 | 5 / `29898c5edcd6b542b7d07e8e169e9255d8112eb7bdac95e24361d13cd3736bf8` | 1.03440368 / 5 | 0.657538891 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `6888ad0ac16f482dccf9045a71cd1089e1ed7b1b9da0b6197841ea610ab02d1d` | 1.05171382 / 9 | 1.01631105 / 2 | [0, 1] | failure @ None (elapsed 50); tail_success @ 31 (elapsed 31) | False |
| A | 4 / `06004e529a768db481a071bde18299cedd9fefc1d89b2f7103ee7b663fe074e3` | 1.03386104 / 4 | 1.44251728 / 3 | [1, 0] | tail_success @ 28 (elapsed 28); failure @ None (elapsed 50) | False |
| B | 5 / `29898c5edcd6b542b7d07e8e169e9255d8112eb7bdac95e24361d13cd3736bf8` | 1.03440368 / 5 | 0.657538891 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0.801067948 / 0.801067926; goal-direction term 1.14774364; squared-error term -0.346675714; algebra residual -2.22044605e-16; saved-minus-float64 2.23147772e-08.
Mean squared error energy 81199.8786 = common 51216.7518 + specific 29983.1268; coordinate MSE 1.07886744; energy identity residual 0.

### pusht / dinowm_noprop / source 31 (WM-DIAG0-A2-v1:pusht:root-031)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `4fe71c501bef610a297625bec890d8e0d3e63fb78e8f4b82cfcf2cc94a8fcb67`; accepted output seal `fd6891879b02daf69ee54e6ec95ab45e58184aeb56647e37ce1a5dd47baa0459`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `a5a19a84c0cda91622d4f27f794e6bb92cc1799d7cb691798f5c3cd0761f4dbb` | 0.805721343 / 1 | 0.242474824 / 1 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 48 (elapsed 48) | False |
| O0 | 1 / `a5a19a84c0cda91622d4f27f794e6bb92cc1799d7cb691798f5c3cd0761f4dbb` | 0.805721343 / 1 | 0.242474824 / 1 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 48 (elapsed 48) | False |
| native | 0 / `69eca17eddb6009777d817f594045f202a3eba28e8bf25150eed39984b5c5a12` | 0.808056951 / 5 | 0.569682777 / 7 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 1 / `a5a19a84c0cda91622d4f27f794e6bb92cc1799d7cb691798f5c3cd0761f4dbb` | 0.805721343 / 1 | 0.242474824 / 1 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 48 (elapsed 48) | False |
| B | 5 / `02b420f7ffaafb5aa9bceadcbfde6331208f5a84e8d417ceff4561d61eb7c0db` | 0.808423936 / 6 | 0.566022515 / 5 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 63856.0017 = common 47981.4666 + specific 15874.5351; coordinate MSE 0.848426893; energy identity residual 0.

### reacher / lewm / source 0 (WM-DIAG0-A2-v1:reacher:root-000)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `b6dfbc79ca15f08b13720f9545d3933d2b6e3b5441dcae025cd7646a8345a198`; accepted output seal `91a92fa2b8172353cb766c31169028ab1079611113120a4c5a3f4c168e3ccbc9`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `7b2ce0f8fde3c8625d2b01ff50d7b86a81fd53597728f6476b84358066ca6c37` | 19.7563362 / 1 | 1.11186433 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| O0 | 1 / `7b2ce0f8fde3c8625d2b01ff50d7b86a81fd53597728f6476b84358066ca6c37` | 19.7563362 / 1 | 1.11186433 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| native | 0 / `510ca52ddfe2332971524997ae7a6aad23507d1010745a8ad605cbf5bdc5322a` | 19.8894691 / 9 | 3.11181355 / 7 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| A | 0 / `510ca52ddfe2332971524997ae7a6aad23507d1010745a8ad605cbf5bdc5322a` | 19.8894691 / 9 | 3.11181355 / 7 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| B | 1 / `7b2ce0f8fde3c8625d2b01ff50d7b86a81fd53597728f6476b84358066ca6c37` | 19.7563362 / 1 | 1.11186433 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 40.0404471 = common 17.9457895 + specific 22.0946575; coordinate MSE 0.208543995; energy identity residual 0.

### reacher / lewm / source 1 (WM-DIAG0-A2-v1:reacher:root-001)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `3cf99ba3c3083377482dc5de3dd54f3802236c57f16bd2d0cf22494783578310`; accepted output seal `2dfbab768d515b05c0739534c26ae59f2bb6f31e751589dbbca7765f51fd2ed0`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `be871f41d42c536e1a6583ce3e3d560e06fdc949d139a3ac1a251129eff7bd8d` | 26.8633919 / 1 | 1.97287083 / 2 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| O0 | 4 / `94a57dbc422e75810392ddca4bdea9847f14d9f1a6282d9caa9acc27df32f55d` | 27.0225544 / 4 | 1.09015512 / 1 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| native | 0 / `0ac645066186982580a24693aadd8b6701b6da163db46483f013f590585ca5ac` | 27.290556 / 9 | 22.9364738 / 12 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 27 (elapsed 27) | False |
| A | 3 / `e4aec5fd51852412889b46fef6c76c1d179eedbc33aebd3a6226d826d2d7e771` | 27.0035343 / 3 | 4.03880358 / 6 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| B | 8 / `e9813dd15d13e4777e794fca4a29fef5c0c56f81c8b27a553ec5aafab467ff30` | 27.2506905 / 8 | 3.65515089 / 4 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |

Selected-pair ordering error (saved / float64): 1.04187822 / 1.04187627; goal-direction term 1.46454247; squared-error term -0.422666195; algebra residual 1.11022302e-15; saved-minus-float64 1.94938353e-06.
Mean squared error energy 62.3063906 = common 28.5332331 + specific 33.7731575; coordinate MSE 0.324512451; energy identity residual 0.

### reacher / lewm / source 2 (WM-DIAG0-A2-v1:reacher:root-002)

Original stratum: gain; action-choice changed: True; O0−P0: +100.000 pp. Source `de5001f421c5df998221b1b2c33b51857bb57d33c7fe4919a96f4714b8d801a4`; accepted output seal `69cbd672dd980900b729b9079b4a1fcd50f867e8ff41f5ce5ac24ae28b8bdf42`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `440fd1af75fbb66c1c3685828af43cda147f1cef140a6e646b5ff097060ab6e3` | 16.9846802 / 1 | 47.5814667 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 12 / `0d7b1e40ae86e14ec2117f3f5b26520a69c36fe296a4b93053ee7452e74bb9b0` | 186.367371 / 13 | 2.61740613 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `6e3eea56f23e0ac1799df7b6759a8c7bf151d816daa08ec54eaa95a927ea8fa5` | 17.2971725 / 7 | 61.4287491 / 9 | [0, 1] | failure @ None (elapsed 50); tail_success @ 30 (elapsed 30) | False |
| A | 10 / `6d5373a68c993a24376744edc3068cb2d4bc5cb8cbcce9fcb319c548ec08418a` | 78.5976105 / 11 | 31.6126213 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 2 / `b8b03d18bd54ed6cd4ec5b06879ddcc7910d5d31e3edb9c41d879afad674907e` | 17.0802288 / 2 | 45.4428635 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 214.346751 / 214.346755; goal-direction term 89.3038187; squared-error term 125.042936; algebra residual -5.68434189e-14; saved-minus-float64 -3.6361383e-06.
Mean squared error energy 76.9155089 = common 50.3008935 + specific 26.6146153; coordinate MSE 0.400601609; energy identity residual 1.42108547e-14.

### reacher / lewm / source 3 (WM-DIAG0-A2-v1:reacher:root-003)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `a9af9a3738bbddfddeb8e3cf6eede0b6423a8e92a3d1aa6f6f7fc105556f2a3b`; accepted output seal `7a49fd9675300a1caa7b6a04ba5058a451a92b7b4fff112e57cf1636efa854cb`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `a7a91466cc7e1f82f8bec5e976ba8f6584fe73bd150db7608396435885d70674` | 11.7906475 / 1 | 29.7165108 / 8 | [1, 1] | tail_success @ 29 (elapsed 29); tail_success @ 28 (elapsed 28) | False |
| O0 | 8 / `1fb5bb713f0e72cc270f77f7f54b09075bfd535670fb4ed141d255e5209aeeb9` | 11.9580479 / 9 | 2.05574608 / 1 | [1, 1] | prefix_success @ 18 (elapsed 18); prefix_success @ 18 (elapsed 18) | True |
| native | 0 / `ad1f65ad51838d63e346293c5c658c840c3edf42be3dfab8092aea6839032004` | 11.8698883 / 3 | 30.4342155 / 10 | [1, 1] | tail_success @ 30 (elapsed 30); tail_success @ 30 (elapsed 30) | False |
| A | 6 / `440d6b315a47947e616908b3e94d8fa4719a487fdfb09abae0108a929f424bdc` | 11.9293499 / 7 | 28.4550934 / 7 | [1, 1] | tail_success @ 35 (elapsed 35); tail_success @ 28 (elapsed 28) | False |
| B | 11 / `e2f7f94f297c48063d1d1961fca20b6475d0bb3ff09c2616781a7a90422a2468` | 110.277115 / 12 | 2.9581368 / 3 | [1, 1] | prefix_success @ 13 (elapsed 13); prefix_success @ 13 (elapsed 13) | True |

Selected-pair ordering error (saved / float64): 27.8281651 / 27.8281648; goal-direction term 59.9910196; squared-error term -32.1628547; algebra residual -3.55271368e-15; saved-minus-float64 2.20183207e-07.
Mean squared error energy 53.6040599 = common 20.5938295 + specific 33.0102304; coordinate MSE 0.279187812; energy identity residual 0.

### reacher / lewm / source 4 (WM-DIAG0-A2-v1:reacher:root-004)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `5c352bac29d9f5911bd1bbe227871d357fdea401fdd3a503273a18051bef347e`; accepted output seal `09ae668a7870e1c883dde3823dd76f7f623f244065d5bd3d1f8d09452ab13a58`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `6dd4bb89cd4c28fb69d8f31c9c58367ecba532df519749b5bf618437b92abf3b` | 17.5555878 / 1 | 75.1041412 / 12 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 12 / `d855e6bf33f4ecaf2485e9b12596edbc6211842cbb19fb790e04a853acb20929` | 112.663292 / 13 | 3.42371893 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `4c8f23e1b14ab4bab981e55e0ac1554bee25d2b25a718d55502e68656498dc6b` | 18.0327396 / 9 | 46.9231606 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 11 / `7d963cbe45bb4a24dcca413779d5f7222d0e4a3c5e2892b1ce7d76a01c3a6743` | 69.2017288 / 12 | 3.79958487 / 2 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 8 / `e9881e31122caae155a85ffceec8acfba6f1cb27339e4e6de3e971144ba42bd7` | 17.8853779 / 8 | 45.4702301 / 5 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 166.788126 / 166.788126; goal-direction term 133.443648; squared-error term 33.3444777; algebra residual 0; saved-minus-float64 5.31464565e-07.
Mean squared error energy 78.0194217 = common 55.1099382 + specific 22.9094835; coordinate MSE 0.406351155; energy identity residual 0.

### reacher / lewm / source 5 (WM-DIAG0-A2-v1:reacher:root-005)

Original stratum: gain; action-choice changed: True; O0−P0: +100.000 pp. Source `21c130798e2a9d0fdc5cb128905843c935eee44d68a77966914793cd772acf6e`; accepted output seal `7419578cc42a26acbf1108a84e9717e848aa9bebcebd41ea54bdb0ba2b9acba1`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `801da4baa9e07d1d73b1da5e1f7772e0e3f570b7705d786ab072168a4b37bbac` | 20.9075527 / 1 | 10.0851393 / 9 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 3 / `18e0cbe58321f84b41f9008f57086c3a307c41327fd18e963f8cf057a15a68fa` | 20.9651699 / 3 | 0.249491796 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `2b35eaea2e833b2b76994f6c4669eebe64c2497818a8ad43e6ab098813d0b523` | 21.7128716 / 9 | 4.57250214 / 8 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| A | 6 / `881a488c4f99fad3e27bc20fec3deddceb724f60d32e4d7e93712f3310f209b5` | 21.5017433 / 6 | 1.32030582 / 2 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| B | 3 / `18e0cbe58321f84b41f9008f57086c3a307c41327fd18e963f8cf057a15a68fa` | 20.9651699 / 3 | 0.249491796 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 9.89326467 / 9.89326549; goal-direction term 14.668876; squared-error term -4.77561047; algebra residual 0; saved-minus-float64 -8.26340305e-07.
Mean squared error energy 29.3002161 = common 18.47905 + specific 10.8211661; coordinate MSE 0.152605292; energy identity residual -7.10542736e-15.

### reacher / lewm / source 6 (WM-DIAG0-A2-v1:reacher:root-006)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `723b1d45ca4a02b99b63e6b111f101cc131a38b5bc0e9d6f1b8a5cb97a06a06d`; accepted output seal `fad3cd01c8d13aaefe80382631f171d35d76b1b8105339d77eedfc19265b449a`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `bdd3e61565bdf7d403a40cbd418093b6e4aabe1b6bf9573cbeceeb417c539dbf` | 13.1161232 / 1 | 37.8150406 / 10 | [1, 0] | tail_success @ 37 (elapsed 37); failure @ None (elapsed 50) | False |
| O0 | 3 / `2b71a8505599b0dcdd70ea34604cc4c3864eebd9e5a99695290fa855e6faed8b` | 13.1862144 / 3 | 1.69708538 / 1 | [1, 1] | prefix_success @ 12 (elapsed 12); prefix_success @ 12 (elapsed 12) | True |
| native | 0 / `8d5f262ba3c82f562a0c1f769c3671063029b284447db75f582d95deffcf475a` | 13.6965103 / 9 | 8.29265881 / 4 | [1, 0] | tail_success @ 30 (elapsed 30); failure @ None (elapsed 50) | False |
| A | 7 / `f04e4cd94e3f2c6f91eb23297f168202bc46a996cbc8c21e6e6a2c588ba3b1c8` | 13.4466496 / 7 | 2.08712482 / 3 | [1, 1] | prefix_success @ 13 (elapsed 13); prefix_success @ 13 (elapsed 13) | True |
| B | 0 / `8d5f262ba3c82f562a0c1f769c3671063029b284447db75f582d95deffcf475a` | 13.6965103 / 9 | 8.29265881 / 4 | [1, 0] | tail_success @ 30 (elapsed 30); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 36.1880465 / 36.1880485; goal-direction term 57.9621717; squared-error term -21.7741232; algebra residual -7.10542736e-15; saved-minus-float64 -1.99541183e-06.
Mean squared error energy 28.5698023 = common 16.9122099 + specific 11.6575924; coordinate MSE 0.148801053; energy identity residual -3.55271368e-15.

### reacher / lewm / source 7 (WM-DIAG0-A2-v1:reacher:root-007)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `6a6b38fccf114311b98b21b24629749e9c1e78f48102bad7958fbaa6b76fd075`; accepted output seal `ae24260cc14c29a9a0fdaf5c1d1ebe3235d7717e1cad48db8fd3b37d2741ae88`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `735a45a0978b1078761ba1de9b9025efd10aec263a694a411a7e05b0239f08f2` | 22.2803383 / 1 | 8.83384895 / 10 | [1, 1] | tail_success @ 26 (elapsed 26); tail_success @ 48 (elapsed 48) | False |
| O0 | 3 / `7486c4aba122484f9f6d336466d8a3029c70cb202c4d72d9a88efbdbab120c9e` | 22.4387589 / 3 | 1.63281322 / 1 | [1, 1] | prefix_success @ 5 (elapsed 5); prefix_success @ 5 (elapsed 5) | True |
| native | 0 / `755b38faf7ab47c4668bd6fa959070748696824bef8a3bc5d5418ee90a9c5ad3` | 22.7928276 / 9 | 1.77972412 / 2 | [1, 1] | prefix_success @ 5 (elapsed 5); prefix_success @ 5 (elapsed 5) | True |
| A | 0 / `755b38faf7ab47c4668bd6fa959070748696824bef8a3bc5d5418ee90a9c5ad3` | 22.7928276 / 9 | 1.77972412 / 2 | [1, 1] | prefix_success @ 5 (elapsed 5); prefix_success @ 5 (elapsed 5) | True |
| B | 10 / `c2360a49318f5ab2b6c86348383c5ec3a92d61023392f44a4474d4fe271ff5b1` | 90.8534393 / 11 | 2.81934333 / 5 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |

Selected-pair ordering error (saved / float64): 7.3594563 / 7.35945372; goal-direction term 16.8215366; squared-error term -9.46208289; algebra residual -3.55271368e-15; saved-minus-float64 2.57769885e-06.
Mean squared error energy 76.09991 = common 31.8374704 + specific 44.2624396; coordinate MSE 0.396353698; energy identity residual 0.

### reacher / lewm / source 8 (WM-DIAG0-A2-v1:reacher:root-008)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `8d944f312bfaf400e88776c356de4eead5b6b13cecc644adbf65a2f3bd26f6bb`; accepted output seal `93e20c0fbe51e002509cfd9388f4216dc9966052cca8f231b13b195710e696c5`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `aedc746a53c05c96c45c9a74374a4f12075a959e65c421b94598764f93ce4afc` | 37.0032768 / 1 | 2.33741045 / 6 | [1, 1] | prefix_success @ 17 (elapsed 17); prefix_success @ 17 (elapsed 17) | True |
| O0 | 3 / `ae4f4717d12681c63f38ea5aa39cc7e9506d3fd77df8accb16f147ba378b5aa5` | 37.4869881 / 4 | 0.0504545532 / 1 | [1, 1] | prefix_success @ 16 (elapsed 16); prefix_success @ 16 (elapsed 16) | True |
| native | 0 / `5d82c89a244f3ed8131fd2af6f144c3b3a25966ece6a879a97f5a0def39d69b7` | 37.4359894 / 3 | 2.62246037 / 8 | [1, 1] | prefix_success @ 15 (elapsed 15); prefix_success @ 15 (elapsed 15) | True |
| A | 6 / `761fd3868d4e9dae908248759cc5f7fcb1176dec87ba08c50b5ff83af0f3e1e1` | 37.6973267 / 7 | 3.33103371 / 10 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| B | 2 / `bc069fa80d8b1f2f32e997aabb82d11cf20e312be1ac62e2def80a050463f632` | 37.1282845 / 2 | 0.880534112 / 2 | [1, 1] | prefix_success @ 16 (elapsed 16); prefix_success @ 16 (elapsed 16) | True |

Selected-pair ordering error (saved / float64): 2.77066714 / 2.77066847; goal-direction term 5.13905611; squared-error term -2.36838764; algebra residual 1.77635684e-15; saved-minus-float64 -1.33535252e-06.
Mean squared error energy 46.8012441 = common 29.4536815 + specific 17.3475627; coordinate MSE 0.24375648; energy identity residual -7.10542736e-15.

### reacher / lewm / source 9 (WM-DIAG0-A2-v1:reacher:root-009)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `c9796d9bdda0f716d01b8fa17bab2fc1b4b97c25726501f2f7aceec4f080c0b1`; accepted output seal `638108bc0b96d1a9be89b02751814ad2b6a017a7e2968cfb20c9b954b5ca0183`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `6815f3ab6bc5eb537a223ffbb1382657993d038be8059e4e7352c4b419408595` | 24.3157463 / 1 | 3.26140213 / 7 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| O0 | 2 / `c8a319bec62e57b0e9c2d5ad8c1d2c09fb157f789d82cbdd79094d26daf200af` | 25.643055 / 2 | 0.652633905 / 1 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| native | 0 / `8f429c6ad8716e405e85ac670067edc18a20a59ba166302aecc29cc58769bf70` | 25.9126911 / 9 | 2.5037322 / 6 | [1, 1] | prefix_success @ 20 (elapsed 20); prefix_success @ 20 (elapsed 20) | True |
| A | 3 / `6a16358749e52bc93395913c88b6573819babd46377bdb9c78d1a282342e89bf` | 25.6552582 / 3 | 2.23072338 / 4 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| B | 8 / `1c898733c871351091034d7ff3b18a5ccff80b272ed11cc56b1f2d6530581107` | 25.8772507 / 8 | 1.21930587 / 3 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |

Selected-pair ordering error (saved / float64): 3.93607688 / 3.93607839; goal-direction term 6.69753273; squared-error term -2.76145434; algebra residual -2.22044605e-15; saved-minus-float64 -1.51237876e-06.
Mean squared error energy 62.9741829 = common 27.5520656 + specific 35.4221173; coordinate MSE 0.327990536; energy identity residual 0.

### reacher / lewm / source 10 (WM-DIAG0-A2-v1:reacher:root-010)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `5ec08c443971f68d50c8dbd18c2cf28851f4124610230888bec900c6dc348f42`; accepted output seal `0fb098dd333c74e0a6af27d4b0c3dfc6ae9d0afb843b151fb6c7508339de4ec9`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `c22e1e9a6c58299f4f454a426f3998aa48fc62986e588c0177cbaca0a28bd28a` | 14.8054638 / 1 | 2.13288498 / 1 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| O0 | 1 / `c22e1e9a6c58299f4f454a426f3998aa48fc62986e588c0177cbaca0a28bd28a` | 14.8054638 / 1 | 2.13288498 / 1 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| native | 0 / `3633cb666da99e9e4a3102e8de64fcbec67be64fe0d1801d1b3bc1cc4c735a92` | 15.2350063 / 7 | 55.8291245 / 6 | [1, 1] | tail_success @ 33 (elapsed 33); tail_success @ 35 (elapsed 35) | False |
| A | 4 / `afd29f6320aa63bdce42e4e52cf7d34096f42f0a8d02d19b8f8bb7a4238b1ec1` | 15.175724 / 4 | 54.6737061 / 5 | [1, 1] | tail_success @ 28 (elapsed 28); tail_success @ 29 (elapsed 29) | False |
| B | 3 / `43b8491bbaf81fffab22a212b54c75a318a2c3f53dfdfb671a93e8f32a39df5b` | 15.0371122 / 3 | 50.3855629 / 3 | [1, 1] | tail_success @ 33 (elapsed 33); tail_success @ 31 (elapsed 31) | False |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 77.6238742 = common 38.1442922 + specific 39.479582; coordinate MSE 0.404291012; energy identity residual 0.

### reacher / lewm / source 11 (WM-DIAG0-A2-v1:reacher:root-011)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `d7e248d0e3b2a1d25563c5e2f3f3e1a9ae112ef565402ea14bb630fc3f48dbd1`; accepted output seal `c6de07176c2dae25f2d711a8ef9664196ac895c8649a81b5dba0b78879ccbddb`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `ef3654bde585911235140b8868ce09c8555efab868be0ab90dc36dcb743823d3` | 28.0153961 / 1 | 80.925354 / 11 | [1, 1] | tail_success @ 50 (elapsed 50); tail_success @ 49 (elapsed 49) | False |
| O0 | 2 / `18cdc67229140d0076758addee927d8f91e23d6c60bed1a80935d9ee671854fb` | 28.157896 / 2 | 0.281951785 / 1 | [1, 1] | prefix_success @ 20 (elapsed 20); prefix_success @ 20 (elapsed 20) | True |
| native | 0 / `e69f592fef0a739320bde161f8994d20e28895c2a06c5934a67c8a9c73908e8d` | 29.1273327 / 9 | 1.29785275 / 3 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| A | 2 / `18cdc67229140d0076758addee927d8f91e23d6c60bed1a80935d9ee671854fb` | 28.157896 / 2 | 0.281951785 / 1 | [1, 1] | prefix_success @ 20 (elapsed 20); prefix_success @ 20 (elapsed 20) | True |
| B | 2 / `18cdc67229140d0076758addee927d8f91e23d6c60bed1a80935d9ee671854fb` | 28.157896 / 2 | 0.281951785 / 1 | [1, 1] | prefix_success @ 20 (elapsed 20); prefix_success @ 20 (elapsed 20) | True |

Selected-pair ordering error (saved / float64): 80.7859021 / 80.7859021; goal-direction term 149.067224; squared-error term -68.2813218; algebra residual 1.42108547e-14; saved-minus-float64 8.23125248e-08.
Mean squared error energy 44.1891673 = common 22.3849199 + specific 21.8042475; coordinate MSE 0.230151913; energy identity residual -7.10542736e-15.

### reacher / lewm / source 12 (WM-DIAG0-A2-v1:reacher:root-012)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `2a2fed292d9fb54728c7ea828e148f0f0f84f8c11ced8f9983277fc2d03afd62`; accepted output seal `ca49b97ba258f58b00b5be74e3af3935109b935d3af10b94bca0251c62132f9d`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `2abfe7ef46926720169a1080cd74c14153ac92baf645bb77bdcaec10e2c911cb` | 17.1534557 / 1 | 4.44647551 / 7 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| O0 | 8 / `6016ea9adf0a5c77745c5e51c08c8eaa5020396875cb546ff0de0ac00f1fbd1b` | 17.3168221 / 9 | 1.65922511 / 1 | [1, 1] | prefix_success @ 17 (elapsed 17); prefix_success @ 17 (elapsed 17) | True |
| native | 0 / `fde9240a7979d5f2d57a521a2df1fa3763641abb50529522492d69201ef26005` | 17.2367229 / 5 | 3.47049856 / 3 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| A | 3 / `3d6e2d33526cec8ad6d8035bdba5017570051fd96e634411b504f2c5d15bd847` | 17.1810589 / 3 | 5.60615492 / 8 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| B | 4 / `0726555d9413f08e47aa38a8da871d562e5afd1fa1967710abf49eec334f6525` | 17.2066002 / 4 | 3.58914971 / 4 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 2.95061672 / 2.9506178; goal-direction term 7.02023234; squared-error term -4.06961454; algebra residual -5.32907052e-15; saved-minus-float64 -1.08011626e-06.
Mean squared error energy 39.4541315 = common 18.900841 + specific 20.5532905; coordinate MSE 0.205490268; energy identity residual 0.

### reacher / lewm / source 13 (WM-DIAG0-A2-v1:reacher:root-013)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `aa37f1ad770a65638118b1f20ed442d135b73c74cd7bab52f6f4c44e3b345948`; accepted output seal `5000f9598a8ba18c776d2fc16626d67136e635b3e6550b4e634a467721195315`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `bdbf99ccc565fbeed68eb4cc5804f50d5964765d3cffce72c4062c29e2b9199f` | 15.5706062 / 1 | 2.700037 / 7 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| O0 | 9 / `357ec8e74b2f288d7308620990ddb9344ec9865784d41352fb3abf8766d6a978` | 38.7357445 / 10 | 1.0642792 / 1 | [1, 1] | prefix_success @ 18 (elapsed 18); prefix_success @ 18 (elapsed 18) | True |
| native | 0 / `8e13a1772d0fb6814a349ffbcfaad0ce446a648155d6eb7eb1baade3c45b0290` | 16.0378723 / 9 | 69.3762054 / 11 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 7 / `e533bd1bfff84f80d344ccd104a9499387b3727d0b2541eba284c46df48bc522` | 15.8092308 / 7 | 2.63261724 / 5 | [1, 1] | prefix_success @ 18 (elapsed 18); prefix_success @ 18 (elapsed 18) | True |
| B | 3 / `213804dd21b225b6adfddb2ccc69840e0cc63218cc2f00e8fcfc2dd6315fc03c` | 15.6561775 / 3 | 2.65640092 / 6 | [1, 1] | prefix_success @ 16 (elapsed 16); prefix_success @ 16 (elapsed 16) | True |

Selected-pair ordering error (saved / float64): 24.800896 / 24.8008958; goal-direction term 1.16999346; squared-error term 23.6309024; algebra residual -7.10542736e-15; saved-minus-float64 2.32798921e-07.
Mean squared error energy 54.6489042 = common 18.6366358 + specific 36.0122684; coordinate MSE 0.284629709; energy identity residual 0.

### reacher / lewm / source 14 (WM-DIAG0-A2-v1:reacher:root-014)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `ff6642580b55edc9021f94c71b367364656438a690a421e20002b4c1031a8628`; accepted output seal `7a5e54759aea46841c5b056766344c52501efa39e5d7b969da0d39974931cd12`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `51ec20ab5699f0c651239527a002ff0938db3c5f6f9713b264ac538b89f752eb` | 58.2380905 / 1 | 4.13162804 / 5 | [1, 1] | prefix_success @ 8 (elapsed 8); prefix_success @ 8 (elapsed 8) | True |
| O0 | 11 / `db219cce1d7612daaab837d2c7caaed7eb14a3ce2d7d3abd62afde401a58ee2c` | 105.721344 / 12 | 2.34851766 / 1 | [1, 1] | prefix_success @ 16 (elapsed 16); prefix_success @ 16 (elapsed 16) | True |
| native | 0 / `817a7bbb65ee97c6e11732ef9d5d78d7ab463a5c4c53232e955039a968cf35e4` | 58.3801422 / 2 | 48.0214539 / 13 | [1, 1] | tail_success @ 41 (elapsed 41); tail_success @ 37 (elapsed 37) | False |
| A | 4 / `1abcc4d11a7367a30e0621781be2c09cb6ca1fb224731b598b7bfb51c1328e0c` | 58.4989929 / 5 | 35.9829178 / 9 | [1, 1] | tail_success @ 41 (elapsed 41); tail_success @ 41 (elapsed 41) | False |
| B | 3 / `0eab18658298f66d6c2e17341b0b1507a595d4013090954355972796eae6cabb` | 58.4952888 / 4 | 27.9477978 / 7 | [1, 1] | tail_success @ 49 (elapsed 49); tail_success @ 46 (elapsed 46) | False |

Selected-pair ordering error (saved / float64): 49.2663639 / 49.2663651; goal-direction term -7.16971836; squared-error term 56.4360834; algebra residual 7.10542736e-15; saved-minus-float64 -1.21203279e-06.
Mean squared error energy 126.679172 = common 48.4152571 + specific 78.2639147; coordinate MSE 0.659787354; energy identity residual 0.

### reacher / lewm / source 15 (WM-DIAG0-A2-v1:reacher:root-015)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `6c083a9524d5e38cbca1578a70c8c6879473379222ff4f00be4c7e7e0571af79`; accepted output seal `878ecbfb7a5910e0750ef81cfe595dd63b5d7a438b5b85c02f6b577f2ab53547`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `5c831d4227192d08cb6722632f39eec004976f5a71cd97162187ccddb2eab5e6` | 19.3885136 / 1 | 14.8223248 / 8 | [1, 1] | tail_success @ 29 (elapsed 29); tail_success @ 50 (elapsed 50) | False |
| O0 | 15 / `f4768a6e304aff5f87447ea08c50159937063288a45f66b5e6593cf418941451` | 475.493896 / 16 | 2.60606551 / 1 | [1, 1] | prefix_success @ 3 (elapsed 3); prefix_success @ 3 (elapsed 3) | True |
| native | 0 / `9b63de170e27938c23eb86adbe82b1d3ffe1d6746a7f619244cc4301c8b8de1a` | 19.4694481 / 9 | 8.72764587 / 5 | [1, 1] | tail_success @ 26 (elapsed 26); tail_success @ 27 (elapsed 27) | False |
| A | 8 / `c9b9e20de95ecd076416009139b4b7cda3683f8f6d9c6134fdb00a8352519e5f` | 19.458292 / 8 | 18.8460789 / 10 | [0, 1] | failure @ None (elapsed 50); tail_success @ 37 (elapsed 37) | False |
| B | 3 / `fae854d98f7fb0f28765063a95a8fd0df3d871c475aab20fb3518b43815c23f7` | 19.3963947 / 3 | 8.23785973 / 4 | [1, 1] | tail_success @ 26 (elapsed 26); tail_success @ 27 (elapsed 27) | False |

Selected-pair ordering error (saved / float64): 468.321642 / 468.321651; goal-direction term 19.1875342; squared-error term 449.134117; algebra residual 5.68434189e-14; saved-minus-float64 -8.71988573e-06.
Mean squared error energy 63.0657968 = common 26.347018 + specific 36.7187788; coordinate MSE 0.328467692; energy identity residual 0.

### reacher / lewm / source 16 (WM-DIAG0-A2-v1:reacher:root-016)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `1b60a79a5d3a238753e88c2935f01af72e199e32552dd441ec50e98a5fd58ef4`; accepted output seal `ec6961cf0aeedafea765ead3b01e7c71dbf9f9c8b658fb7244f22f4337e278bc`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `e1d69a8b2baebe5999d6bdf3da495f6a3178a1715f5806253a32bebd3ead0348` | 21.7353134 / 1 | 2.77831721 / 3 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| O0 | 3 / `cb586486e06fe370860994ec0db2029e45633457c17155c18b7e7dc3193e1398` | 21.7815666 / 3 | 0.914141834 / 1 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| native | 0 / `8bf9895297121f212ea4aa634e4bdf338fdabdccce3e5fde28c148a25b1f428a` | 21.8190899 / 7 | 1.14281154 / 2 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| A | 7 / `7cb84f94f9d3d230118b15b30e5a4327c28ab5b7c7fc56be567d424dcab06149` | 21.8301239 / 8 | 6.16815853 / 9 | [1, 1] | prefix_success @ 13 (elapsed 13); prefix_success @ 13 (elapsed 13) | True |
| B | 3 / `cb586486e06fe370860994ec0db2029e45633457c17155c18b7e7dc3193e1398` | 21.7815666 / 3 | 0.914141834 / 1 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |

Selected-pair ordering error (saved / float64): 1.91042858 / 1.91042743; goal-direction term 3.16277564; squared-error term -1.25234821; algebra residual -8.8817842e-16; saved-minus-float64 1.15485608e-06.
Mean squared error energy 40.4837041 = common 20.1780246 + specific 20.3056795; coordinate MSE 0.210852626; energy identity residual -7.10542736e-15.

### reacher / lewm / source 17 (WM-DIAG0-A2-v1:reacher:root-017)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `4d4e04e089230a98aef52c748791d318752cdc1b63317b65bc696d966c35a3ad`; accepted output seal `c8da4fbfe33f5a99a26b1f1c9f54d1ba53b64cd9e9204b5ab630f75cbdf9ecaf`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `a84433c2b3242939d67072de8b396707ec407ad880e9eb47da5f6e77630c1c9c` | 25.0541916 / 1 | 35.221489 / 4 | [1, 0] | tail_success @ 27 (elapsed 27); failure @ None (elapsed 50) | False |
| O0 | 11 / `dd42159c7f48c908d1df4a4a0a59e98c96055cfa6fbf1146ea71981cbb9fa7eb` | 73.745491 / 12 | 3.63914776 / 1 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| native | 0 / `093415bc75db451bc49c5f0523a63715a265ca9dc6dc20a0b805c099f42d9be8` | 25.0684967 / 2 | 40.8453102 / 6 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 45 (elapsed 45) | False |
| A | 7 / `233db2f9c3b403a133b61d20ea8febd7dda06546620e82b81ab8859ec447916d` | 25.3005409 / 8 | 51.0172234 / 10 | [1, 0] | tail_success @ 47 (elapsed 47); failure @ None (elapsed 50) | False |
| B | 6 / `d5ee27a3e83a47ed4ccc2ffcc78bf631bf4710bd8f79e944078d0313ee97b7c6` | 25.2132969 / 7 | 38.2631302 / 5 | [0, 1] | failure @ None (elapsed 50); tail_success @ 48 (elapsed 48) | False |

Selected-pair ordering error (saved / float64): 80.2736406 / 80.2736403; goal-direction term 63.9480529; squared-error term 16.3255874; algebra residual 1.42108547e-14; saved-minus-float64 3.76524952e-07.
Mean squared error energy 83.5451521 = common 48.7304809 + specific 34.8146712; coordinate MSE 0.435131001; energy identity residual 0.

### reacher / lewm / source 18 (WM-DIAG0-A2-v1:reacher:root-018)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `4fb0f9f15492061acb76db440c9d5ff6f4cd7cc1c74f0353dbada67f4f94132e`; accepted output seal `4437c04a8e2a1f53d6affdf7053b7e2fc969b0e52dd6ddd8200d39a78b52a236`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `0e2e70012675330a51a9dad641772535026aba17f9cb04d54ed51270147ccd92` | 18.6577129 / 1 | 9.04663467 / 9 | [1, 1] | tail_success @ 26 (elapsed 26); tail_success @ 27 (elapsed 27) | False |
| O0 | 2 / `9727a414940d6c03a05c0bdd24ac3d8c44aa29ab4beeeb0b8baf11232ed468f2` | 18.7417831 / 2 | 0.989315033 / 1 | [1, 1] | prefix_success @ 9 (elapsed 9); prefix_success @ 9 (elapsed 9) | True |
| native | 0 / `c56941acfb66e790cf95c5472f27186ecc08308260e02a8da9952c44f35c3dad` | 19.2349167 / 9 | 2.55274105 / 4 | [1, 1] | prefix_success @ 11 (elapsed 11); prefix_success @ 11 (elapsed 11) | True |
| A | 2 / `9727a414940d6c03a05c0bdd24ac3d8c44aa29ab4beeeb0b8baf11232ed468f2` | 18.7417831 / 2 | 0.989315033 / 1 | [1, 1] | prefix_success @ 9 (elapsed 9); prefix_success @ 9 (elapsed 9) | True |
| B | 2 / `9727a414940d6c03a05c0bdd24ac3d8c44aa29ab4beeeb0b8baf11232ed468f2` | 18.7417831 / 2 | 0.989315033 / 1 | [1, 1] | prefix_success @ 9 (elapsed 9); prefix_success @ 9 (elapsed 9) | True |

Selected-pair ordering error (saved / float64): 8.14138985 / 8.14138912; goal-direction term 15.5279104; squared-error term -7.3865213; algebra residual -3.55271368e-15; saved-minus-float64 7.25720138e-07.
Mean squared error energy 42.1153815 = common 22.3467655 + specific 19.768616; coordinate MSE 0.219350945; energy identity residual 0.

### reacher / lewm / source 19 (WM-DIAG0-A2-v1:reacher:root-019)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `822f0edf4b3251d71094e491c751189ec3024d8377e68e12b8af0c035aaecdda`; accepted output seal `c2cd4ebfafbad45f45f50bc23fb60fd9c62773f8b48eb63ac92d69776cd29a4a`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `128eec2b301d37ddb00d20d5ed7f7b0b116d9ce32e6f1debe260ac12a0ed5632` | 18.1885643 / 1 | 1.31691933 / 1 | [1, 1] | prefix_success @ 20 (elapsed 20); prefix_success @ 20 (elapsed 20) | True |
| O0 | 1 / `128eec2b301d37ddb00d20d5ed7f7b0b116d9ce32e6f1debe260ac12a0ed5632` | 18.1885643 / 1 | 1.31691933 / 1 | [1, 1] | prefix_success @ 20 (elapsed 20); prefix_success @ 20 (elapsed 20) | True |
| native | 0 / `b0389dbd343f3d3801cdcc771ab01788745bc6d6873d4525f2a9e79f0839cb31` | 18.6701603 / 9 | 39.5086327 / 7 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 6 / `85aa4f9c8fc2316660907274a6072b22d8ef052f73e281b461897204556479e8` | 18.5634842 / 6 | 72.8234787 / 12 | [1, 1] | tail_success @ 42 (elapsed 42); tail_success @ 49 (elapsed 49) | False |
| B | 4 / `7d0d856230222b8ff856415097af046700393aca290f08865bc0944555caf386` | 18.5270042 / 4 | 27.4871368 / 4 | [1, 1] | tail_success @ 49 (elapsed 49); tail_success @ 49 (elapsed 49) | False |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 61.0308927 = common 37.8116337 + specific 23.219259; coordinate MSE 0.317869233; energy identity residual 1.42108547e-14.

### reacher / lewm / source 20 (WM-DIAG0-A2-v1:reacher:root-020)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `f8da2c76a258222b2c6ff3b52168f4de3154d458a0d3e77fa9a457e65447b882`; accepted output seal `5839fce619da18c55a646e8446f03cc66c0e9a252cf4df8ce73d6830aba044d3`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `c4b6d18a024bb4c319904e37a8513c6a659b2f35433e58b01a62f6152962ade4` | 23.4955406 / 1 | 32.9221878 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 1 / `c4b6d18a024bb4c319904e37a8513c6a659b2f35433e58b01a62f6152962ade4` | 23.4955406 / 1 | 32.9221878 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `cda0a14234549782dddb06fbd2f80946624f723626af5f306e6d426e8bfe6c54` | 23.7114143 / 3 | 36.1123581 / 7 | [0, 1] | failure @ None (elapsed 50); tail_success @ 48 (elapsed 48) | False |
| A | 7 / `d960cc45ebc682cd771e9f91bae50a19d84af4cf803d71e9db23eca13d6280d4` | 23.86623 / 8 | 34.4467163 / 4 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 49 (elapsed 49) | False |
| B | 7 / `d960cc45ebc682cd771e9f91bae50a19d84af4cf803d71e9db23eca13d6280d4` | 23.86623 / 8 | 34.4467163 / 4 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 49 (elapsed 49) | False |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 56.6258086 = common 38.8300235 + specific 17.795785; coordinate MSE 0.294926086; energy identity residual -7.10542736e-15.

### reacher / lewm / source 21 (WM-DIAG0-A2-v1:reacher:root-021)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `5d5b9efeb68b0e855fb4f2e9f0418f2d494344cdd09f38a705eb40e881554638`; accepted output seal `897e7b3d76b3a31d37332b987ea8907681403f36f298e2ea260170bcb00969be`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `f5ed24a38731496e5d716f7eada6398098abbd7b23d45572cbc5cc06f45fe7ad` | 18.3249054 / 1 | 2.17952681 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| O0 | 1 / `f5ed24a38731496e5d716f7eada6398098abbd7b23d45572cbc5cc06f45fe7ad` | 18.3249054 / 1 | 2.17952681 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `1c5c2cb2206e47e4a56d9286e9e2ed689e95e9821815577d10877cbb29117c6b` | 19.094574 / 9 | 15.7904043 / 8 | [1, 1] | tail_success @ 27 (elapsed 27); tail_success @ 28 (elapsed 28) | False |
| A | 8 / `0799aa5a6c7d52d8759e0b7da512555852ae813ad11be39fefd7660da7f5e839` | 18.7862415 / 8 | 27.7033234 / 9 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 7 / `8ea1a70582dde8d41da7406fa478a0092b205f578093cd9f42b10899de6f0868` | 18.7656555 / 7 | 8.20741272 / 2 | [1, 1] | tail_success @ 26 (elapsed 26); tail_success @ 26 (elapsed 26) | False |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 42.5346659 = common 22.1922095 + specific 20.3424564; coordinate MSE 0.221534718; energy identity residual 0.

### reacher / lewm / source 22 (WM-DIAG0-A2-v1:reacher:root-022)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `6787964a4485258256bbadf89595702525181e562bc25a1ea98297a617d87e6c`; accepted output seal `ef52a8833cd18957fdb0331e3d82a875eecad9fee3ccd13243d0ef687404e795`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `0f6ee5933a1f9d17bff3184aaae38547410e1bf2ac17a6f6e7c668bd6e7b1a51` | 11.0954113 / 1 | 1.74999058 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| O0 | 1 / `0f6ee5933a1f9d17bff3184aaae38547410e1bf2ac17a6f6e7c668bd6e7b1a51` | 11.0954113 / 1 | 1.74999058 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| native | 0 / `de78813b3350f6851e8ee75aa292e222d07f667d73ce4fceafb2812e1efedab9` | 11.9308043 / 9 | 20.9578571 / 9 | [1, 1] | tail_success @ 36 (elapsed 36); tail_success @ 50 (elapsed 50) | False |
| A | 9 / `01a129139f1ad87344443a16b6b91c6c8530f7e220d99345533e14da5440a12b` | 31.6298141 / 10 | 2.74609041 / 2 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| B | 8 / `f9f28af4646f2f716c7e1aa17e7518fc69afe8830ad60670b5e32fdca8efb0c5` | 11.5794764 / 8 | 15.8942699 / 3 | [0, 1] | failure @ None (elapsed 50); tail_success @ 50 (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 47.6726726 = common 24.7694855 + specific 22.9031871; coordinate MSE 0.24829517; energy identity residual 7.10542736e-15.

### reacher / lewm / source 23 (WM-DIAG0-A2-v1:reacher:root-023)

Original stratum: loss; action-choice changed: True; O0−P0: -50.000 pp. Source `01f7c70d6b065e965823ae105d4ea75e9c04a671c12d096557cdb3b01630643f`; accepted output seal `159f1c15eadaf5ff85d6dc6ab20854b6a678471a31e29ec0520f2fe150fdde5d`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `a36da101d1f1006e8e7a581c3b0914d9e4c185e5b1095a0bec6e8a2a871c2b49` | 32.1093216 / 1 | 14.727088 / 7 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 50 (elapsed 50) | False |
| O0 | 0 / `f857ecf08700230690755bf259368a44a9f5afaff801d581926fa5373948f558` | 32.4207916 / 9 | 11.0975266 / 1 | [1, 0] | tail_success @ 49 (elapsed 49); failure @ None (elapsed 50) | False |
| native | 0 / `f857ecf08700230690755bf259368a44a9f5afaff801d581926fa5373948f558` | 32.4207916 / 9 | 11.0975266 / 1 | [1, 0] | tail_success @ 49 (elapsed 49); failure @ None (elapsed 50) | False |
| A | 3 / `61a00bb7cae65c3d588b75d7e72dcabd852a5ec7336c9a7cfe47bbd877fde4ea` | 32.3226318 / 3 | 11.3693142 / 2 | [1, 0] | tail_success @ 49 (elapsed 49); failure @ None (elapsed 50) | False |
| B | 0 / `f857ecf08700230690755bf259368a44a9f5afaff801d581926fa5373948f558` | 32.4207916 / 9 | 11.0975266 / 1 | [1, 0] | tail_success @ 49 (elapsed 49); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 3.94103146 / 3.94103673; goal-direction term 5.9175219; squared-error term -1.97648518; algebra residual -1.0658141e-14; saved-minus-float64 -5.27092173e-06.
Mean squared error energy 55.9890838 = common 37.7172984 + specific 18.2717854; coordinate MSE 0.291609811; energy identity residual -7.10542736e-15.

### reacher / lewm / source 24 (WM-DIAG0-A2-v1:reacher:root-024)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `dc70cf0f539c9a47d2911db36cbfc8bd9af3c57f157fc3c8483ff471745d1cad`; accepted output seal `56701419548ae3f30b2fe29d2c6791ff5e0fe47c374a1e129c898ff0f1338855`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `4dba7a3ade7a1305b28918f74b9e793df6fc927fd31046f9e51001354465192f` | 20.1585236 / 1 | 2.0963819 / 3 | [1, 1] | prefix_success @ 18 (elapsed 18); prefix_success @ 18 (elapsed 18) | True |
| O0 | 5 / `0f4bb86d18b7054c97f8051b14701c07599553fd0ed1d2411157c9f862225caa` | 20.6123371 / 5 | 0.538071573 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `b5fef7bd506c86f8fb7a92488706962a250d79f1d94f21a8064e87cdc12ac501` | 20.6289005 / 6 | 23.8320885 / 8 | [0, 1] | failure @ None (elapsed 50); tail_success @ 33 (elapsed 33) | False |
| A | 4 / `2b81c5e7fe509f196da2acae84b2052b75112480d698c2c24e42da94f9a6b847` | 20.5060768 / 4 | 19.4513187 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 10 / `d83236b92dfa355186fec83eb6e8e79bc6c807a3f7903d5db46bc4ea915ee775` | 79.4366302 / 11 | 0.741501808 / 2 | [1, 1] | prefix_success @ 12 (elapsed 12); prefix_success @ 12 (elapsed 12) | True |

Selected-pair ordering error (saved / float64): 2.01212388 / 2.01212276; goal-direction term -0.166637694; squared-error term 2.17876046; algebra residual 2.66453526e-15; saved-minus-float64 1.1196854e-06.
Mean squared error energy 65.8879125 = common 29.1402844 + specific 36.7476281; coordinate MSE 0.343166211; energy identity residual 1.42108547e-14.

### reacher / lewm / source 25 (WM-DIAG0-A2-v1:reacher:root-025)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `90b2b8420f1662410f6c8fb42c59929e9e8884fe255276f21565cce39da8145c`; accepted output seal `87fb085fb4b00efeb06a2673e59e1ffe903686a50d9e89d8fc23e61a91671738`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `574e6a106cc83813c2c79c3d4ad57799171e1e1d67b104a580f0d840aa4cf2f5` | 11.2059269 / 1 | 25.9333725 / 8 | [1, 1] | tail_success @ 27 (elapsed 27); tail_success @ 29 (elapsed 29) | False |
| O0 | 6 / `55bb23b8e1946f18bbed7f0d98f77ca199a85fda645b3b711ba857223f706ef4` | 11.3862057 / 6 | 6.55072069 / 1 | [1, 1] | tail_success @ 26 (elapsed 26); tail_success @ 27 (elapsed 27) | False |
| native | 0 / `670f73d49db48201709602068aa34b241a15bd8756c849d662693a13d4aabbc1` | 11.5894566 / 9 | 14.3651648 / 3 | [1, 1] | tail_success @ 26 (elapsed 26); tail_success @ 35 (elapsed 35) | False |
| A | 8 / `5c371fbef66b2038cf33b6d3729b153ab69dbdf06de5be256a4b3de319b1227c` | 11.4398975 / 8 | 18.6063385 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 0 / `670f73d49db48201709602068aa34b241a15bd8756c849d662693a13d4aabbc1` | 11.5894566 / 9 | 14.3651648 / 3 | [1, 1] | tail_success @ 26 (elapsed 26); tail_success @ 35 (elapsed 35) | False |

Selected-pair ordering error (saved / float64): 19.5629306 / 19.5629312; goal-direction term 40.8062233; squared-error term -21.2432921; algebra residual 0; saved-minus-float64 -6.30391099e-07.
Mean squared error energy 37.4155174 = common 24.0753506 + specific 13.3401667; coordinate MSE 0.194872486; energy identity residual 0.

### reacher / lewm / source 26 (WM-DIAG0-A2-v1:reacher:root-026)

Original stratum: gain; action-choice changed: True; O0−P0: +100.000 pp. Source `4e8fd87b75ca5d0cec3f965b04d6fa309eeeb00ca2bc98c5a766a5f63a7b928c`; accepted output seal `36e23166714fe4a12b498a7061e5363ea4a5426d9d7269484e25424a9037d56b`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `ad70e310f2d5eb12fdd6d4c08bb1a15a40ddc7a562b6a7cb080cae9976c94f2f` | 30.7586861 / 1 | 120.73674 / 12 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 6 / `c01a4fa44423c7e7e1961223ec744a46745289498af9fa72b08b380f0b017830` | 31.4305916 / 6 | 2.10432649 / 1 | [1, 1] | prefix_success @ 14 (elapsed 14); prefix_success @ 14 (elapsed 14) | True |
| native | 0 / `599871e2d8c51b58df8602680186c4170cfa4893101a79c34ea8d98dd471bf3a` | 31.5541859 / 9 | 94.8676605 / 5 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 8 / `4876eea3623a16d97721f4a40fd238a428faf6ae655d3c4a3a0a7a9982d85214` | 31.4326191 / 8 | 102.728622 / 11 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 8 / `4876eea3623a16d97721f4a40fd238a428faf6ae655d3c4a3a0a7a9982d85214` | 31.4326191 / 8 | 102.728622 / 11 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 119.304319 / 119.304329; goal-direction term 254.213054; squared-error term -134.908724; algebra residual 0; saved-minus-float64 -1.01898314e-05.
Mean squared error energy 112.220809 = common 72.3203562 + specific 39.9004524; coordinate MSE 0.584483378; energy identity residual 0.

### reacher / lewm / source 27 (WM-DIAG0-A2-v1:reacher:root-027)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `84402ff53fdb2987c340ad72ec8ec3223c3c215c2319abebafdbf0d706772d7c`; accepted output seal `904cca4d2ba0d6501052c75dfa3da73c3654ea0c1bbe69ca80d6bd8f445a0afa`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `7f7a78ed2d6267b1a4f96e321d45a9ce7b5e493bf1247d5414a2dbb6b4e5fa5d` | 22.7722721 / 1 | 36.2710342 / 11 | [0, 1] | failure @ None (elapsed 50); tail_success @ 47 (elapsed 47) | False |
| O0 | 5 / `33de9812ccc1cb591f12dec194b124cd9b2a8c841a87d9f63d0fc3c3d5a11c6f` | 22.9098454 / 5 | 3.06647873 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `2c6b1f6e9f6895aedb19e38610af5a4d053c256d919a195833c9b4fd4b13d39a` | 23.1237411 / 9 | 32.4670601 / 10 | [0, 1] | failure @ None (elapsed 50); tail_success @ 28 (elapsed 28) | False |
| A | 9 / `82760acd52c01f2fd3de71c5c85dfeb6b255f94a8390770479ad5d69e9f863c5` | 39.7486305 / 10 | 13.8377123 / 2 | [0, 1] | failure @ None (elapsed 50); tail_success @ 27 (elapsed 27) | False |
| B | 9 / `82760acd52c01f2fd3de71c5c85dfeb6b255f94a8390770479ad5d69e9f863c5` | 39.7486305 / 10 | 13.8377123 / 2 | [0, 1] | failure @ None (elapsed 50); tail_success @ 27 (elapsed 27) | False |

Selected-pair ordering error (saved / float64): 33.3421288 / 33.3421301; goal-direction term 59.5882046; squared-error term -26.2460745; algebra residual 0; saved-minus-float64 -1.37905036e-06.
Mean squared error energy 53.7483695 = common 34.0734686 + specific 19.6749009; coordinate MSE 0.279939424; energy identity residual 0.

### reacher / lewm / source 28 (WM-DIAG0-A2-v1:reacher:root-028)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `3861946e480c84693f37eafb141900cda1e3015cdebcbd48df349b0eb3df8ef5`; accepted output seal `d85323c2794e6cc0a758b1b2983168f9104c65c8e4458690d6b6a4f9802a4428`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `a035351d6acdb93af7ed81109e4f04e2f3c3026c4d3223c82f4b6a1d3f88f3ab` | 27.2319126 / 1 | 6.79589128 / 8 | [1, 0] | tail_success @ 50 (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 10 / `e90db058535f54f28014ec66a76cf021809f305446cb3c0912f6b37534ad43be` | 41.7267647 / 11 | 0.515551567 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `2209005d5a608d427d5795330260d9f8133522d7f19c5156ab2d3f4d90f5359a` | 27.3759975 / 2 | 6.61623573 / 5 | [1, 0] | tail_success @ 27 (elapsed 27); failure @ None (elapsed 50) | False |
| A | 10 / `e90db058535f54f28014ec66a76cf021809f305446cb3c0912f6b37534ad43be` | 41.7267647 / 11 | 0.515551567 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| B | 6 / `8c94b36d188e79228b71c35e773ce2b968e63769b3f7a88b69875f4c701fce4f` | 27.4542255 / 7 | 5.30877924 / 4 | [1, 0] | tail_success @ 27 (elapsed 27); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 20.7751918 / 20.7751902; goal-direction term 13.7774006; squared-error term 6.99778965; algebra residual 7.10542736e-15; saved-minus-float64 1.54773836e-06.
Mean squared error energy 37.5352682 = common 29.6674495 + specific 7.8678187; coordinate MSE 0.195496188; energy identity residual 0.

### reacher / lewm / source 29 (WM-DIAG0-A2-v1:reacher:root-029)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `052f98b6f190e04d428fee785429590a1419b7fabbc40b3f310992085b986c5f`; accepted output seal `eaa355d738ee96949007d88ab99c83407be9b9e14494e34f469b155a2b75928a`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `b2b666025a3489a330bce45a13670bc49cf3b41642487b48b9240f7f8bf10367` | 20.237257 / 1 | 4.91991711 / 6 | [1, 0] | tail_success @ 27 (elapsed 27); failure @ None (elapsed 50) | False |
| O0 | 4 / `7b818fecd302d5815df5cb09e84fe1312766ba2f1dbdf2a15b242ef6fdceb1ed` | 20.4575043 / 4 | 0.936054707 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| native | 0 / `14e22ba21cd5d4adc1ec24b1578c0369d09440e6f9bd6ba140524d69e3901a5f` | 20.6092186 / 8 | 4.01427031 / 5 | [1, 0] | tail_success @ 26 (elapsed 26); failure @ None (elapsed 50) | False |
| A | 4 / `7b818fecd302d5815df5cb09e84fe1312766ba2f1dbdf2a15b242ef6fdceb1ed` | 20.4575043 / 4 | 0.936054707 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| B | 2 / `99b406f8e0b8d48e98f1c19609224a426f882961565a7793f54b888389c5c57b` | 20.4152508 / 2 | 1.862082 / 2 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 4.20410967 / 4.20411063; goal-direction term 6.79654193; squared-error term -2.5924313; algebra residual 0; saved-minus-float64 -9.6390169e-07.
Mean squared error energy 27.1224951 = common 18.1005589 + specific 9.02193613; coordinate MSE 0.141262995; energy identity residual 0.

### reacher / lewm / source 30 (WM-DIAG0-A2-v1:reacher:root-030)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `eebd723f13229de8853565a3cc96dd9ee7660aa5559a0e90ece90817fa5e1082`; accepted output seal `695b0065286255a5d5fbd8d15010e5d38ed4dc009da9b5380aaeea7447a53cd7`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `c20f3ef41f0a04b27dddcd1c3e83749643ea704ab57d24de795edc178031cbd0` | 27.8967342 / 1 | 64.6621704 / 11 | [0, 1] | failure @ None (elapsed 50); tail_success @ 43 (elapsed 43) | False |
| O0 | 2 / `7d649fdbae2fab2118a45a855da29ab3c00229065b23ebe3d277a48cf9646a5c` | 28.2233868 / 2 | 0.217573732 / 1 | [1, 1] | prefix_success @ 9 (elapsed 9); prefix_success @ 9 (elapsed 9) | True |
| native | 0 / `09ea2e99c7beee919ab1c9391a150c086770ee9ba577c4451fe58b1daa460980` | 28.8425198 / 9 | 57.0209465 / 9 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 0 / `09ea2e99c7beee919ab1c9391a150c086770ee9ba577c4451fe58b1daa460980` | 28.8425198 / 9 | 57.0209465 / 9 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 11 / `7146ef78212ce37207c477d483c2f7dde34a881c00661b0ad1bb9bc386fcdeaa` | 137.48056 / 12 | 4.24038458 / 5 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |

Selected-pair ordering error (saved / float64): 64.7712492 / 64.7712483; goal-direction term 138.202681; squared-error term -73.4314329; algebra residual 0; saved-minus-float64 9.49978016e-07.
Mean squared error energy 113.425995 = common 48.8275034 + specific 64.5984917; coordinate MSE 0.590760391; energy identity residual 0.

### reacher / lewm / source 31 (WM-DIAG0-A2-v1:reacher:root-031)

Original stratum: gain; action-choice changed: True; O0−P0: +100.000 pp. Source `80cc6b9e75d2d0eb7f25b7f5b38727b59a9fe7fd807743ba4fad3fd251bbc9d3`; accepted output seal `91811cbe1b35e3218c7b037f867b7fc563ac7a833e7243b67ce27c3f2537c763`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `3835ee97e675fd90565d3521311f7932427c97a4ec9604949db1012c62c942e9` | 26.0452538 / 1 | 148.377472 / 9 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 8 / `f32f883a713ec9ac8ceaa887cc29ba6c39e2eaf29f7a6819ab6bcb39168c53b9` | 26.9337673 / 8 | 90.0780487 / 1 | [1, 1] | tail_success @ 50 (elapsed 50); tail_success @ 50 (elapsed 50) | False |
| native | 0 / `ce23a9cae8945c95127c8bbccc0b36d652dd131eb90a28a56cb3d3bc7c8b1a09` | 27.1377487 / 9 | 105.876877 / 5 | [1, 0] | tail_success @ 48 (elapsed 48); failure @ None (elapsed 50) | False |
| A | 8 / `f32f883a713ec9ac8ceaa887cc29ba6c39e2eaf29f7a6819ab6bcb39168c53b9` | 26.9337673 / 8 | 90.0780487 / 1 | [1, 1] | tail_success @ 50 (elapsed 50); tail_success @ 50 (elapsed 50) | False |
| B | 3 / `5dc112c6d262510a50eb95d31c278fb1c06cd807e1a74eef551635e17f2c7c85` | 26.5459518 / 3 | 93.5689697 / 3 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 59.1879368 / 59.1879283; goal-direction term 121.03764; squared-error term -61.8497115; algebra residual 1.42108547e-14; saved-minus-float64 8.43744446e-06.
Mean squared error energy 151.465964 = common 94.1562905 + specific 57.3096734; coordinate MSE 0.788885228; energy identity residual 0.

### reacher / dinowm_noprop / source 0 (WM-DIAG0-A2-v1:reacher:root-000)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `e9b6673d8a9c8a0ef4146d59042cccc2cc558795c73b3c90af4fa6f49de17599`; accepted output seal `dab51d11fcfa66270dcfdce84ed8e2adfe129618ec1186af7975c683aae1d5e5`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `06af4c3ec71a2e3610f1419d670ea450b6218b9abdc4b97add8d5d423a43f053` | 0.37076354 / 1 | 0.173950404 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 8 / `f8d6e515f36474f722d0e125952ee703d5c2d1ab9d37b7e0298738a0768bb7c3` | 0.371651947 / 8 | 0.0587111413 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| native | 0 / `094fadf93a4fa93bde64b1c0a8e846ffee92e7d0008ff8c2ab79af20d99e0dd8` | 0.372519821 / 9 | 0.149264783 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 8 / `f8d6e515f36474f722d0e125952ee703d5c2d1ab9d37b7e0298738a0768bb7c3` | 0.371651947 / 8 | 0.0587111413 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 8 / `f8d6e515f36474f722d0e125952ee703d5c2d1ab9d37b7e0298738a0768bb7c3` | 0.371651947 / 8 | 0.0587111413 / 1 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0.11612767 / 0.116127659; goal-direction term 0.209598863; squared-error term -0.0934712037; algebra residual -2.77555756e-17; saved-minus-float64 1.03565747e-08.
Mean squared error energy 40237.2477 = common 28970.0737 + specific 11267.174; coordinate MSE 0.534614792; energy identity residual 0.

### reacher / dinowm_noprop / source 1 (WM-DIAG0-A2-v1:reacher:root-001)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `eff6819a4646f8eaf99d0c1bb902c1e68b61aa1407be1de6259fb664fcfbad64`; accepted output seal `8a155edb99930c1da52d7bfbb3846c6162d3f12b8da065b21e6d0f0294aae2e7`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `19c7927bea850b74ffe03782ef510357781810cbb4075a8fc95441ddbe8a5900` | 0.381569117 / 1 | 0.0886060447 / 11 | [0, 1] | failure @ None (elapsed 50); tail_success @ 26 (elapsed 26) | False |
| O0 | 2 / `f4bbcfe093e538291448efd682fb84102b91c624ef7b32c2c97ff979b436b274` | 0.38270393 / 2 | 0.0164189599 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `c87d395091df140e08ccb696f09f225ddb1d246912b5a6d9a11978d8ea62ad56` | 0.384568393 / 9 | 0.0432727747 / 4 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| A | 2 / `f4bbcfe093e538291448efd682fb84102b91c624ef7b32c2c97ff979b436b274` | 0.38270393 / 2 | 0.0164189599 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| B | 2 / `f4bbcfe093e538291448efd682fb84102b91c624ef7b32c2c97ff979b436b274` | 0.38270393 / 2 | 0.0164189599 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 0.0733218975 / 0.0733219365; goal-direction term 0.10602752; squared-error term -0.0327055835; algebra residual 6.9388939e-17; saved-minus-float64 -3.89441091e-08.
Mean squared error energy 37825.5683 = common 26512.7007 + specific 11312.8676; coordinate MSE 0.502571858; energy identity residual -7.27595761e-12.

### reacher / dinowm_noprop / source 2 (WM-DIAG0-A2-v1:reacher:root-002)

Original stratum: gain; action-choice changed: True; O0−P0: +100.000 pp. Source `632a470ffe8b212fcf61016dc92282b7c62cd5a2588cd5100cad56d2f98589f9`; accepted output seal `12224316ae8fe7a1f2f8baab41311a6453ab3991a42ff447ce9a66cbd7e7e977`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `ac8300005bc069e73e1225fe8b7e0da06e1bb8a6835b0a89f655bff95dbb278a` | 0.354174078 / 1 | 0.118578665 / 10 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 6 / `0c4a23b13decef3c58ca57ea85648712a4e860b5dca0647b3647daa470b715d9` | 0.356970221 / 6 | 0.0178624727 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `c7a6dd0905e39b0723d1d34e83cc1e025be5763dcf080e31ec294b192c73fcae` | 0.366936386 / 9 | 0.0768872201 / 4 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| A | 8 / `b9afe7af862bf3255d8074d15dd3fe02efe103e704aa84d67cdb424e38752252` | 0.357562453 / 8 | 0.100386076 / 7 | [1, 0] | tail_success @ 27 (elapsed 27); failure @ None (elapsed 50) | False |
| B | 6 / `0c4a23b13decef3c58ca57ea85648712a4e860b5dca0647b3647daa470b715d9` | 0.356970221 / 6 | 0.0178624727 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |

Selected-pair ordering error (saved / float64): 0.103512336 / 0.10351231; goal-direction term 0.154118416; squared-error term -0.0506061057; algebra residual 0; saved-minus-float64 2.51274198e-08.
Mean squared error energy 35030.3499 = common 24673.2706 + specific 10357.0793; coordinate MSE 0.465433008; energy identity residual 0.

### reacher / dinowm_noprop / source 3 (WM-DIAG0-A2-v1:reacher:root-003)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `9604b0b63d39fe85bdaa1fff2060a870089bc8c474f0717582d574e2a4c5cd84`; accepted output seal `824cfe1fcb3e8c13c77ba4ccf2f6bdfaea2b79d4488102c9f5997db6c9027e19`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `cd0e3aefc60afb938f348ecb02a13f5737a30970352f8477da18421f3924f6e2` | 0.361423254 / 1 | 0.0418526903 / 4 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| O0 | 9 / `7e3e7c907d98c37e6b71467a7feb9959058ea61f4ad4c6c364130f3a38ee037f` | 0.492295027 / 10 | 0.0182269663 / 1 | [1, 1] | prefix_success @ 18 (elapsed 18); prefix_success @ 18 (elapsed 18) | True |
| native | 0 / `2883993c1bd5d86fbbcd163d32cf078ca8a8876deb026081d17c1f9dfc5fc0a1` | 0.364177287 / 9 | 0.0963929817 / 9 | [1, 1] | prefix_success @ 10 (elapsed 10); prefix_success @ 10 (elapsed 10) | True |
| A | 3 / `db4eac5895c859836254d315fa217dd2465c31bf396cf6bde91be047e766a700` | 0.362897545 / 3 | 0.0788682178 / 7 | [1, 1] | prefix_success @ 15 (elapsed 15); prefix_success @ 15 (elapsed 15) | True |
| B | 11 / `512202f6312bda239401c76b0cbcf959bd4e0a97d3e66b19f32ee384c7a5833b` | 0.698203623 / 12 | 0.0449052416 / 5 | [1, 1] | prefix_success @ 10 (elapsed 10); prefix_success @ 10 (elapsed 10) | True |

Selected-pair ordering error (saved / float64): 0.154497497 / 0.154497513; goal-direction term 0.0756784562; squared-error term 0.0788190572; algebra residual -1.94289029e-16; saved-minus-float64 -1.66113459e-08.
Mean squared error energy 40755.47 = common 24645.6438 + specific 16109.8262; coordinate MSE 0.541500186; energy identity residual 7.27595761e-12.

### reacher / dinowm_noprop / source 4 (WM-DIAG0-A2-v1:reacher:root-004)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `198112f4173b1f8599b263205b18b012498c367dcc4114b9e51344b33bc4493f`; accepted output seal `dabd22d322e6f50b63b5845c3fbb1c98c93b8c53644ac6fb6ebacf038d99fd6b`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `52bcf76d8ef40f65ecf7851177765258cbfb66fdb1d0edf338d4be5718c9d8ab` | 0.401110232 / 1 | 0.113974847 / 8 | [0, 1] | failure @ None (elapsed 50); tail_success @ 31 (elapsed 31) | False |
| O0 | 10 / `cd5979e0a51be0401368dbe5663e0688e6b8506efed8a111f764af7fbdd3e8c7` | 0.521769047 / 11 | 0.00920514856 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `a3c66ecde9bf94964c82480e78d75b96c5afa9028c1cb370cc67ce9c0ff3c999` | 0.402942002 / 9 | 0.118233852 / 10 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 0 / `a3c66ecde9bf94964c82480e78d75b96c5afa9028c1cb370cc67ce9c0ff3c999` | 0.402942002 / 9 | 0.118233852 / 10 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 10 / `cd5979e0a51be0401368dbe5663e0688e6b8506efed8a111f764af7fbdd3e8c7` | 0.521769047 / 11 | 0.00920514856 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 0.225428513 / 0.22542849; goal-direction term 0.133070661; squared-error term 0.092357829; algebra residual -2.77555756e-17; saved-minus-float64 2.3323307e-08.
Mean squared error energy 40219.603 = common 28599.2776 + specific 11620.3253; coordinate MSE 0.534380354; energy identity residual -7.27595761e-12.

### reacher / dinowm_noprop / source 5 (WM-DIAG0-A2-v1:reacher:root-005)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `813b29e22207eb66ec17e8f6606fbb507309f5e3d0b8cd97c94acb09c3617457`; accepted output seal `62935aeb67e7a882158bae28f497544d3183fdef85e8e968a23fc37bfb09d662`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `754c7ee4419d22d1eb2fd253b63883767ed5d2ce58ded3cbadd119264a38aefe` | 0.429844797 / 1 | 0.321642101 / 11 | [1, 1] | tail_success @ 31 (elapsed 31); tail_success @ 27 (elapsed 27) | False |
| O0 | 7 / `1b53f7ca1a9d9123988431f5fda552ae9f110d94020489559add3ee0945c980f` | 0.432123959 / 7 | 0.0192065947 / 1 | [1, 1] | tail_success @ 26 (elapsed 26); tail_success @ 26 (elapsed 26) | False |
| native | 0 / `cb725daaefa92ab891d6f94449c7228654f703d0de6df08461cb9e6657084ccf` | 0.432921022 / 9 | 0.189452231 / 8 | [1, 1] | tail_success @ 43 (elapsed 43); tail_success @ 50 (elapsed 50) | False |
| A | 8 / `2cd34666681257917e2da9a8939b80c1c7f99e85f78ad471324243ce34c59dbf` | 0.43218267 / 8 | 0.281534374 / 10 | [1, 1] | tail_success @ 28 (elapsed 28); tail_success @ 48 (elapsed 48) | False |
| B | 5 / `50c3c2e9eeb0bf3c6c63efeae216b26d606a93d9b351ccbe66b161cd1f1f87a4` | 0.43179062 / 5 | 0.0951005667 / 4 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |

Selected-pair ordering error (saved / float64): 0.304714669 / 0.304714699; goal-direction term 0.58496061; squared-error term -0.280245911; algebra residual 5.55111512e-17; saved-minus-float64 -3.00692878e-08.
Mean squared error energy 51910.7803 = common 33822.8665 + specific 18087.9138; coordinate MSE 0.689715937; energy identity residual -7.27595761e-12.

### reacher / dinowm_noprop / source 6 (WM-DIAG0-A2-v1:reacher:root-006)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `8a44ed3a0ecb2b640b315d4abc0cb02d5dfb3ac5514cb6f39f49a58c8e530619`; accepted output seal `e80e840b5c13f3984253526eef3606ab53500fd1930c475f30412f0d5628c6ea`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `0cded1483552ac4eccc8246c0672cb76eceedd04815d949a27f450555a266949` | 0.350731403 / 1 | 0.0151910158 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| O0 | 1 / `0cded1483552ac4eccc8246c0672cb76eceedd04815d949a27f450555a266949` | 0.350731403 / 1 | 0.0151910158 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `ec54cd9a6a732363d81bea3d647c3ef4ebf379c50582d2fb5c881b8ccad9c012` | 0.352511436 / 9 | 0.0287742764 / 4 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| A | 1 / `0cded1483552ac4eccc8246c0672cb76eceedd04815d949a27f450555a266949` | 0.350731403 / 1 | 0.0151910158 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| B | 1 / `0cded1483552ac4eccc8246c0672cb76eceedd04815d949a27f450555a266949` | 0.350731403 / 1 | 0.0151910158 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 31657.4009 = common 25416.7592 + specific 6240.64172; coordinate MSE 0.420618103; energy identity residual 3.63797881e-12.

### reacher / dinowm_noprop / source 7 (WM-DIAG0-A2-v1:reacher:root-007)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `286c65760e14c3f68386a4740bbc988641662ebb6ff0c4e4869b2c2db2eaae7e`; accepted output seal `e3b302d252f8f17d89796bc8ff68cb6a84457e80e98103c9e610545e6feb8a6f`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `15f2f4c72cfe65b183d4f06c76b987d338e11c355eadf83293b53a237f310bf2` | 0.403363436 / 1 | 0.0344911255 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| O0 | 1 / `15f2f4c72cfe65b183d4f06c76b987d338e11c355eadf83293b53a237f310bf2` | 0.403363436 / 1 | 0.0344911255 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| native | 0 / `57a767fd85d3907330cda69af43f8c11f4f0b07eee56cea7ab328b58f591bbc7` | 0.407253861 / 9 | 0.147986203 / 5 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| A | 0 / `57a767fd85d3907330cda69af43f8c11f4f0b07eee56cea7ab328b58f591bbc7` | 0.407253861 / 9 | 0.147986203 / 5 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| B | 3 / `a42f81b52c05baa52ba061aec006278824954a6f8b7963c94aeceb89f717a2a1` | 0.403426826 / 3 | 0.040655043 / 2 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 39065.3319 = common 27527.1443 + specific 11538.1876; coordinate MSE 0.519044057; energy identity residual 0.

### reacher / dinowm_noprop / source 8 (WM-DIAG0-A2-v1:reacher:root-008)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `ac403d447b2b8e1ebc1bd4030b18cfc2cee17f22e5a41f666ea5619f55a384e9`; accepted output seal `5919edc01e7d31be179a28b3e0d2632a7e4d64794370acfac8b5876820926e61`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `d77654022b177a7555fa5b770c9e53f97a93f25ae4822cb0608389739851706d` | 0.381287009 / 1 | 0.0491313152 / 7 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| O0 | 2 / `48dbddbc270e2730a7044eeda14b1e7af78a3804075b6f1bfffcd99aaf3a27cc` | 0.382156074 / 2 | 0.0310026854 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `7096b4f4dbcc41df603db170963d8b8455a9977403924f6e9263c7e617780cf1` | 0.383944333 / 9 | 0.0484646894 / 6 | [1, 1] | prefix_success @ 10 (elapsed 10); prefix_success @ 10 (elapsed 10) | True |
| A | 2 / `48dbddbc270e2730a7044eeda14b1e7af78a3804075b6f1bfffcd99aaf3a27cc` | 0.382156074 / 2 | 0.0310026854 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| B | 7 / `8d476f5afbe9b9dccd1f307e1a1b00197bb28bd764c0dbf9bda638e771b8db78` | 0.382482857 / 7 | 0.0392615646 / 2 | [1, 1] | prefix_success @ 9 (elapsed 9); prefix_success @ 9 (elapsed 9) | True |

Selected-pair ordering error (saved / float64): 0.0189976953 / 0.018997707; goal-direction term 0.0349746656; squared-error term -0.0159769586; algebra residual 9.02056208e-17; saved-minus-float64 -1.17010429e-08.
Mean squared error energy 34666.0317 = common 26883.2948 + specific 7782.73694; coordinate MSE 0.460592471; energy identity residual -7.27595761e-12.

### reacher / dinowm_noprop / source 9 (WM-DIAG0-A2-v1:reacher:root-009)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `b8a3ccf2e11ad121c67fe7e94c35d87160b7a8177858b26f443891d86408a8f2`; accepted output seal `9c98c220b733aacfa60e80e036a58f0f44e6e191dd791cddb88dd9487e7c781a`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `dda729f76d5c5a94c94895a620e123a72eee7209ce7f06519cc5c03d5f7d1e7c` | 0.396831155 / 1 | 0.413117737 / 11 | [1, 1] | tail_success @ 38 (elapsed 38); tail_success @ 50 (elapsed 50) | False |
| O0 | 3 / `2e6d34ad1fea4b7b2d56a7dc9fa6bd71a8382859c0306c5d1067c0798ad6244e` | 0.397796184 / 3 | 0.0365546457 / 1 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| native | 0 / `cd7709df96a7ae1bb395d29f2199eab08e176288fa9152d2dcc60bdf30b6271e` | 0.398675859 / 9 | 0.0479021519 / 5 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| A | 8 / `11f1256c25553db07ec90155606a3b45b05b40b58935d3e78c612d00c76f7c55` | 0.398427963 / 8 | 0.0383903049 / 2 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| B | 8 / `11f1256c25553db07ec90155606a3b45b05b40b58935d3e78c612d00c76f7c55` | 0.398427963 / 8 | 0.0383903049 / 2 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |

Selected-pair ordering error (saved / float64): 0.37752812 / 0.377528149; goal-direction term 0.704251344; squared-error term -0.326723195; algebra residual -3.33066907e-16; saved-minus-float64 -2.91290343e-08.
Mean squared error energy 41752.6635 = common 27225.3954 + specific 14527.2681; coordinate MSE 0.554749462; energy identity residual 0.

### reacher / dinowm_noprop / source 10 (WM-DIAG0-A2-v1:reacher:root-010)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `2c274ca14ccdd298258efc92731898e881d15330e83195f4ea5a96eccb597208`; accepted output seal `3881d4f67185199b08c43f3807b271d22222355f9b142fe6dad620e4dc046820`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `0904f79ce1db0d9d695a52c20146731eb37f5197e2809883f919c6ba2469bc16` | 0.359548032 / 1 | 0.377342254 / 12 | [1, 1] | tail_success @ 35 (elapsed 35); tail_success @ 32 (elapsed 32) | False |
| O0 | 4 / `5af298aec31a740a37f855cd3e18e16841091e776408649a3a9e12e83314f3ca` | 0.360287249 / 4 | 0.0248874351 / 1 | [1, 1] | prefix_success @ 12 (elapsed 12); prefix_success @ 12 (elapsed 12) | True |
| native | 0 / `63ff65e81aa00ef4e63f765b0fec44e92feb9d89448f646ba36d546f1fbb6aa1` | 0.361797363 / 9 | 0.300833911 / 9 | [1, 0] | tail_success @ 42 (elapsed 42); failure @ None (elapsed 50) | False |
| A | 0 / `63ff65e81aa00ef4e63f765b0fec44e92feb9d89448f646ba36d546f1fbb6aa1` | 0.361797363 / 9 | 0.300833911 / 9 | [1, 0] | tail_success @ 42 (elapsed 42); failure @ None (elapsed 50) | False |
| B | 4 / `5af298aec31a740a37f855cd3e18e16841091e776408649a3a9e12e83314f3ca` | 0.360287249 / 4 | 0.0248874351 / 1 | [1, 1] | prefix_success @ 12 (elapsed 12); prefix_success @ 12 (elapsed 12) | True |

Selected-pair ordering error (saved / float64): 0.353194036 / 0.35319406; goal-direction term 0.653187198; squared-error term -0.299993137; algebra residual -5.55111512e-17; saved-minus-float64 -2.4846641e-08.
Mean squared error energy 43048.1412 = common 26982.2943 + specific 16065.8469; coordinate MSE 0.571961911; energy identity residual 0.

### reacher / dinowm_noprop / source 11 (WM-DIAG0-A2-v1:reacher:root-011)

Original stratum: gain; action-choice changed: True; O0−P0: +100.000 pp. Source `386a5aed44e823817815ed1a8a6bf19fc7ee50177e981dbcc68da750cfdef4c1`; accepted output seal `fb8870e836cc38b88992c2b62e2f43218e794c87f3b88a2f81e8bd03c549e22a`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `ebd179bb5c26d369ee61e25bbe65faabcd5763214fb699f45855c246bf3b6658` | 0.378901094 / 1 | 0.0819709077 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 10 / `8d2c4bcc4d4eb6b0906b63cddd950393c00bb9eb07967489650bb0d86d36f14b` | 0.604088366 / 11 | 0.0359118581 / 1 | [1, 1] | prefix_success @ 4 (elapsed 4); prefix_success @ 4 (elapsed 4) | True |
| native | 0 / `7d29bd09ed350ec186bce6f5a1622997617f0871a4f00a2a432f8430274a935d` | 0.38114211 / 9 | 0.101669781 / 9 | [0, 1] | failure @ None (elapsed 50); tail_success @ 44 (elapsed 44) | False |
| A | 7 / `dc6919a98fed44aa6a70f2bd7babdff3ed7940daeed458923ff07fb6e36b385a` | 0.379508555 / 7 | 0.0756557509 / 4 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 10 / `8d2c4bcc4d4eb6b0906b63cddd950393c00bb9eb07967489650bb0d86d36f14b` | 0.604088366 / 11 | 0.0359118581 / 1 | [1, 1] | prefix_success @ 4 (elapsed 4); prefix_success @ 4 (elapsed 4) | True |

Selected-pair ordering error (saved / float64): 0.271246321 / 0.27124633; goal-direction term 0.116560028; squared-error term 0.154686302; algebra residual -2.77555756e-16; saved-minus-float64 -8.70085026e-09.
Mean squared error energy 38970.764 = common 25979.1229 + specific 12991.6411; coordinate MSE 0.517787574; energy identity residual -7.27595761e-12.

### reacher / dinowm_noprop / source 12 (WM-DIAG0-A2-v1:reacher:root-012)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `596814b976b330931db15fc9482f5d8fd45f824019c9e42ef5dcfa0f5e98f58d`; accepted output seal `6bd58424a03efbad52371a51452a81a7d34868f3e6d39adcc534ecf9ca2dd2b0`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `55999a202ba6a4d7365f461b3eb78514f4f579b9e67e0b46a6fb6b18fdd941c4` | 0.37455076 / 1 | 0.374223441 / 6 | [1, 1] | tail_success @ 50 (elapsed 50); tail_success @ 39 (elapsed 39) | False |
| O0 | 12 / `5666af5c4edf759f5d3a3b4bb84612e83619b50ff7b4fe9936527afeb055e367` | 0.890314817 / 13 | 0.0767554715 / 1 | [1, 1] | tail_success @ 29 (elapsed 29); tail_success @ 26 (elapsed 26) | False |
| native | 0 / `19500b83bc34ba815f437cac0e88f87bd1e7facf02935efc430346109587945b` | 0.38238579 / 9 | 0.418975472 / 12 | [1, 1] | tail_success @ 37 (elapsed 37); tail_success @ 49 (elapsed 49) | False |
| A | 7 / `314514c3ca1d4274936b1d1ac963f7493350e0c9e319345158a050132d75b21b` | 0.375277311 / 7 | 0.383263856 / 9 | [1, 1] | tail_success @ 38 (elapsed 38); tail_success @ 31 (elapsed 31) | False |
| B | 9 / `149a8e33b797cf0237e18c421e746178a56154977dfdae4a926d8ff7b7a3c1c0` | 0.538200796 / 10 | 0.188677698 / 2 | [1, 1] | tail_success @ 35 (elapsed 35); tail_success @ 50 (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0.813232027 / 0.813232081; goal-direction term 0.530806414; squared-error term 0.282425667; algebra residual 3.33066907e-16; saved-minus-float64 -5.36935544e-08.
Mean squared error energy 60877.8074 = common 36464.2422 + specific 24413.5653; coordinate MSE 0.808856923; energy identity residual 0.

### reacher / dinowm_noprop / source 13 (WM-DIAG0-A2-v1:reacher:root-013)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `3e72a9d6455652f9d0beabfcea02feebcc41fd35217e02ae59404a1535ca4568`; accepted output seal `6aaf941d94dbe76aff8a8c820c1b4d16cdf1e5611a7993e3f26d3a19402fca3c`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `0aea4c1d920877b783852ac29cdb906aca428f2412330b102144964c0288a709` | 0.346857816 / 1 | 0.513108611 / 4 | [1, 1] | tail_success @ 50 (elapsed 50); tail_success @ 50 (elapsed 50) | False |
| O0 | 12 / `1afec3b2fbce5b097afececfc3526615154cae605dcd922ffc32dee58c805472` | 0.6798895 / 13 | 0.0458529294 / 1 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| native | 0 / `f2a497cd8628a13bb7089c61a21eeccbdf92d151642c196b40f00d8f10b47157` | 0.347040385 / 4 | 0.567236423 / 8 | [1, 1] | tail_success @ 50 (elapsed 50); tail_success @ 48 (elapsed 48) | False |
| A | 5 / `9d636462a0f90fa11f3b6440a9a913ab5416d3994dbe42306c117fbed4b3c5e6` | 0.34734267 / 6 | 0.525057673 / 6 | [1, 1] | tail_success @ 46 (elapsed 46); tail_success @ 48 (elapsed 48) | False |
| B | 5 / `9d636462a0f90fa11f3b6440a9a913ab5416d3994dbe42306c117fbed4b3c5e6` | 0.34734267 / 6 | 0.525057673 / 6 | [1, 1] | tail_success @ 46 (elapsed 46); tail_success @ 48 (elapsed 48) | False |

Selected-pair ordering error (saved / float64): 0.800287366 / 0.800287394; goal-direction term 0.923312231; squared-error term -0.123024838; algebra residual -2.22044605e-16; saved-minus-float64 -2.76705003e-08.
Mean squared error energy 60940.3231 = common 40902.0833 + specific 20038.2398; coordinate MSE 0.809687541; energy identity residual -7.27595761e-12.

### reacher / dinowm_noprop / source 14 (WM-DIAG0-A2-v1:reacher:root-014)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `2dbeefdadeb9d5b76442fe66d2ec2c975eb814d90b09d977bfffdfa076e32ee7`; accepted output seal `43c6bbda7a6e773be68136b908b38cba0d4dc574eb801a660122041c9ffefaf2`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `c4a36d6ca31aebef51c5f8a3ff38cd2f15018d5759436058a176974fc8346c67` | 0.46235624 / 1 | 0.0462533012 / 8 | [1, 1] | prefix_success @ 20 (elapsed 20); prefix_success @ 20 (elapsed 20) | True |
| O0 | 5 / `85ed25d52047a06a2016c096bbcaee99cce370233f003349df09095e45f5d6e1` | 0.465158373 / 5 | 0.0243405066 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `f239127827c303817d1826dd27602b4b1010b1e85c7d027b89ca2e0ca199558a` | 0.475467384 / 9 | 0.0265112743 / 2 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| A | 1 / `c4a36d6ca31aebef51c5f8a3ff38cd2f15018d5759436058a176974fc8346c67` | 0.46235624 / 1 | 0.0462533012 / 8 | [1, 1] | prefix_success @ 20 (elapsed 20); prefix_success @ 20 (elapsed 20) | True |
| B | 0 / `f239127827c303817d1826dd27602b4b1010b1e85c7d027b89ca2e0ca199558a` | 0.475467384 / 9 | 0.0265112743 / 2 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 0.0247149281 / 0.0247148852; goal-direction term 0.0335289488; squared-error term -0.0088140636; algebra residual 8.32667268e-17; saved-minus-float64 4.29044645e-08.
Mean squared error energy 41427.5268 = common 30735.0036 + specific 10692.5232; coordinate MSE 0.550429512; energy identity residual 0.

### reacher / dinowm_noprop / source 15 (WM-DIAG0-A2-v1:reacher:root-015)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `84b3a8cc1b8a0fd6d333301e09528f9a32db721f39c0c737c782c193d20e4fc3`; accepted output seal `c9f908d6d72df7a6d2d852c62d306a6f5f89aef6bb925c9bacd6ae7a42dfcd7b`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `59573f75f22a1a4b5e8182672dd8275b5ba435449e3060c46e2b97d77c7279f7` | 0.400026321 / 1 | 0.0542039275 / 6 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| O0 | 7 / `cba0058087dd61ad4e13084c74670efc247d38680e51a827410bb2c885839314` | 0.40093419 / 7 | 0.0150110358 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `dbba2c9f15b943771402b1e162a490e9c5ed6c08f00301b7f378b5aa05118c26` | 0.407844156 / 9 | 0.207956716 / 11 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| A | 0 / `dbba2c9f15b943771402b1e162a490e9c5ed6c08f00301b7f378b5aa05118c26` | 0.407844156 / 9 | 0.207956716 / 11 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| B | 7 / `cba0058087dd61ad4e13084c74670efc247d38680e51a827410bb2c885839314` | 0.40093419 / 7 | 0.0150110358 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 0.0401007598 / 0.0401007496; goal-direction term 0.0558221062; squared-error term -0.0157213566; algebra residual 1.38777878e-17; saved-minus-float64 1.02151175e-08.
Mean squared error energy 38927.4468 = common 27489.7318 + specific 11437.715; coordinate MSE 0.517212038; energy identity residual 0.

### reacher / dinowm_noprop / source 16 (WM-DIAG0-A2-v1:reacher:root-016)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `53e4f081a4da0efc00c0394a88eae507c0072d5cb16bc7049ca7e0f1c54cd712`; accepted output seal `9037c24411e96c600a5d64b693b63e19cd4da90d5327dcf1bf9f51cedd708bf7`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `8f854a1763acb90b300e0846298e9ee881bbacc2e2db2f61ea57942db158d359` | 0.353018671 / 1 | 0.176670045 / 6 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| O0 | 3 / `c1ae703d2cd5a6363ec210b827fd57cff5d72270b42f59911e2304b4a0932049` | 0.354327798 / 3 | 0.0251443628 / 1 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| native | 0 / `8bbe9edc0072786b439427f93de7c14666e933c262ef734a6c32b1cba5afd4c6` | 0.36936155 / 9 | 0.176444516 / 5 | [1, 1] | tail_success @ 30 (elapsed 30); tail_success @ 47 (elapsed 47) | False |
| A | 2 / `8ad5f4762dc0a07d24ac87d0935050dc6efa50682ead351720fa4263ddcd0efe` | 0.354130536 / 2 | 0.319288224 / 12 | [1, 0] | tail_success @ 30 (elapsed 30); failure @ None (elapsed 50) | False |
| B | 10 / `3c34c0780976353eb23e6099020d2da92eb7880351bed706b1989b27db2b9ee3` | 0.583701253 / 11 | 0.0301011428 / 2 | [1, 1] | prefix_success @ 20 (elapsed 20); prefix_success @ 20 (elapsed 20) | True |

Selected-pair ordering error (saved / float64): 0.152834808 / 0.152834842; goal-direction term 0.249441758; squared-error term -0.0966069167; algebra residual -1.66533454e-16; saved-minus-float64 -3.30748606e-08.
Mean squared error energy 45156.2357 = common 28886.2833 + specific 16269.9525; coordinate MSE 0.599971245; energy identity residual 0.

### reacher / dinowm_noprop / source 17 (WM-DIAG0-A2-v1:reacher:root-017)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `0b2da43a90e8ea47e26ff7190d2652b84ffea2f79e51b5d912c48ef9c9550b36`; accepted output seal `ce353defdd2339a45805ff8114e549d6695ea00171ef19318c30835e29f5db8c`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `10ccf9d608ff823b280bd1e42325d938c2c4ed138ee62b30ab0fd7bba6e8a764` | 0.433429122 / 1 | 0.169478089 / 3 | [0, 1] | failure @ None (elapsed 50); tail_success @ 29 (elapsed 29) | False |
| O0 | 14 / `c0ad2872d72c0395017c60218d65e02ecd2234b118306ca1214bb4a68faabdde` | 1.07468069 / 15 | 0.0390524305 / 1 | [1, 1] | prefix_success @ 16 (elapsed 16); prefix_success @ 16 (elapsed 16) | True |
| native | 0 / `9149a77426031fe56afb70ca09fbc685cd5cd3833cec3a1609e8e93d6bb462ad` | 0.437395453 / 9 | 0.273545504 / 6 | [1, 1] | tail_success @ 27 (elapsed 27); tail_success @ 41 (elapsed 41) | False |
| A | 5 / `c619cee4dfd370ca3c02c4ee2af6fafd5c8c3f58d78e18099a52e06d5cba9f15` | 0.434237003 / 5 | 0.116414927 / 2 | [0, 1] | failure @ None (elapsed 50); tail_success @ 27 (elapsed 27) | False |
| B | 1 / `10ccf9d608ff823b280bd1e42325d938c2c4ed138ee62b30ab0fd7bba6e8a764` | 0.433429122 / 1 | 0.169478089 / 3 | [0, 1] | failure @ None (elapsed 50); tail_success @ 29 (elapsed 29) | False |

Selected-pair ordering error (saved / float64): 0.771677222 / 0.771677158; goal-direction term 0.292129301; squared-error term 0.479547857; algebra residual 2.22044605e-16; saved-minus-float64 6.40085418e-08.
Mean squared error energy 54110.209 = common 36368.011 + specific 17742.198; coordinate MSE 0.718938789; energy identity residual 1.45519152e-11.

### reacher / dinowm_noprop / source 18 (WM-DIAG0-A2-v1:reacher:root-018)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `7a294e161ef521e746de75fb25c84f68b4e60be12dddef4027062b0514d5dd77`; accepted output seal `ac95928488906a5ebc5c28cebae205dc7835c3484a3a7ae4c2592fad721a0583`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `242f410d4ecd6175a4fcf9e58365bd12dc6e942a9cb79a99c55ac2a423d03e18` | 0.339156538 / 1 | 0.290184438 / 6 | [1, 1] | tail_success @ 31 (elapsed 31); tail_success @ 50 (elapsed 50) | False |
| O0 | 6 / `22a16b0e4f7b58be9336bafdf3263c1f973ad5004de9f21f4544cb3bd91467be` | 0.340867937 / 6 | 0.0197509024 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| native | 0 / `09b4462603db85af1bb21719580b8b4aa476e03e0fbd02167b7176181fc39db6` | 0.349812001 / 9 | 0.293263048 / 8 | [1, 1] | tail_success @ 50 (elapsed 50); tail_success @ 49 (elapsed 49) | False |
| A | 3 / `daaac2bc699b7e431dfbfb82e9ab5cb996bcdd4a6f40685562bb168272f1becf` | 0.339941621 / 3 | 0.0644109026 / 2 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| B | 6 / `22a16b0e4f7b58be9336bafdf3263c1f973ad5004de9f21f4544cb3bd91467be` | 0.340867937 / 6 | 0.0197509024 / 1 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |

Selected-pair ordering error (saved / float64): 0.272144934 / 0.27214495; goal-direction term 0.525145886; squared-error term -0.253000936; algebra residual 1.66533454e-16; saved-minus-float64 -1.56888488e-08.
Mean squared error energy 41985.804 = common 27735.6 + specific 14250.204; coordinate MSE 0.557847098; energy identity residual -1.45519152e-11.

### reacher / dinowm_noprop / source 19 (WM-DIAG0-A2-v1:reacher:root-019)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `4f102d3d48295e20864249ee0f7dbe773a45c0c78189e4d53f7be7e25817258e`; accepted output seal `0b2091fa19274b027e5f01410806183a86eee86ca15e1507a78f40d513f008e8`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `b8671eb50a27323f2b825e095137dba95e048768182bc053a8006eb6f2d0c582` | 0.372998774 / 1 | 0.265773624 / 6 | [1, 0] | tail_success @ 50 (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 12 / `a6c5ab82cf001859dd439e22298c7c4e40f157a5b32e6a6fd9aa2ed820844f13` | 0.701576889 / 13 | 0.140997663 / 1 | [1, 0] | tail_success @ 37 (elapsed 37); failure @ None (elapsed 50) | False |
| native | 0 / `a17c4b43f49bfc22417159172f45356ee59adf1c856251e845e81543b555394c` | 0.381507725 / 9 | 0.239364028 / 3 | [0, 1] | failure @ None (elapsed 50); tail_success @ 48 (elapsed 48) | False |
| A | 0 / `a17c4b43f49bfc22417159172f45356ee59adf1c856251e845e81543b555394c` | 0.381507725 / 9 | 0.239364028 / 3 | [0, 1] | failure @ None (elapsed 50); tail_success @ 48 (elapsed 48) | False |
| B | 0 / `a17c4b43f49bfc22417159172f45356ee59adf1c856251e845e81543b555394c` | 0.381507725 / 9 | 0.239364028 / 3 | [0, 1] | failure @ None (elapsed 50); tail_success @ 48 (elapsed 48) | False |

Selected-pair ordering error (saved / float64): 0.453354076 / 0.45335409; goal-direction term 0.481673383; squared-error term -0.0283192933; algebra residual -5.55111512e-17; saved-minus-float64 -1.39970421e-08.
Mean squared error energy 47273.2975 = common 31754.4521 + specific 15518.8454; coordinate MSE 0.628099723; energy identity residual 7.27595761e-12.

### reacher / dinowm_noprop / source 20 (WM-DIAG0-A2-v1:reacher:root-020)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `75e59cb6f28a03fbceb8ad9d5c3a46a8263625175ee3e2337d1b284b6ca916bc`; accepted output seal `4984f25cfc0c6af36dbc2d2d4ca39feb469a0df433c6015bee697ca2df818372`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `b22fcd164a8eb5690872301986c7bb6a25b0d3141ccf59d7ff34672a503b6fd6` | 0.384571344 / 1 | 0.0699569136 / 6 | [1, 1] | tail_success @ 40 (elapsed 40); tail_success @ 33 (elapsed 33) | False |
| O0 | 3 / `4d340bc02fbe576bca68257f2bb5f8e49eafcd500c49a01f11f3e0653e0683e7` | 0.385128677 / 3 | 0.0533781424 / 1 | [1, 1] | tail_success @ 45 (elapsed 45); tail_success @ 28 (elapsed 28) | False |
| native | 0 / `351f2491a67f837cbecbb12a1ea3d66ebbd2c3584fceb2c9b4633681fa895551` | 0.386622429 / 9 | 0.0736036375 / 7 | [1, 1] | tail_success @ 40 (elapsed 40); tail_success @ 28 (elapsed 28) | False |
| A | 6 / `cbb7e5b3224bde445f01f60cc59be865b33ce20388c4520789a4e4868adf085e` | 0.385665357 / 6 | 0.0628217831 / 4 | [1, 1] | tail_success @ 43 (elapsed 43); tail_success @ 28 (elapsed 28) | False |
| B | 6 / `cbb7e5b3224bde445f01f60cc59be865b33ce20388c4520789a4e4868adf085e` | 0.385665357 / 6 | 0.0628217831 / 4 | [1, 1] | tail_success @ 43 (elapsed 43); tail_success @ 28 (elapsed 28) | False |

Selected-pair ordering error (saved / float64): 0.0171361044 / 0.0171361122; goal-direction term 0.0297107661; squared-error term -0.0125746539; algebra residual 5.55111512e-17; saved-minus-float64 -7.80571085e-09.
Mean squared error energy 35168.2391 = common 25687.0565 + specific 9481.18264; coordinate MSE 0.467265082; energy identity residual 0.

### reacher / dinowm_noprop / source 21 (WM-DIAG0-A2-v1:reacher:root-021)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `3bf2666e9ffc9751e1ffd6cbae01980aeca430839edaecf8454ef8a5e3709ced`; accepted output seal `ba934acceb0976db4f9705a45edeb380779f9d4d1700f2caf494f3e0662789d6`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `ddd2bf3938f9e7f071ec905cde60703320bf456d76da5482bfe934c650f6d974` | 0.391607285 / 1 | 0.0351443738 / 2 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| O0 | 14 / `9e239e10008c3ea976b9a58d32f6c778c613d5e83660530bfc97181c5317e05b` | 1.28991055 / 15 | 0.0145336008 / 1 | [1, 1] | prefix_success @ 16 (elapsed 16); prefix_success @ 16 (elapsed 16) | True |
| native | 0 / `6f3133e3b4e257d3279de5a7072260edcb71d707d4b64097d1afe212bdfabd92` | 0.394307673 / 9 | 0.190340087 / 9 | [1, 1] | tail_success @ 45 (elapsed 45); tail_success @ 43 (elapsed 43) | False |
| A | 1 / `ddd2bf3938f9e7f071ec905cde60703320bf456d76da5482bfe934c650f6d974` | 0.391607285 / 1 | 0.0351443738 / 2 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |
| B | 14 / `9e239e10008c3ea976b9a58d32f6c778c613d5e83660530bfc97181c5317e05b` | 1.28991055 / 15 | 0.0145336008 / 1 | [1, 1] | prefix_success @ 16 (elapsed 16); prefix_success @ 16 (elapsed 16) | True |

Selected-pair ordering error (saved / float64): 0.918914043 / 0.918913952; goal-direction term 0.0392956121; squared-error term 0.87961834; algebra residual 5.55111512e-16; saved-minus-float64 9.12181529e-08.
Mean squared error energy 47365.4456 = common 29750.7003 + specific 17614.7453; coordinate MSE 0.629324054; energy identity residual 0.

### reacher / dinowm_noprop / source 22 (WM-DIAG0-A2-v1:reacher:root-022)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `510dca7c344ae4827a07068f25d67473e516c99af69e1c67eabf67f886ad1887`; accepted output seal `482856d4eb646eac2651e40228e9bdbe673d371f0e495c4aef2b2368a250a108`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `1ad0a9718a01066144dc696393ff28a82945ba92f3f0c8d3b523d3f93e7366ee` | 0.293642402 / 1 | 0.326982349 / 9 | [1, 0] | tail_success @ 30 (elapsed 30); failure @ None (elapsed 50) | False |
| O0 | 15 / `2d755aecf6952aa6b339b28a229092e94cf2f4b9afd9d6c2232a34b52b1443d6` | 1.85602009 / 16 | 0.031667646 / 1 | [1, 1] | prefix_success @ 4 (elapsed 4); prefix_success @ 4 (elapsed 4) | True |
| native | 0 / `db32fc3b9e49047f34c5da94766f5677b46cb88170c0de345c587e0faffbcb5e` | 0.29754284 / 9 | 0.381716102 / 11 | [1, 0] | tail_success @ 50 (elapsed 50); failure @ None (elapsed 50) | False |
| A | 4 / `52a6e19698d966eb2a708868199308fdc94b4a84d230db880801c62e3781b2af` | 0.293856025 / 4 | 0.35155651 / 10 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 15 / `2d755aecf6952aa6b339b28a229092e94cf2f4b9afd9d6c2232a34b52b1443d6` | 1.85602009 / 16 | 0.031667646 / 1 | [1, 1] | prefix_success @ 4 (elapsed 4); prefix_success @ 4 (elapsed 4) | True |

Selected-pair ordering error (saved / float64): 1.85769239 / 1.85769259; goal-direction term 0.587530347; squared-error term 1.27016225; algebra residual 0; saved-minus-float64 -2.00166974e-07.
Mean squared error energy 54278.7644 = common 27764.8009 + specific 26513.9636; coordinate MSE 0.721178311; energy identity residual -7.27595761e-12.

### reacher / dinowm_noprop / source 23 (WM-DIAG0-A2-v1:reacher:root-023)

Original stratum: gain; action-choice changed: True; O0−P0: +100.000 pp. Source `6cc4deab9f30b7602aa537f7f5ef3ed11a4d61eaa81fb05fd501262b6610e529`; accepted output seal `708e02b8ee2d534ab8982cd4b559d374fde297a32f27a2027c83bddb108a8c5e`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `a3512d795b584a0d629f0a097be5608dc5e467c5d20f771ee683825878b70471` | 0.386593372 / 1 | 0.0720385462 / 11 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 0 / `0226d092dce491b3eb6d669d3e4cdfed8faed14669bc139a8acfe1286479f662` | 0.437051147 / 9 | 0.0103157405 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `0226d092dce491b3eb6d669d3e4cdfed8faed14669bc139a8acfe1286479f662` | 0.437051147 / 9 | 0.0103157405 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| A | 3 / `5ce32fc5ac417000882e6a7296dd7b95adb67684b4c000727c3d83916d8ac334` | 0.388121814 / 3 | 0.0266248751 / 4 | [1, 1] | prefix_success @ 23 (elapsed 23); prefix_success @ 23 (elapsed 23) | True |
| B | 6 / `24cff2aaaab09f58107b1f2c714ec28a0a89dc08047540e8d9f9d9cac5572f1b` | 0.388804108 / 6 | 0.0196445137 / 3 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 0.112180581 / 0.112180576; goal-direction term 0.131442473; squared-error term -0.0192618966; algebra residual -8.32667268e-17; saved-minus-float64 4.85299634e-09.
Mean squared error energy 34849.7117 = common 26771.3236 + specific 8078.38812; coordinate MSE 0.463032946; energy identity residual 0.

### reacher / dinowm_noprop / source 24 (WM-DIAG0-A2-v1:reacher:root-024)

Original stratum: gain; action-choice changed: True; O0−P0: +100.000 pp. Source `0edbea7d4ce6d253ae177bb83f90c3e028f42e1f09a92d1b423d146f778b0ca7`; accepted output seal `3f4dafd7a5ae6632d2996624b895ffd9554db7412d4f6442d4ebd3d670b3b8b2`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `abbe741310a7e5166431f189222bc4c7b45be27f8625e29b281e74fdaf6ff023` | 0.372609824 / 1 | 0.567016602 / 12 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| O0 | 10 / `620cac6e371f1734f7818e120d48206672337ea6e770a22964f86ce9f53af441` | 0.59231174 / 11 | 0.0453633666 / 1 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 43 (elapsed 43) | False |
| native | 0 / `a571024a48318e7ec8f512bb095f4aa0526ab5b3f6d01810963a970ca4e41c41` | 0.379420072 / 9 | 0.557022989 / 11 | [1, 0] | tail_success @ 43 (elapsed 43); failure @ None (elapsed 50) | False |
| A | 4 / `f3d6727a9ea1628462d38a2e9caf89462a4d550313396845295ac0591f49a479` | 0.372765571 / 4 | 0.156141266 / 3 | [1, 1] | tail_success @ 29 (elapsed 29); tail_success @ 48 (elapsed 48) | False |
| B | 10 / `620cac6e371f1734f7818e120d48206672337ea6e770a22964f86ce9f53af441` | 0.59231174 / 11 | 0.0453633666 / 1 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 43 (elapsed 43) | False |

Selected-pair ordering error (saved / float64): 0.741355151 / 0.741355235; goal-direction term 0.874861389; squared-error term -0.133506154; algebra residual 0; saved-minus-float64 -8.43739556e-08.
Mean squared error energy 57726.7823 = common 35321.6667 + specific 22405.1156; coordinate MSE 0.766990623; energy identity residual 0.

### reacher / dinowm_noprop / source 25 (WM-DIAG0-A2-v1:reacher:root-025)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `4dcc097afb5e6e94325be426f88621e24c81f702883c43131c48702e5e9e17d0`; accepted output seal `9ced244faa6e4b3274f074d0e6eb24d6b48b3cb780b5e9148f1c093999ff26f8`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `a685ff431075c6f8e2bd1c0bd1c3b04f6d82c7d205bbb4b578c0d760c5a094f1` | 0.349831611 / 1 | 0.0489799343 / 5 | [1, 1] | prefix_success @ 15 (elapsed 15); prefix_success @ 15 (elapsed 15) | True |
| O0 | 8 / `49e3026ef27f41f8abbd9fc15dfd6ef6cadabd15c970aae1b0bc18b2bdc06880` | 0.350466818 / 8 | 0.0239786934 / 1 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| native | 0 / `16a50af8efdd7e12bdbd45c36074496db84b447837caf61e74f4dbf81e7d409d` | 0.351537704 / 9 | 0.033063218 / 4 | [1, 1] | prefix_success @ 17 (elapsed 17); prefix_success @ 17 (elapsed 17) | True |
| A | 5 / `ec7ab1ca299f9f3fecfe5417ba0f3e1ffffaa9228da8993f12b6d9f6a378517c` | 0.350120187 / 5 | 0.0319485888 / 3 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| B | 2 / `c6ab9563df1098787b226dd5f21372110757742e8be779d3a256c8355220e2b0` | 0.349918216 / 2 | 0.027221594 / 2 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |

Selected-pair ordering error (saved / float64): 0.0256364476 / 0.0256364492; goal-direction term 0.0376280852; squared-error term -0.0119916359; algebra residual -4.85722573e-17; saved-minus-float64 -1.64568751e-09.
Mean squared error energy 31219.4791 = common 23885.4793 + specific 7333.99978; coordinate MSE 0.414799626; energy identity residual 3.63797881e-12.

### reacher / dinowm_noprop / source 26 (WM-DIAG0-A2-v1:reacher:root-026)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `2c9651332b24ecaee30eb38df421b2aad4cede6c2dc71364efb6e5f89aaeaf90`; accepted output seal `2457a7e45730f45f8378a804a809778a0a3d1b14cfe3c7f193e138fd04bcacd6`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `1e55ef76610718cf77fa1be4e638871e730517d3630595826d0281fcfaab6841` | 0.397332966 / 1 | 0.0120560909 / 1 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| O0 | 1 / `1e55ef76610718cf77fa1be4e638871e730517d3630595826d0281fcfaab6841` | 0.397332966 / 1 | 0.0120560909 / 1 | [1, 1] | prefix_success @ 21 (elapsed 21); prefix_success @ 21 (elapsed 21) | True |
| native | 0 / `daf3ea226d598ecf66b264260bb9b03c470269946d9ef5a72ce092c8d5c0dd6f` | 0.39788729 / 9 | 0.046891097 / 7 | [1, 1] | prefix_success @ 16 (elapsed 16); prefix_success @ 16 (elapsed 16) | True |
| A | 7 / `99b9b8838bfe0b18f4d08e27dcd017b4900d9b2f4e9a31fa138f6748e890b44c` | 0.397661269 / 7 | 0.0707533136 / 8 | [1, 1] | prefix_success @ 16 (elapsed 16); prefix_success @ 16 (elapsed 16) | True |
| B | 6 / `69f0b6fdf7c79aed315a0621fb584887dbdae3d349365483aa96c8ad6e1fba07` | 0.397618026 / 6 | 0.0217255075 / 3 | [1, 1] | prefix_success @ 16 (elapsed 16); prefix_success @ 16 (elapsed 16) | True |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 36135.6273 = common 28115.3875 + specific 8020.23975; coordinate MSE 0.480118347; energy identity residual 0.

### reacher / dinowm_noprop / source 27 (WM-DIAG0-A2-v1:reacher:root-027)

Original stratum: tie; action-choice changed: False; O0−P0: +0.000 pp. Source `bf664f4658f1daf41606714378f5244268b2fe6f18fecff620a9c69c9d277714`; accepted output seal `4ec803e40c0faf96ccf902760324deddf613ca9b40e7a68f5019b09fc127a333`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `4ad166707dc6d1b47625c254ef7ecbfc2634e198d51c5940314c95d0fec0d60f` | 0.381877929 / 1 | 0.0119256573 / 1 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| O0 | 1 / `4ad166707dc6d1b47625c254ef7ecbfc2634e198d51c5940314c95d0fec0d60f` | 0.381877929 / 1 | 0.0119256573 / 1 | [1, 1] | prefix_success @ 22 (elapsed 22); prefix_success @ 22 (elapsed 22) | True |
| native | 0 / `c7eadf2bb6698b576e2460d324e1c73b65182636f89c6918b185a173b8a3bc7a` | 0.390697509 / 9 | 0.102011241 / 8 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 8 / `fab8dadd22c6f669464a74e9dbf1c45811cd1eb5f3864fea8b09b60b4e65856a` | 0.383582413 / 8 | 0.0769937709 / 5 | [1, 1] | tail_success @ 26 (elapsed 26); tail_success @ 31 (elapsed 31) | False |
| B | 14 / `18846d7c20242349dd6b7366c6060e32754616bb4f7388b11222514984bdfd8c` | 0.977751136 / 15 | 0.0425305478 / 2 | [1, 1] | prefix_success @ 19 (elapsed 19); prefix_success @ 19 (elapsed 19) | True |

Selected-pair ordering error (saved / float64): 0 / 0; goal-direction term 0; squared-error term 0; algebra residual 0; saved-minus-float64 0.
Mean squared error energy 40287.9569 = common 27260.2117 + specific 13027.7452; coordinate MSE 0.535288543; energy identity residual 0.

### reacher / dinowm_noprop / source 28 (WM-DIAG0-A2-v1:reacher:root-028)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `829459fb859b9669b67e56fc5eaea938eb064ab57b469b1775994d65b192528c`; accepted output seal `ebd0999f414b8a8f31b3dbbef8efc8b44495be528ffb3da658c91bc6f12bfd5a`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `0c82658ca72766935c2b7267c82e9659b40dd4c4681e1b65717cda79bc52837a` | 0.415977687 / 1 | 0.021310024 / 2 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| O0 | 10 / `9586da7355deadf3141fe357cd47c0c1cb9c9c4071faae4d2d646f8b1e56d86c` | 0.498705745 / 11 | 0.0147374012 / 1 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| native | 0 / `cc0c7c878e475943696157b53335f3ac1762f065d727aec1db2008e355fb433c` | 0.416667581 / 9 | 0.0843305513 / 11 | [0, 1] | failure @ None (elapsed 50); tail_success @ 26 (elapsed 26) | False |
| A | 5 / `73cb9a8678730efb498fd9cb28e1f1fdade791a73386574ebef9f0f03297d8e1` | 0.416155219 / 5 | 0.0677101165 / 9 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| B | 8 / `b7e3b9f33b9b3fcb74a540c46690dff9f2123bd2c633dace93ef03ab34d475e4` | 0.4162817 / 8 | 0.0310447514 / 4 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |

Selected-pair ordering error (saved / float64): 0.0893006809 / 0.089300701; goal-direction term 0.00894720396; squared-error term 0.080353497; algebra residual 1.38777878e-17; saved-minus-float64 -2.00833049e-08.
Mean squared error energy 37209.2156 = common 29838.318 + specific 7370.89762; coordinate MSE 0.494382648; energy identity residual 0.

### reacher / dinowm_noprop / source 29 (WM-DIAG0-A2-v1:reacher:root-029)

Original stratum: tie; action-choice changed: True; O0−P0: +0.000 pp. Source `a7753438b8ae2d0ee81c0c0acc39710ff9bdcd8202ebb98326e8d602f8ae4b22`; accepted output seal `a3c48348534cc48992eb8c1ebcc75fff70fb95c52ea39e137b16d138cfc87430`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `c55a9b58337cc17e4c374958711901286fa0dbb64e39cb67fcfff95a79d4688e` | 0.370799869 / 1 | 0.179446682 / 2 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |
| O0 | 10 / `cc18e825ce29b0d1b3922b32be5eaf66cf9b51387e40df2ffaec2f79fd54c0f6` | 0.67625165 / 11 | 0.100259729 / 1 | [1, 1] | prefix_success @ 15 (elapsed 15); prefix_success @ 15 (elapsed 15) | True |
| native | 0 / `f184be49ce939248c7c618b4aca84bbd9f90f09dec6dfb1e436d0aa0dd1c31a9` | 0.374034882 / 9 | 0.223975405 / 6 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| A | 0 / `f184be49ce939248c7c618b4aca84bbd9f90f09dec6dfb1e436d0aa0dd1c31a9` | 0.374034882 / 9 | 0.223975405 / 6 | [1, 1] | prefix_success @ 25 (elapsed 25); prefix_success @ 25 (elapsed 25) | False |
| B | 1 / `c55a9b58337cc17e4c374958711901286fa0dbb64e39cb67fcfff95a79d4688e` | 0.370799869 / 1 | 0.179446682 / 2 | [1, 1] | prefix_success @ 24 (elapsed 24); prefix_success @ 24 (elapsed 24) | True |

Selected-pair ordering error (saved / float64): 0.384638734 / 0.384638724; goal-direction term 0.0994631535; squared-error term 0.285175571; algebra residual -1.66533454e-16; saved-minus-float64 9.72676367e-09.
Mean squared error energy 41941.5473 = common 30291.0822 + specific 11650.4651; coordinate MSE 0.557259079; energy identity residual 0.

### reacher / dinowm_noprop / source 30 (WM-DIAG0-A2-v1:reacher:root-030)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `71140efcd57a375fffa561aa6d636c9cf795d4ab767f0cb614343c9c2eaa8b91`; accepted output seal `f1a3c80c67f7c1a6c9610d0439ea29ff80b614e048001092705a251fae459f8a`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `c61de0eda492c4b22aedf1e43801ba1ecec72c686e70b2eddf6068eb523dccf3` | 0.35896495 / 1 | 0.141622737 / 6 | [0, 1] | failure @ None (elapsed 50); tail_success @ 44 (elapsed 44) | False |
| O0 | 12 / `ee0df83ee4feb8b745d9d96ffe207d5747980e6be9ea5c18220c997248235398` | 0.822585344 / 13 | 0.0709271282 / 1 | [1, 1] | prefix_success @ 20 (elapsed 20); prefix_success @ 20 (elapsed 20) | True |
| native | 0 / `02dcbbfa3d31a4bccd933f686d6a3c4ec2211362f71a4b73f342bcadfe9cbb60` | 0.359585077 / 5 | 0.131725416 / 5 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| A | 1 / `c61de0eda492c4b22aedf1e43801ba1ecec72c686e70b2eddf6068eb523dccf3` | 0.35896495 / 1 | 0.141622737 / 6 | [0, 1] | failure @ None (elapsed 50); tail_success @ 44 (elapsed 44) | False |
| B | 2 / `21074bc146143b05c46cc14ed45bc610996da6065247eaf0ab519be7b4e3ddbd` | 0.358979344 / 2 | 0.121947177 / 2 | [1, 1] | tail_success @ 45 (elapsed 45); tail_success @ 40 (elapsed 40) | False |

Selected-pair ordering error (saved / float64): 0.534316003 / 0.534316031; goal-direction term 0.124719222; squared-error term 0.40959681; algebra residual -1.11022302e-16; saved-minus-float64 -2.79717894e-08.
Mean squared error energy 40976.4845 = common 27228.6261 + specific 13747.8584; coordinate MSE 0.54443671; energy identity residual 0.

### reacher / dinowm_noprop / source 31 (WM-DIAG0-A2-v1:reacher:root-031)

Original stratum: gain; action-choice changed: True; O0−P0: +50.000 pp. Source `60f0da5b72a464bc435947bd69a12a79bc770b7fffeba7cae63b1c7f2abab0a2`; accepted output seal `35cc8ebcc5f3b96d25b0494a4ab92e5f06ee9779fd265a1aedb2adede9fa14ab`.

| Role | Index / candidate ID | Predicted S0 / rank | Realized S0 / rank | Two outcomes | Draw phase / actual clocks | Oracle terminal absorbed |
|---|---|---|---|---|---|---|
| P0 | 1 / `a836f9c6d19a76ea2abe7185d2087cdc494a4669faa5b15a0c95c0fac7525829` | 0.356735229 / 1 | 0.407493532 / 5 | [1, 0] | tail_success @ 48 (elapsed 48); failure @ None (elapsed 50) | False |
| O0 | 9 / `d1a1af7b14ad0194c28c446e7d98d014098c9fb64b2feeb691e8b3e767b4979c` | 0.480983287 / 10 | 0.169376478 / 1 | [1, 1] | tail_success @ 50 (elapsed 50); tail_success @ 48 (elapsed 48) | False |
| native | 0 / `843f06c520e0cf87eb1f8148024c3e20d0d074e695b1d504a36f80eb928103ba` | 0.369737744 / 9 | 0.370211601 / 3 | [1, 1] | tail_success @ 48 (elapsed 48); tail_success @ 48 (elapsed 48) | False |
| A | 3 / `067de709a17ab7ba17133ea98d40c099ccc9ae61972519f4bde1a6e4bc5c55ec` | 0.359426379 / 3 | 0.412079573 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |
| B | 3 / `067de709a17ab7ba17133ea98d40c099ccc9ae61972519f4bde1a6e4bc5c55ec` | 0.359426379 / 3 | 0.412079573 / 6 | [0, 0] | failure @ None (elapsed 50); failure @ None (elapsed 50) | False |

Selected-pair ordering error (saved / float64): 0.362365112 / 0.362365093; goal-direction term 0.441322743; squared-error term -0.0789576496; algebra residual 2.77555756e-16; saved-minus-float64 1.85744269e-08.
Mean squared error energy 57598.2902 = common 38123.8126 + specific 19474.4776; coordinate MSE 0.765283405; energy identity residual -7.27595761e-12.

## Mechanism conclusion and at most one unlaunched proposal

### One mechanism conclusion

On these exposed banks, removing the bank-common forecast displacement alone is not sufficient to reproduce the Reacher realized-consequence advantage. The fixed candidate-specific correction is consistent with an important action-dependent goal-ordering error in Reacher/DINO, but the weaker Le-WM effect and adverse PushT results do not support one transferable repair mechanism. Much of the original Reacher advantage involves choosing chunks that already succeed within the first 25 actions, rather than demonstrating better continuing post-chunk dynamics.

This statement has concrete checks: the frozen A correction should produce no appreciable positive mean Reacher gain here, B should improve Reacher/DINO more clearly than Le-WM, and the original O0 advantage should be concentrated in increased prefix-success counts with fewer tail-success counts. The complete saved-data result satisfies those checks. A future independent-parent replication showing clear A gains in both Reacher systems, no B gain, or predominantly tail-only improvements would contradict extending this pattern beyond the current discovery banks. These are not post hoc confirmatory tests.

### Evidence and uncertainty

The original Reacher O0-P0 gains remain +20.3125 percentage points for Le-WM and +21.875 points for DINO. A, which removes the common vector while retaining candidate-specific errors, changes success by 0 points [descriptive paired 95% interval -17.1875, +17.1875] for Le-WM and +1.5625 [-9.375, +14.0625] for DINO. A has 6 gains/6 losses/20 ties and 4/5/23 respectively: cancellation and uncertainty are not proof that the common component never matters for any parent.

B, which removes candidate-specific error while retaining the common displacement, gives Le-WM +6.25 points [-3.125, +17.1875], with 4 gains/2 losses/26 ties, and DINO +17.1875 [+4.6875, +31.25], with 8/1/23. Their success rates are 78.125% and 90.625%, versus P0's 71.875% and 73.4375%. B agrees with the exact O0 candidate on only 6/32 and 12/32 parents; equal success is not identical choice. A agrees on 5/32 and 4/32. The stronger DINO result makes candidate-dependent ordering a plausible contributor, not a proven universal necessity or a learnable correction.

Common error accounts for a mean within-parent energy fraction of 54.635% in Reacher/Le-WM and 68.762% in Reacher/DINO. Its prevalence in squared error does not imply that common-error removal yields useful decisions. The selected P0/O0 pair's mean relative ordering error is 47.303261 in Le-WM sum units, comprising a +39.924339 goal-direction difference and +7.378922 squared-error difference. In DINO mean units it is 0.32407658, comprising +0.25747527 and +0.06660130. These signed differences explain the algebra of relative goal costs, not a causal partition of task success; units cannot be compared across representations. All parent strata and signed roundoff residuals are retained, including losses and unchanged choices.

### Prefix success, tail success and absorption

Across 64 recorded draws per setting, Reacher/Le-WM P0→O0 changes prefix successes 26→54, tail successes 20→5, and failures 18→5. Its +20.3125-point total change is the disjoint description +43.75 prefix points and -23.4375 tail points. The corresponding DINO counts are 26→50, 21→11, and 17→3: +37.5 prefix points and -15.625 tail points sum to +21.875. These categories overlap neither within a draw nor as a success definition, but their differences are not independent effects or causal shares.

The transitions make this more precise. Le-WM has 12 failure→prefix-success draws, 2 failure→tail-success, 16 tail→prefix, and 1 tail→failure. DINO has 11 failure→prefix-success, 3 failure→tail-success, 13 tail→prefix, and no new failed draws. Thus tail behavior contributes in some parents, but many changed choices recognize an already successful first chunk or replace a later success with an earlier one. A change from tail success to prefix success alone creates no full-budget success gain. For B in Reacher/DINO, +31.25 prefix points and -14.0625 tail points sum to its +17.1875-point change; Le-WM B has +6.25 prefix points and no tail-point change.

Post-stop absorbed terminal oracle features occur in 114/512 Le-WM and 116/512 DINO Reacher candidates. Selected P0→O0 absorbed-parent counts rise 13→23 and 11→19. These observations are retained, not excluded. The frozen feature after success/termination is legitimate under the original contract, but its discrepancy from a continuing forecast must not automatically be called an ordinary continuing-dynamics error. No new absorption-adjusted subset or correction has been searched.

### What PushT contradicts or leaves open

PushT A changes success by +1.5625 points in each backbone, with intervals [-10.9375, +14.0625] for Le-WM and [-4.6875, +9.375] for DINO. B changes success by -4.6875 [-14.0625, +1.5625] and -9.375 [-21.875, 0]. The original O0-P0 changes remain +9.375 and -3.125 points. Neither fixed correction establishes a positive PushT mechanism; B can be adverse even when it improves Reacher/DINO. Common energy is also substantial in PushT (mean within-parent fractions 60.513%/74.403%), again contradicting the shortcut from large common energy to a useful common-shift repair.

PushT O0 increases prefix-success counts but reduces tail-success counts; for DINO the +18.75 prefix-point change is outweighed by -21.875 tail points. Recognizing a successful first chunk and improving total success are therefore different claims. PushT was exposed during this follow-up and is not a held-out transfer test.

### Practical recommendation: do not choose one transferable repair yet

I recommend against selecting or implementing a practical learned repair from this result alone. In particular, neither a bank-common bias corrector nor a universal candidate-specific dynamics repair is justified across both Reacher systems and PushT. No new method is proposed or launched here.

Any later decision would need independent training/development data and new physical parent sources for evaluation; all current cohorts are exposed discovery. Deployment inputs must be limited to the current permitted observations/goal, candidate actions, and available predictor outputs—not candidate future states, oracle bank errors or tail outcomes. Learnability of the useful DINO correction cannot be inferred from its privileged retrospective construction. A diagnostic-transfer claim would additionally require a setting excluded from recommendation development.

Before preferring a more complicated mechanism, the matched simple explanation must be a direct first-chunk success/goal-score calibration using the same permitted inputs and added data/compute, compared with the unchanged planner. Such a scalar-cost intervention would be scoring/calibration, not repaired dynamics. This names a necessary conceptual control, not a second implemented or selected follow-up method. Evidence of equal gains from that simple control would undermine attributing any future benefit specifically to repaired feature dynamics. No architecture, fitting, collection or evaluation design is selected for execution now.

Both A and B use the tested bank's realized futures; neither is deployable. New intervals are descriptive source-paired discovery intervals, not confirmatory, multiplicity-controlled, independent across backbones or independent-training-seed evidence. Small finite candidate banks and two draws remain noisy. The original S1 coordinate-readout limitation does not establish that score learning generally cannot help. No physical/kernel cause, architecture-superiority, novelty or universal predictor diagnosis is claimed.


## Provenance and limitations

- Original publication: `4837834b15cffae1fd848108b8737187f4caee06`; frozen execution identity: `42b999a83358e1c6e3780a6bf5e3e16ee2209a88ee51977f3cf6c892b95c6f10`.
- One saved-data-only CPU job; no old estimator or intervals rerun, no model/physics/GPU/training/source/candidate-generation calls, no latent banks persisted.
- Corrected arrays use privileged tested-bank realized consequences and are cast once from float64 back to native saved dtype before the unchanged pure-array S0. Their usefulness does not establish learnability or a latent-manifold repair.
- Saved native/GPU choices remain authoritative; float64 algebra is a separate identity check, with every signed roundoff residual recorded. No near-tie historical choice is changed.
- Prefix absorption and early successes remain in the main result. Post-stop discrepancies are not automatically ordinary continuing-dynamics errors.
- Fixed small candidate banks and two draws are noisy; hindsight maxima are not expected optimal performance. No oracle-recovery percentage or additive success-cause fraction is reported.
- All current sources/settings are exposed discovery. A future practical repair needs independent new source parents, and a diagnostic-transfer claim also needs a setting excluded from recommendation development.
- S1 coordinate-readout weakness does not establish that scoring cannot help. Original DINO reproduction/representation-control, Le-WM scope, uncached-reference and unsaved-role-array limitations remain unchanged.
- Existing prior-art ledger only; no novelty claim or new literature search. No future pipeline or old monitor is launched.
