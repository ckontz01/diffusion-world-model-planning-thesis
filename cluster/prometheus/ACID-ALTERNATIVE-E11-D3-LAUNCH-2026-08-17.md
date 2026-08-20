# E11 untouched-D3 launch record

Launched: 2026-08-17  
Status at handoff: blinded evaluation running; aggregate locked

## Frozen identity

- Protocol: `ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-PROTOCOL-2026-08-17.md`
- Protocol SHA-256: `9b4bde9e2f69a7b92abaaf33f9db3016b8f61e82bedbe662a71a054cf3832ce0`
- Snapshot: `/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e11-1c52b60488373719`
- Source-manifest SHA-256: `1c52b60488373719017138bc33cef78fbc23551fe8efcb3637113a1d0b93c07e`

## Slurm chain

- Outcome-free preflight: `297832` — completed `0:0` in `00:03:06`
- P1 closed-loop integration smoke: `297833` — completed `0:0` in `00:00:32`
- D3 manifest generation: `297834` — completed `0:0` in `00:03:12`
- Blinded 576-shard evaluation array: `297835` — running
- Locked aggregate analysis: `297836` — pending on full-array success

## D3 manifest seals

Each task contains 400 starts from 400 distinct eligible P3 episodes, split
into eight immutable 50-start shards. All selected intersections with R0, D1,
and D2 are zero. No outcome column, C1 path, or I1 path was read.

- PushT: `fbe5699dead294002f085d1044d6b36d0935b57e7772405cb6ccfa87ebd4ed8f`
- Reacher: `566da39d7ad4fb67d1c73319b42ce3712e0358b8cd9856c32fb23b785aef828e`
- Cube: `641e55b7d4eba078c33923c9a5413673cfb38b827d295996ef7d09e425558b8c`

## Blinding rule

Do not open per-shard summaries, episode tables, success-bearing stdout, or
arm metrics while array `297835` is incomplete. Scheduler state, exit codes,
error stacks, and file/checksum existence may be monitored. Read results only
from aggregate job `297836` after all 576 shards complete successfully.
