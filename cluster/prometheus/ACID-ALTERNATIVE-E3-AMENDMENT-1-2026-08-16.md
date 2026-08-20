# ACID-alternative E3 amendment 1: read-only preflight compilation

Date logged: 2026-08-16 (Asia/Nicosia)  
Applies to: `ACID-ALTERNATIVE-E3-EXPLORATORY-D2-CLOSED-LOOP-PROTOCOL-2026-08-16.md`  
Protocol SHA-256: `c48eaf320c9b378af5e5d265397af8efd3485c45a288481d25f5161238af1fb0`

## Timing and outcome status

The first E3 authorization/preflight job, `297568`, failed after three seconds.
The immutable source manifest had verified successfully, but the explicit
`python -m py_compile` check attempted to create `__pycache__` inside the
correctly read-only snapshot and received `Permission denied`.

No exploratory authorization was created. No E3 model, planner, simulator,
candidate, success outcome, summary, or analysis output existed or was read.
Dependent GPU array `297569` and analysis job `297570` never started and were
cancelled. C1 and I1 were not read.

The superseded E3 source-manifest SHA-256 was
`b771456aadcdd558c37d41af7dff2eceef7693b70a141659769736d9d515524e`.
The failed chain is retained in the audit and may not be reused.

## Outcome-independent correction

Replace the bytecode-emitting `py_compile` invocation with a read-only
in-memory `compile(source, filename, "exec")` pass over the same five Python
files. The existing runtime import/self-test and synthetic 54-run analyzer
test remain unchanged. The correction changes no executable Python source,
model, checkpoint, data, task, arm, seed, endpoint, CEM setting, lambda,
bootstrap, threshold, authorization rule, or scientific decision.

A new content-addressed source snapshot and a wholly new scheduler chain are
required. The new authorization must again verify the failed v3 Stage-A
identity before any GPU element can start.
