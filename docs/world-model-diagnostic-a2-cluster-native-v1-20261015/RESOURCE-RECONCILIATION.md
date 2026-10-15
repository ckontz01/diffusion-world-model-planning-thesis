# Cluster route: storage decision required, not a VM permission

The VM requirement is removed by the human's direct instruction. No local administrator or VM service is required for this route. The remaining issue identified here is the unchanged resource envelope, before any research allocation or checkpoint copy.

All numbers below are decimal bytes. Cluster measurements are `du -sb` of the exact existing container/environment; local PC figures sum the files in the two known C0 runtime directories. These are logical-size accounting, not enforced filesystem quotas. Runtime compatibility and full dependency hashes have not yet been tested.

| Item | Bytes |
|---|---:|
| Existing shared container, counted once |3,139,002,368|
| Existing Python environment, counted once |2,058,354,358|
| Cluster runtime subtotal |5,197,356,726|
| Abandoned PC runtime and VM metadata, retained outside cluster live storage |1,512,400,813|
| Original live reservation |11,555,606,036|
| Original isolated-runtime reservation replaced for this comparison |−4,000,000,000|
| Unneeded safe-export reservation removed for direct loading, most favorable case |−410,653,018|
| Candidate cluster live reservation |12,342,309,744|
| Current cluster live cap |12,000,000,000|
| Live shortfall |342,309,744|

Even without charging the abandoned PC runtime against cluster live storage, and even after releasing the entire unneeded safe-export reservation, the original full environment does not fit the existing live cap. This is not a claim that every installed package is needed. A smaller import/runtime closure would need a concrete reviewed specification and measurements; it cannot simply be assumed to save the shortfall. No slimming, installation or environment mutation has been performed.

For inclusive accounting, do not count the PC runtime twice. The prior 4,862,451,499-byte preparation reservation included 4,000,000,000 bytes for PC runtime growth. Since that route is abandoned, a comparison retaining its measured files instead is:

`4,862,451,499 − 4,000,000,000 + 1,512,400,813 = 2,374,852,312 bytes`

This retains the prior non-runtime/preparation/small-package reservations, all existing PC files and failed records. It is conditional on no further PC VM operation or growth; all sizes must be rechecked at launch. No files are deleted and no original accounting record is overwritten.

With both existing 14 GB archive reservations retained, even the candidate live reservation gives:

`12,342,309,744 + 14,000,000,000 + 14,000,000,000 + 2,374,852,312 = 42,717,162,056 bytes`

That is 717,162,056 bytes over the current 42 GB inclusive cap. Disk free space is not the blocker: the required SSD was healthy with 310,111,760,384 bytes free. The issue is the explicit study cap, which the VM-waiver instruction did not increase.

## Concrete proposed resource-only amendment — NOT authorized or applied

Use **13 GB live / 14 GB archive / 44 GB inclusive**, unchanged CPU/GPU/thread/RAM/time limits, no new model/image acquisition, no scientific change. Full cap topology would be:

`13,000,000,000 + 14,000,000,000 + 14,000,000,000 + 2,374,852,312 = 43,374,852,312 bytes`

This leaves 625,147,688 bytes inclusive headroom and 657,690,256 bytes live headroom against the current candidate reservation. Headroom is not spent twice; every future source, receipt, allocation failure and transfer partial must fit the corresponding remaining ledger. The 1,800-second conversion allocation remains unconsumed/unreassigned. Exact runtime/import/model/parity checks and the missing native runner still need completion before launch, even if this resource amendment is accepted.

Until the storage decision is resolved, no original-environment campaign is staged or submitted. This package records the implemented VM waiver, authenticated missing encoder source, nonexecuting checkpoint dependency inventory and eight new artificial checks. It does not claim model loading, native parity or experiment launch.
