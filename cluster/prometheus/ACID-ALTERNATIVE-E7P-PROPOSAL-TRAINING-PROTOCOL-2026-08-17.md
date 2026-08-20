# E7P P1-only GDP-CEM proposal-training protocol

Date frozen: 2026-08-17  
Role: P1-only mechanism development  
Outcome access: no D2, D3, C1, or I1 data or outcomes may be read

## Inputs

Use only the three immutable E7P sequence caches derived under
`ACID-ALTERNATIVE-E7P-SEQUENCE-CACHE-PROTOCOL-2026-08-17.md` and their referenced
flat Le-WM latent caches. Preserve their episode-level P1 train/validation roles.

## Models

Train one task-specific model for each of these conditions with seed 6101:

1. `diffusion_true`: current latent, true t+25 goal latent, and true 25-action
   sequence;
2. `diffusion_shuffled_goal`: identical except for a deterministic nonzero
   cyclic derangement of goal rows separately within P1 train and P1 validation;
3. `gaussian_true`: a conditional diagonal-Gaussian action-sequence model using
   the same true inputs and capacity-matched backbone.

The joint action is represented as 25 primitive-action tokens. Latents use the
existing P1-training statistics recorded in the transition cache. A second
model-side primitive-action standardizer is fit on P1 train only and inverted
before planner integration.

Both proposal families use the same four-block FiLM residual MLP backbone:

- latent dimension 192;
- width 512;
- depth 4;
- timestep embedding dimension 128;
- condition `[z_current, z_goal, z_goal - z_current]`;
- complete flattened action trajectory as the modeled joint variable.

Diffusion uses epsilon prediction with a 100-level cosine schedule. No
classifier-free guidance or goal dropout is permitted in E7P. The Gaussian
control predicts a joint trajectory mean and diagonal log standard deviation,
clamped to `[-5, 2]` during training and inference.

## Optimization

- optimizer: AdamW, betas `(0.9, 0.999)`, weight decay `1e-4`;
- peak learning rate: `2e-4`;
- linear warmup: 1,000 steps, then cosine decay;
- batch size: 1,024;
- optimization steps: 30,000;
- gradient-norm clipping: 1.0;
- CUDA bfloat16 autocast with float32 loss accumulation;
- EMA decay: 0.999;
- validation every 1,000 steps on 8,192 fixed P1-validation rows;
- select the minimum fixed validation objective, breaking exact ties in favor
  of the earlier step.

The diffusion objective is mean squared epsilon error under a fixed validation
noise/timestep bank. The Gaussian objective is diagonal Gaussian negative log
likelihood. These objectives select checkpoints only within a model condition;
their numeric scales are not compared across proposal families.

## Required preflight and recorded outputs

- model forward, sampling, finiteness, and deterministic-DDIM tests;
- fixed-tiny-batch overfit for both proposal families;
- exact Gaussian-control reproduction of the released CEM sampler;
- checkpoint and source hashes;
- per-evaluation training trace, best step, parameter count, data counts,
  standardizers, derangement offsets, runtime, peak CUDA memory, and software
  versions;
- `protected_c1_i1_read=false`, `d2_read=false`, and `d3_read=false`.

Training these models authorizes no planner evaluation or claim. Proposal
fraction, DDIM inference steps, and refresh integration are selected in a later
P1-validation-only stage under a separately frozen metric.

