# WM-DIAG0-A2-C0-V1: data-only host validator

This is one completed **parser/identity component**, not a completed conversion,
reconstruction, isolation or research gate. `GateReady=false`. No real checkpoint
was read, deserialized, converted or forwarded; no source generation, fitting,
simulator, Slurm/GPU job or scientific configuration change was performed.

Pro's completed reply to the already-submitted 02:28 Cyprus review request gave
this one bounded task: tensor-only Safetensors plus constrained JSON validation
using artificial exports, publication of compact sources/first-boot preparation,
and one new small SSD package. It explicitly forbids automatic boot, conversion
or research continuation. Human delegation authorizes the task, not a relaxation
of science, resources or security. The original 56-test suite was not repeated.

## Format and independent trust boundary

The format follows the [primary Safetensors specification](https://github.com/safetensors/safetensors/blob/main/README.md):
little-endian 8-byte header length; bounded UTF-8 JSON; offsets relative to the
data buffer; little-endian, row-major numeric bits. This **strict subset** forbids
`__metadata__`, executable/import targets, extra header fields and all unlisted
formats. It supports BOOL, I8/U8, I16/U16, I32/U32, I64/U64, BF16, F16, F32 and F64.
Sub-byte, float8, complex, string and object types are explicitly unsupported.
There is no cast, quantization, reshape or numeric-array object deserialization.
Only canonical numeric storage is exported; trusted one-hop aliases describe
ties. Overlapping storage is forbidden. Empty tensors must be at a complete-data
coverage boundary. Scalars have `shape=[]`. Zero-sized dimensions are permitted;
all dimensions are checked even if an earlier one is zero.

`contract.schema.json` describes the independent reviewer-trusted input, while
`export.schema.json` describes untrusted converter metadata. The executable
validator enforces both schemas and cross-field constraints; it does NOT load a
JSON Schema library or fetch any schema references. The expected contract must
come from a separately reviewed architecture/input inventory, never from the
same converter's manifest. UNBOUND is a hard rejection, before stage parsing.
`REAL-STATE-BINDING.json` records only already-reviewed source/config identities
and known source requirements. Real state inventories remain explicitly UNBOUND.
It is NOT an executable BOUND contract.

The only directory members allowed are `manifest.json` and the exact declared
Safetensors filenames. Checks include duplicate keys, count/rank/dimension/size
limits before allocation, exact tensor membership, dtypes/shapes, integer byte
arithmetic, offsets and file length, full coverage with no holes/overlap/tail,
per-member and per-tensor hashes, and exact original artifact labels and typed
configuration (including signed zero). Null trusted hashes mean an additional
known hash is absent, NOT that a converter self-manifest is authoritative.
Numeric weights/buffers use finite-only policy. A specifically declared floating
causal-mask tensor may permit negative infinity only; positive infinity and NaN
still reject. Source `Attention.bias` can instead be a finite binary tensor:
its **actual** policy is not guessed from the artificial additive mask.

Hashes establish byte identity and bound labels. They do not prove that arbitrary
input code was harmless or that an exported tensor came from an original object.
Those claims need authenticated isolated-conversion provenance later.

## Host staging and limits

No installed `safetensors` package was found in the existing native Python
3.12.14. The implementation uses only Python's standard library. No installation,
download, runtime build or scientific environment change was required.

Stage only regular local files in a reviewer-owned directory. No automatic guest
disk mount, extraction, host pickle loading or staging of research inputs exists.
On Windows, directory/file reparse attributes and all ancestors are checked;
handles deny write/delete sharing, final handle paths must match the local
requested path, and hardlinks are rejected. UNC roots and alternate streams
reject. POSIX uses O_NOFOLLOW and link checks; hostile concurrent ancestor
mutation is outside that fallback's supported staging assumption. This is not
a sandbox or universal filesystem-race proof. Windows actual hardlink rejection
was exercised; actual symlink/junction and adversarial race tests remain pending.
The reparse-bit rejection is a mocked unit test, explicitly not a real junction.

Caller caps and stricter trusted-contract caps both apply. Hard maxima: 512MiB
total staged files, 256KiB contract/manifest/header, 8192 tensors/aliases,
rank 8, dimension 1,000,000, 8 tensor files and 120 cooperative wall seconds.
Manifest/config nesting and members are bounded. Reads stream at 64KiB. Float
validation inspects IEEE bits, not converted float values. The program imports
no model code and constructs no model. The Python API's returned tensor table
is bounded by count/name limits; CLI omits it and prints a data-only summary.
Cooperative clock rejection was tested with an artificial clock; it is not a
hard OS timeout or blocked-I/O guarantee. The artificial test subprocess had
a 15-second external timeout. Guest containment/output quotas are NOT tested.
This profile has a conservative <=8MiB returned-report bound, not an unlimited
scientific readout. No report contains tensor values or efficacy.

Example for the **artificial** fixture only:

```powershell
& 'C:/Users/Chris/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -I -B 'docs/world-model-diagnostic-a2-c0-v1-20261005/validator.py' --contract 'docs/world-model-diagnostic-a2-c0-v1-20261005/artificial-002/valid_exact_roundtrip/contract.json' --stage 'docs/world-model-diagnostic-a2-c0-v1-20261005/artificial-002/valid_exact_roundtrip/export' --max-bytes 65536 --max-seconds 5
```

Artificial contracts include parameters, persistent/nonpersistent buffers,
required unregistered causal mask, normalization/configuration and shared-tensor
declarations. The oracle is hand-specified expected bytes, not the fixture
producer's manifest. Every required tensor and descriptor is compared exactly.
No model forward or reconstruction is claimed: V1's Pro instruction narrowed
the next step to parser/schema/byte equality only. Artificial parity would not
validate the real released weights in any event.

## Pending work, unchanged permissions

The prepared one-shot administrator first-boot command and its helpers remain
byte-for-byte unchanged. No privileged boot attempt exists. The agent is
unelevated and the installed Computer Use policy prohibits PowerShell UI
automation. Human consent is present; allowed privileged execution capability
is absent. There is no elevation/terminal/service/task/security workaround.
The 8MiB OS-only report disk is not checkpoint-export media.

Still pending: actual offline boot/isolation readback; no-network/no-credentials
guest confinement and hard CPU/RAM/wall/output/export controls; pinned complete
guest runtime; full real tensor/architecture contract; concrete converter and
explicit reconstruction constructors; isolated artificial-object boundary and
round-trip tests; then a separately authorized real-conversion-only operation;
confined deserialized-reference-versus-reconstruction execution parity; native
forecast/cost/returned-plan/cache/chunking checks; generation/physics/tail adapters;
finite execution/preservation contract. Comparing two consumers of the same
export cannot establish equivalence to the original object. Reference-side real
checkpoint forwards must be explicitly authorized, confined and charged later.
Preserve T=1 context, native patch layout, action grouping, BF16/F32 boundaries,
recurrent channels, goal score, chunking and cache ownership. No historical
training-checkout equivalence is invented for the third-party encoder.

Do not execute a purported real-conversion command: no bound converter exists,
so V1 deliberately supplies no nominal launcher. Conversion is **not implemented
by this component**, and actual research deserialization remains disabled.

All 120 root identities/roles/seeds/collection rules, tasks/backbones, four cells,
S1, candidate bank/native-return, oracle/evaluation separation, 50-action budget
and tail, and analysis remain unchanged. All historical studies, E12 drafts,
checkpoints and paused monitors are unchanged.

## Accounting and preservation

`AUTHORIZATION-AND-RESERVATION.json` retains the full 1800-second V1 charge,
including publication/preservation/handoff, on top of the latest away ledger:
8914.10301460012 charged, 5485.89698539988 left of 14400. Actual new script
times are recorded separately inside this charge, never charged twice.
The earlier 600-second boot reservation remains charged; the separate real
conversion envelope is unconsumed. Four CPU threads and 8GiB remain ceilings.
New code/tests/metadata and backup copies have a 64MiB bound. The previous
4795342635-byte retained-preparation conservative total plus this reservation
is 4862451499, below 5GiB. Canonical OS/media/runtime/state/failures remain within
the SAME 4,000,000,000-byte reservation. Real runtime/export sizes are still
unknown; no storage slack is spent twice. Whole-study 12GB live/14GB archive/
42GB inclusive proposal is unchanged, not a launch authorization.

Published sources include unchanged existing first-boot/provisioning sources and
compact receipts, not OS images/disks, model weights, browser captures or
credentials. Only this new small package is preserved with whole/member checks;
neither the completed 373-member A2 package nor historical packages are recopied.
