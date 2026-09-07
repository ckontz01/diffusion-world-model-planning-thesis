# Independent PushT look 1: N=1600

Decision: **stop_futility_strong_adverse_signal**

|Arm|Mean success|H75|H150|
|---|---:|---:|---:|
|vad_continuation|16.30%|21.19%|11.42%|
|vad_greedy_300|14.09%|20.54%|7.65%|
|diagonal_gaussian_continuation|13.36%|17.44%|9.29%|
|vad_greedy_576|15.12%|21.44%|8.81%|
|direct_gmm_continuation|15.30%|19.38%|11.23%|
|sage|21.04%|26.48%|15.60%|

|Control|Difference (pp)|Lower bound at this look (pp)|Crossed now|
|---|---:|---:|---|
|vad_greedy_300|2.208|0.823|True|
|diagonal_gaussian_continuation|2.938|1.588|True|
|sage|-4.740|-6.532|False|

New independent weak-policy reachable-goal distribution; not original SAGE paper reproduction. Fixed checkpoint blocks, episode-level inference. All registered outcomes included.
