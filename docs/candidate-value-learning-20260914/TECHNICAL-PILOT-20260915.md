# CVL-1 eight-job technical tranche passed

Observed on the 15 September 2026 local-date heartbeat (14 September UTC).
The frozen dispatcher recorded `technical_pilot_passed` at Unix time
1789420274.4526672 for references1444,1314,767,1481. It autonomously advanced
to the remaining training collection under the existing approval; no new job
was submitted by the monitoring task.

## Exact completed tranche

All eight jobs are COMPLETED with exit0:0. Full adjacent checksum seals were
independently verified. A strict top-level allowlist extracted only technical
metadata; nested banks, targets, labels and outcomes were not deserialized or
reported. Each report has exact source/capsule hashes from
[the restart receipt](RESTART-20260914.md), matching train index/reference/H,
technical_valid=true, independent_saved_artifact_checks=true and
protected_payload_reads=0.

|Train index|Reference|H|Slurm job|Allocation seconds|Worker seconds|Sampled RSS bytes|Payload bytes before report|
|---|---|---|---|---|---|---|---|
|0|1444|75|301163|176|130.3262|1645293568|2242843|
|1|1444|150|301164|185|139.3436|1649336320|2181529|
|2|1314|75|301165|175|130.6392|1648455680|2264852|
|3|1314|150|301166|292|247.1821|1719578624|4220531|
|4|767|75|301167|123|77.6291|1631121408|1308411|
|5|767|150|301168|293|247.0700|1665323008|4177434|
|6|1481|75|301169|173|129.3134|1641320448|2237541|
|7|1481|150|301170|274|230.3173|1697263616|3688406|

The registered technical conditions pass:

- Longest allocation293s <=600s.
- Maximum sampled host RSS1,719,578,624bytes =1.60148GiB <=16GiB.
- Pilot payload sum22,321,547bytes; unchanged projection
  `(sum/8)*256 =714,289,504bytes`, below16,000,000,000bytes.

This projection is not an observed final payload, a worst-case guarantee, or
permission to relax ongoing storage/time limits. It excludes later reports/logs
and controls, for which the frozen envelope retains headroom. Sampled RSS is not
total node or device memory. Pilot acceptance did not inspect success rates,
candidate outcomes, available-anchor counts or efficacy.

## Seal identities

|Train index|SHA-256 of adjacent sha256.txt|
|---|---|
|0|`48e9073aa27e7be9f4d940bda74ed1d85d7ea6c268116cbb7eb09c38998301aa`|
|1|`d9ceb8cfc7528558ed6a107e66ad9567b6772ff7d33f2f836f67258616394b95`|
|2|`d313d0663d650428b9fde848391324a8af5705ad10683fbfa671975e9c24d288`|
|3|`6857a67dc9b36103fcf40e1bb65246eefd432403def240d67372beb3bafb70a7`|
|4|`97ebca7e4f145b4d022c32b9f1712a3bd413219abc2270c328ae7bc2c690a654`|
|5|`0d28281c198e1745a6c8d5f7f4b345ab20b9841d08ee338135f0fd99d9371366`|
|6|`881998d58606d8dafbf7ee950c7ee8503c8dd9ecd3616bdd4dab96aef9678b4a`|
|7|`7a39d4749b85fdbf9d0838d68db53c264fc2221f4e81710767debcf53f4f0f69`|

The read-only verification helper is preserved outside the immutable source as
`pilot_technical_check.py` in the run's control staging directory and external
`D:/THESIS-BACKUPS/candidate-value-learning-20260914/source-84141f2/`.
It hashes sealed members and decodes only the allowlisted top-level technical
fields, not the outcome-bearing report object. It does not modify the run,
source, manifest, models, sampler, analysis or decision rules.

## Accounting, progression and backup boundary

The tranche used1,691GPU-allocation seconds. Including the two passed80-second
preflights and the prior failed45-second allocation, cumulative cost at the
pilot gate was1,896seconds (31m36s). The50-hour limit has not been reset.

Post-pilot jobs301171 and301172 (reference1293,H75/H150) completed0:0 in162s
and149s respectively. Known terminal cumulative GPU cost through301172 is
2,207seconds; CPU fitting/analysis allocation remains zero. The dispatcher next
submitted301174, train index10, reference433,H75, with its600-second reservation.
There is no scientific advancement claim from these collection completions.
Fitting/sparse-support, ranking-promise and closed-loop gates have not run.

The latest dispatcher terminal-file byte count was27,375,954, before the active
job's subsequent writes; the existing50MB control reservation is additional.
External D remains THESIS_SSD with379,326,091,264free bytes. WSL backup companion
PID680 remains running with no error-log output. No stage backup request exists
yet: the approved train-stage archive and acknowledgement occur after all192
training jobs. Thus source/control copies are verified, but no completed
training-stage archive is claimed. No laptop-disk fallback or extra backup job.

The ten-minute monitor remains active. All scientific outputs remain behind
the frozen stage barriers. Historical artifacts and E12 drafts are unchanged.
