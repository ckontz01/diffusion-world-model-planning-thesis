# LGP1 preparation handoff

This is a source-inspected, synthetically tested feasibility package, **not a
completed research execution pipeline and not a launch approval**.

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

New implementation:

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

Remaining work is explicitly listed in protocol §10: real cache/training loops,
tensor-CEM/runtime binding, driver adapter, dispatch and aggregate accounting.
Do not present this preparation reference implementation as an end-to-end run.
The smallest shared-planner comparison is scientifically specified, but actual
throughput and runtime parity remain to be measured only after authorization.

No change to continuation, SI1/CVL decisions, E14/E19 decisions or model files.
The three E12 untracked drafts were verified still present in `/home/chris/thesis`.
No GPU job, research inference, training update, physics step or new label.
