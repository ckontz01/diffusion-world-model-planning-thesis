# R2 engineering review evidence

This package contains no new benchmark results and authorizes no holdout.

- [Main boundary/seed review](main/R2-REVIEW.json): 24 sealed fresh-process
  initializations and one fixed action per run; includes the full trace hash
  inventory and source-summary hash.
- [Preserved-observation/source audit](source-audit/SOURCE-AUDIT.json): pinned
  functions/hashes and checks of 180 already-saved R1 PushT step observations.
- [Contact probe summary](contact/CONTACT-SUMMARY.json): eight sealed
  isolated setter probes, zero primitive actions; retains numerical residuals
  from the imperfect reconstruction of R1 reset geometry.
- MAIN-SOURCE-MANIFEST.sha256 and CONTACT-SOURCE-MANIFEST.sha256 are the exact
  pre-execution source manifests. Each JSON has its own adjacent seal.

Read the [result and limitations](../E19-R2-LOCALIZATION-RESULT-2026-09-05.md),
especially the seed-32 baseline limitation. Do not describe paired agreement
as proof of correct restoration or this evidence as exact historical replay.

Raw/full artifacts remain on Prometheus. Local copies are in `/home/chris/thesis`
on external-SSD-backed WSL Thesis-Ubuntu. Verify with
`python cluster/prometheus/verify_gdp_cem_e19_r2_result.py` from the repo root.
