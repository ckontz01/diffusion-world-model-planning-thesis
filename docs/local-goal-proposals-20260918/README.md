# LGP1 — completed development result

19 September 2026: **complete, authenticated and externally backed up**.
Diffusion26/192 (13.542%) versus GMM28/192 (14.583%); paired difference
−1.042pp, descriptive source-bootstrap interval[−7.292,+5.208]pp over32 exposed
sources. Retain continuation; promote no model and launch no follow-up.

- [Final report, all horizons/seeds and bounded interpretation](FINAL-REPORT.md)
- [All32 source effects](FINAL-SOURCE-EFFECTS.md)
- [Compact complete aggregate projection](FINAL-AGGREGATE-PROJECTION.json)
- [Authentication of every worker and original model freeze](FINAL-AUTHENTICATION.json)
- [Actual accounting](FINAL-ACCOUNTING.json) and [verified SSD backup](FINAL-BACKUP-VERIFIED.json)
- [Final-copy-only portability correction](BACKUP-PORTABILITY.md)

## Historical preparation handoff

The following text preserves the preparation status before explicit execution
approval and the separately recorded recoveries. It is not the current status.

The execution pipeline is now implemented and synthetically tested. **Real
runtime, numerical-data checks and throughput remain untested; execution is
not approved.** The reviewed preparation is preserved at `63e1d922`.

The three findings against `dc073fd6` are resolved in the separately frozen
[correction package](CORRECTION-PACKAGE.json). Read the narrow
[correction receipt](PRE-LAUNCH-CORRECTIONS.md) and
[new test evidence](CORRECTION-TEST-RESULTS.json). The previous source package
and its metadata remain preserved; neither package authorizes execution.

- [Implementation completion and launch commands](IMPLEMENTATION-COMPLETION.md)
- [Complete immutable package identity](LAUNCH-PACKAGE.json)
- [Pipeline regression evidence](PIPELINE-TEST-RESULTS.json)
- [Authenticated source/input lock](INPUTS.json)

The source package emits a separate disabled approval template that binds its
actual manifest and inputs. The document template below is preserved historical
preparation, not the completed package's approval form.

- [Protocol and actual interfaces](PROTOCOL.md): common target and sample-only
  CEM boundary; E14/CVD difference; training, execution and endpoint design.
- [Cost and launch envelope](RESOURCE-PLAN.md): six fits,384 primary episodes;
  hard proposed93.333GPU-hour cap, with unresolved measured-throughput feasibility.
- [Final identifier inventory](INVENTORY-ELIGIBLE.json):9,439training/1,057validation
  expert episodes after excluding entire released SAGE val/test roles and paper
  memberships; no payload read. Preliminary paper-only inventory is retained
  separately and does not define eligibility.
- [Roles](DATA-ROLES.json):32already-exposed development references, no reserved
  CVL closed-loop references, no new reference collection.
- [Source pins](SOURCE-PINS.json) and [synthetic evidence](TEST-RESULTS.json).
- [Disabled approval](APPROVAL-TEMPLATE.json): cannot authorize execution.

Initial preparation components (the completion record lists the added bindings):

- `cluster/prometheus/local_goal_proposals.py`: reference CEM, action bridge,
  lowdim construction, stage clock and local-target boundary.
- `cluster/prometheus/local_goal_models.py`: actual new GMM/diffusion definitions,
  per-row NLL/velocity losses and samplers. Parameters13,336,104/13,526,410
  respectively. No historical checkpoint is loaded or converted.
- `cluster/prometheus/test_local_goal_proposals.py`:10synthetic tests, including
  sample-only compatibility, full30round scoring budget, ties, projection before
  every cost, affine roundtrip, clock restart, final target switch, finite losses
  and deterministic model sampling. No optimizer or simulator used.

Reproduce synthetic tests with the existing CPU environment:

```
python -m unittest discover -s cluster/prometheus -p test_local_goal_proposals.py -v
```

`prepare_local_goal_inventory.py` is a read-only SSH source/metadata inspector.
It checks the pinned clean SAGE tree, authenticates the existing episode-role
registry and reads only released episode-role and paper memberships. It never
imports models or opens research payloads. The first invocation encountered
host Python3.6's lack of `subprocess(text=...)`; using `universal_newlines=True`
fixed only that metadata helper. No allocation or research execution occurred.

The bindings formerly missing from protocol §10 are implemented. This is not
an end-to-end research run: actual throughput, GPU kernels, checkpoint loading,
selected-data checks and physical integration remain to be measured only after
authorization, within the fixed allocation envelope.

No change to continuation, SI1/CVL decisions, E14/E19 decisions or model files.
The three E12 untracked drafts were verified still present in `/home/chris/thesis`.
No GPU job, research inference, research-data training update, physics step or
new label. Artificial-tensor optimizer steps are included in the new tests.
