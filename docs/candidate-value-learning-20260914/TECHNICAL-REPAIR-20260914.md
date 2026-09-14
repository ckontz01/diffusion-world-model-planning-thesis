# CVL-1 infrastructure correction after preflight 301159

The user explicitly authorized fixing and restarting this technical failure.
The earlier failed run and [stop report](STOP-20260914.md) remain preserved.
No scientific result was available: 301159 stopped before model/record access.
This is not permission to retry a sparse-support or ranking-promise stop.

## Established cause: three container-owned Python aliases

A read-only host/container comparison used only the named Python environment,
without loading models, episodes or protected payloads and without a GPU job.
The original host hash covered 21,643 entries; the container hash covered 21,646.
**Every common entry was identical.** The three container-only entries were:

|Environment path|Link destination|
|---|---|
|bin/python|/opt/conda/bin/python|
|bin/python3|python|
|bin/python3.11|python|

The aliases resolve inside the pinned Apptainer image but not on the host.
The old `is_file()`-then-content-hash rule omitted dangling aliases on the host
and dereferenced them in the container. This was a view-dependent inventory bug,
not changed dependency/model bytes. Container-resolved Python content SHA-256:
`b5e87ec94959bba4d7dd6aa47435241277b182342a29485f1b8d0a35f7349bbd`.

Original host tree:
`de39e8bc08614c001979ab346884666e93243815766200adca1006029e0c495b`

Original container tree:
`61c0c05891c8d0078d08c2645a407cfe6661a53035160c56a83a6db615e1274c`

The corrected tree hashes each regular file's bytes and each symlink's path and
literal destination, including dangling aliases. It does not omit the aliases
or relax regular-file checks. The complete SIF bytes remain independently pinned,
authenticating the container-owned interpreter. Link retargeting and regular-file
modifications change the digest; host availability of the target does not.

Independently executed host Python3.6 and container Python3.11 checks now agree:

- Environment: `cf3451575c574ef848dccc6f031ffeb18fe84130620fefa22e37ace6a8a374b6`
- Runtime code: `d5422bf4684b7805c7bf31491cc5f72b9f833855cc749376e74ee95eed0e32e3`

Comparison inventories are preserved under
`/lustreFS/data/superworld/ckontzias/thesis/staging/candidate-value-technical-repair-20260914/`
and externally in `D:/THESIS-BACKUPS/candidate-value-learning-20260914/source-f937845/`:
host.json SHA `557e6347c43e6fe6b271dc50ed71f878059c20b276446743d47253bae3122cb4`;
container.json SHA `f3646334fee794f8369a52529bd28b8fe20fcaa352a25969d3f50d871b01a1a7`.
These contain runtime file identities, not research outcomes.

## Established cause: filesystem-owned metadata copy

The source capsule carries `lustre.lov`, a Lustre filesystem-owned extended
attribute. The observed Python3.6 `shutil.copy2` traceback failed in `_copyxattr`
while applying attributes after copying the bytes. The repaired terminal copier
creates destinations exclusively, copies bytes, and verifies SHA-256. It does not
propagate xattrs or permissions, overwrite existing files, change ownership, or
bypass protected metadata operations. The original partial terminal is untouched.

The dispatcher now also creates the intended parent after namespace/approval
authentication while retaining exclusive creation of the run itself.

## Accounting and restart boundary

The separately bound restart approval carries 301159 as a prior FAILED A6000
allocation, 45 seconds. The dispatcher includes that cost from its first
reservation through final reporting. The 50-hour ceiling is not reset. New
registered maximum 173,400 GPU seconds +45 prior seconds =173,445 seconds, still
inside 180,000. This explicitly authorized technical replacement introduces one
additional historical preflight allocation, not an extra scientific case or seed.
CPU-job allocation remains 7,200 seconds, and source/control/diagnostic evidence
remain inside the existing 50MB control reservation within the 20GB ceiling.

No automatic retry loop was added. Future failed jobs stop and preserve evidence;
scientific sparse-support/ranking gates remain unchanged. No model, loss,
preprocessing, sampler, seed, allocation, endpoint, decoder, initializer, planner,
success predicate, historical result or scientific protocol was changed.

## Regression and deployment requirements

Three infrastructure tests cover dangling/resolved symlink invariance plus
tamper detection, exclusive content copying without xattrs, and prior-cost
validation. The full mocked dispatcher also checks parent creation and cumulative
costs with the 45-second prior allocation. These extend the 52 prior tests to55.
Run all55 locally and from the new exported source before launch. Bind a new
source/capsule/approval; never modify the old immutable snapshots. Real registered
preflights must still pass before the eight-job tranche. Host/container hashing
agreement is not a claim that those GPU preflights already passed.
