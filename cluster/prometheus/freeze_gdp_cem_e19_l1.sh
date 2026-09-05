#!/usr/bin/env bash
# Freeze only L1 additions; the verified parent is a read-only dependency.
set -euo pipefail
test "$#" -eq 2
STAGED=$(realpath "$1")
DEST=$(realpath "$2")
test "${DEST}" = /lustreFS/data/superworld/ckontzias/thesis/snapshots
FILES=(analyze_gdp_cem_e19_l1.py gdp_cem_e19_l1_tools.py test_gdp_cem_e19_l1_tools.py
  run_gdp_cem_e19_l1.slurm freeze_gdp_cem_e19_l1.sh gdp_cem_e19_d2_specs.py
  E19-L1-EXPOSED-ARTIFACT-LOCALIZATION-PLAN-2026-09-05.md)
for name in "${FILES[@]}"; do test -f "${STAGED}/${name}"; done
if LC_ALL=C grep -n $'\r' "${FILES[@]/#/${STAGED}/}"; then
  printf 'CR rejected before freeze\n' >&2
  exit 2
fi
bash -n "${STAGED}/run_gdp_cem_e19_l1.slurm"
MANIFEST=$(mktemp)
(cd "${STAGED}" && printf '%s\n' "${FILES[@]}" | LC_ALL=C sort | xargs sha256sum) > "${MANIFEST}"
IDENTITY=$(sha256sum "${MANIFEST}" | cut -d' ' -f1)
SNAPSHOT=${DEST}/gdp-cem-e19-l1-${IDENTITY:0:16}
test ! -e "${SNAPSHOT}"
mkdir "${SNAPSHOT}"
for name in "${FILES[@]}"; do cp -p -- "${STAGED}/${name}" "${SNAPSHOT}/${name}"; done
cp -- "${MANIFEST}" "${SNAPSHOT}/SOURCE-MANIFEST.sha256"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256)
chmod -R a-w -- "${SNAPSHOT}"
printf 'SNAPSHOT=%s\nSOURCE_MANIFEST_SHA256=%s\n' "${SNAPSHOT}" "${IDENTITY}"
