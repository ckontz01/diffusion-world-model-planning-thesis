# Active counterfactual feedback verification: local research attempt

This package is an original method-design attempt plus executable **artificial**
mechanism tests, not a robotics experiment, a faithful implementation of another
paper, or proof of literature novelty. Start with METHOD.md and PRIOR-ART.md.

## What is implemented

- `experiment.py`: joint response/outcome learning from artificial branched
  sources; static, passive, fixed-probe, oracle information-gain, active
  counterfactual-feedback, no-transfer and exact Bayes-oracle controls.
- `contrast_filter.py`: Gaussian contrast-sufficient observation compression and
  exact scalar expected-max acquisition. Established mathematical ingredients,
  isolated here as a possible implementation component.
- `tests.py`: 15 exact/invariance/data-boundary checks.
- `scale_check.py`: complete sample-size sensitivity and exact analytic grid.
- `check_compression.py`: dense-versus-compressed Gaussian consistency tests.
- `run-v1`, `sensitivity-v1`, `compression-v1`: configs written before their own
  runs and complete outputs. These are deliberately constructed mechanism tests,
  not preregistered independent evidence for the thesis.

NOT implemented: a trained neural Le-WM feedback operator, a robot/simulator
controller, production candidate-tree binding, literature native comparators,
real-data calibration, repeated-policy safety or actual task improvement.

## Local results

The main experiment has seven cases and30 fit seeds,1,024 independent artificial
training sources each. Every source has nine coupled branch outcome labels.
Test performance is calculated exactly from the known artificial outcome law;
it is not a finite held-out estimate or an observed robot success count.

Informative hidden-response case:
- static and passive:58.00% expected terminal success;
- fixed informative prefix and proposed active feedback:75.66%;
- active prefix but no response-dependent reranking:56.26%;
- entropy probe:56.71%; exact Bayesian contingent optimum:75.66%.

The fixed informative-prefix control MATCHES the proposal in that case. Active
selection matters across the other cases: the proposed rule avoids paying for
a test when the condition is already known, a response is uninformative, the
prefix is too costly, no decision-relevant uncertainty exists, or the mode
changes before the continuation. The fixed-probe control then loses utility.

A serious failure is retained: an unannounced reversal of response meaning
reduces the proposed rule to21.34%, versus58.00% static. The observable marginal
response is unchanged; there is no distribution-free detection guarantee.

A correctly specified generic Bayesian controller using the same joint model
makes the SAME contingent decisions. We explicitly test equality by exhaustive
enumeration. These tests isolate an information-acquisition capability; they do
NOT show a new decision theorem or a win over Bayes-optimal dual control.

Sample-size sensitivity: four sizes32/128/512/2048 ×100 fit seeds ×7cases =2,800
additional small table fits. Low-data errors can hurt even without distribution
shift. All cases/outputs are retained; no best seed or sample size is selected.
The exact2,550-cell signal-quality/prefix-cost grid agrees with the closed-form
tradeoff to2.22e-16. There are695 strictly beneficial cells; the other1,855 do not
justify testing. This is an exhaustive artificial grid, not a robotics benchmark.

The Gaussian component reduces192 observation coordinates to at most7 for8
candidate-mean comparisons under its specified joint Gaussian law. Across64
random laws/1,024 observations, maximum dense-versus-compressed contrast-mean
error was6.19e-13 and covariance error7.27e-14. A common-mode-only covariance
produces zero informative contrast dimensions. This does not prove that a
learned neural representation is sufficient in real tasks or guarantee latency.

## Reproduce

Python3 with NumPy is sufficient (local NumPy2.3.5). No PyTorch, simulator,
checkpoint, external data or GPU is used. The existing directory outputs are
exclusive; reproduce in a fresh copy or pass a new --out directory.

```
OPENBLAS_NUM_THREADS=1 python tests.py
OPENBLAS_NUM_THREADS=1 python experiment.py --out NEW-RUN
# scale_check/check_compression create fixed exclusive names: use fresh copy.
OPENBLAS_NUM_THREADS=1 python scale_check.py
OPENBLAS_NUM_THREADS=1 python check_compression.py
```

The approximately19.07million artificial binary labels across the main and
sample-size experiments are cheap, coupled, generated numbers. They are NOT
19million independent situations, research interactions or robot rollouts.
No claims of scientific scale are based on that count. Numerical runs took
seconds locally; most work was formulation, reasoning and primary-source review.

No worker action, research launch, protected-data access or protocol change is
implicitly authorized by this package. AV1 stays unlaunched and prior outcomes
stay unchanged. The next useful evidence is whether actual prefix residuals
predict unseen continuation differences beyond ordinary observed-state/history
features, under a fixed small robot-development design.
