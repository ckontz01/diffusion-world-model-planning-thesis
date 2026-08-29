#!/usr/bin/env bash
set -euo pipefail

STAGED_ROOT=${1:?usage: freeze_gdp_cem_e19_discrepancy.sh STAGED_ROOT E19_SNAPSHOT OUTPUT_PARENT}
E19_SNAPSHOT=${2:?usage: freeze_gdp_cem_e19_discrepancy.sh STAGED_ROOT E19_SNAPSHOT OUTPUT_PARENT}
OUTPUT_PARENT=${3:?usage: freeze_gdp_cem_e19_discrepancy.sh STAGED_ROOT E19_SNAPSHOT OUTPUT_PARENT}
ROOT=/lustreFS/data/superworld/ckontzias/thesis
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
E19_SOURCE_MANIFEST_SHA256=9f5499887c0d2e1f9808cc5f493e7f172e717bcb8db202088e89e5c29f2a1d6c
E19_PROTOCOL_SHA256=759f64b67a5c8e9d33e03c4d7027ede7edf99f1a4186236fb8f0879fc7ed0e20
SAGE_COMMIT=8219029fd52e89157e05aebb998ab26f0ef46966
SAGE_TREE=0c64066eeac97c27fee382c1879bb26968b3fd56
PROTOCOL=ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-DISCREPANCY-DIAGNOSTIC-PROTOCOL-2026-08-29.md

FILES=(
  "${PROTOCOL}"
  analyze_gdp_cem_e19_discrepancy.py
  compare_gdp_cem_e19_discrepancy.py
  create_gdp_cem_e19_discrepancy_runs.py
  freeze_gdp_cem_e19_discrepancy.sh
  gdp_cem_e19_discrepancy_specs.py
  run_gdp_cem_e19_discrepancy_analyze.slurm
  run_gdp_cem_e19_discrepancy_compare.slurm
  run_gdp_cem_e19_discrepancy_sentinel.slurm
  submit_gdp_cem_e19_discrepancy.sh
  test_analyze_gdp_cem_e19_discrepancy.py
  test_compare_gdp_cem_e19_discrepancy.py
  test_gdp_cem_e19_discrepancy_specs.py
  test_trace_gdp_cem_e19_discrepancy.py
  trace_gdp_cem_e19_discrepancy.py
)
E19_FILES=(
  gdp_cem_e19_cube_generator_compat.py
  gdp_cem_e19_specs.py
  validate_gdp_cem_e19_cell.py
)

STAGED_ROOT=$(cd "${STAGED_ROOT}" && pwd -P)
E19_SNAPSHOT=$(cd "${E19_SNAPSHOT}" && pwd -P)
mkdir -p "${OUTPUT_PARENT}"
OUTPUT_PARENT=$(cd "${OUTPUT_PARENT}" && pwd -P)

test -f "${ENV_DIR}/E19-ENVIRONMENT-LOCK.txt"
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
test "$(sha256sum "${E19_SNAPSHOT}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = \
  "${E19_SOURCE_MANIFEST_SHA256}"
(cd "${E19_SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test "$(sha256sum "${E19_SNAPSHOT}/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-REPRODUCTION-AND-OVERLAP-PROTOCOL-2026-08-28.md" | cut -d' ' -f1)" = \
  "${E19_PROTOCOL_SHA256}"
test "$(git -C "${E19_SNAPSHOT}/official-sage" rev-parse HEAD)" = "${SAGE_COMMIT}"
test "$(git -C "${E19_SNAPSHOT}/official-sage" rev-parse 'HEAD^{tree}')" = "${SAGE_TREE}"
test -z "$(git -C "${E19_SNAPSHOT}/official-sage" status --porcelain --untracked-files=all)"
for file in "${FILES[@]}"; do
  test -f "${STAGED_ROOT}/${file}"
done
for file in "${E19_FILES[@]}"; do
  test -f "${E19_SNAPSHOT}/${file}"
done
test -d "${E19_SNAPSHOT}/lewm-serialization-compat"
test -d "${E19_SNAPSHOT}/lewm-runtime"

BUILD=$(mktemp -d "${OUTPUT_PARENT}/.gdp-cem-e19-discrepancy-freeze.XXXXXXXX")
cleanup() {
  if [[ -n "${BUILD:-}" && -d "${BUILD}" ]]; then
    case "${BUILD}" in
      "${OUTPUT_PARENT}"/.gdp-cem-e19-discrepancy-freeze.*) rm -rf -- "${BUILD}" ;;
      *) printf 'refusing unsafe cleanup target: %s\n' "${BUILD}" >&2 ;;
    esac
  fi
}
trap cleanup EXIT

for file in "${FILES[@]}"; do
  cp -- "${STAGED_ROOT}/${file}" "${BUILD}/${file}"
done
for file in "${E19_FILES[@]}"; do
  cp -- "${E19_SNAPSHOT}/${file}" "${BUILD}/${file}"
done
cp -a -- "${E19_SNAPSHOT}/official-sage" "${BUILD}/official-sage"
cp -a -- "${E19_SNAPSHOT}/lewm-serialization-compat" \
  "${BUILD}/lewm-serialization-compat"
cp -a -- "${E19_SNAPSHOT}/lewm-runtime" "${BUILD}/lewm-runtime"

export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
export PYTHONPATH=${BUILD}/lewm-serialization-compat:${BUILD}:${BUILD}/official-sage:${BUILD}/lewm-runtime
export E19_SAGE_ROOT=${BUILD}/official-sage
export E19_DIAGNOSTIC_E19_RUN_ROOT=${ROOT}/experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988
export E19_DIAGNOSTIC_FLAT_ROOT=${ROOT}/downloads/acid-alternative/flat-lewm-models
export E19_DIAGNOSTIC_STABLEWM_ROOT=${ROOT}/data/stablewm
"${ENV_DIR}/bin/python" "${BUILD}/create_gdp_cem_e19_discrepancy_runs.py" \
  --output "${BUILD}/E19-DISCREPANCY-RUNS.tsv"
test "$(wc -l < "${BUILD}/E19-DISCREPANCY-RUNS.tsv")" -eq 11
if LC_ALL=C grep -q $'\r' "${BUILD}/E19-DISCREPANCY-RUNS.tsv"; then
  printf 'refusing CRLF-bearing Bash registry\n' >&2
  exit 1
fi

"${ENV_DIR}/bin/python" - "${BUILD}" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
for path in sorted(root.glob("*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY
find "${BUILD}" -maxdepth 1 -type f \
  \( -name '*.sh' -o -name '*.slurm' \) -exec bash -n '{}' ';'

"${ENV_DIR}/bin/python" -m pytest -q -p no:cacheprovider \
  "${BUILD}/test_gdp_cem_e19_discrepancy_specs.py" \
  "${BUILD}/test_trace_gdp_cem_e19_discrepancy.py" \
  "${BUILD}/test_compare_gdp_cem_e19_discrepancy.py" \
  "${BUILD}/test_analyze_gdp_cem_e19_discrepancy.py" \
  > "${BUILD}/wrapper-tests.txt"
"${ENV_DIR}/bin/python" -m pytest -q -p no:cacheprovider \
  "${BUILD}/official-sage/tests" > "${BUILD}/upstream-tests.txt"
grep -Eq '^7 passed(, [0-9]+ warnings?)? in [0-9.]+s$' \
  "${BUILD}/upstream-tests.txt"
test -z "$(git -C "${BUILD}/official-sage" status --porcelain --untracked-files=all)"

"${ENV_DIR}/bin/python" - "${BUILD}" "${ENV_DIR}" \
  "${E19_SNAPSHOT}" "${E19_SOURCE_MANIFEST_SHA256}" \
  "${E19_PROTOCOL_SHA256}" "${SAGE_COMMIT}" "${SAGE_TREE}" \
  "${PROTOCOL}" <<'PY'
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


root = Path(sys.argv[1])
environment = Path(sys.argv[2])
wrapper_text = (root / "wrapper-tests.txt").read_text(encoding="utf-8")
match = re.search(r"(\d+) passed", wrapper_text)
if match is None:
    raise RuntimeError("wrapper-test pass count missing")
payload = {
    "kind": "gdp_cem_e19_outcome_informed_discrepancy_snapshot_preflight",
    "e19_snapshot": sys.argv[3],
    "e19_source_manifest_sha256": sys.argv[4],
    "e19_protocol_sha256": sys.argv[5],
    "official_sage_commit": sys.argv[6],
    "official_sage_tree": sys.argv[7],
    "diagnostic_protocol_sha256": digest(root / sys.argv[8]),
    "run_manifest_sha256": digest(root / "E19-DISCREPANCY-RUNS.tsv"),
    "sentinel_count": 5,
    "repeat_count": 2,
    "run_count": 10,
    "episode_count": 500,
    "wrapper_test_count": int(match.group(1)),
    "wrapper_tests_sha256": digest(root / "wrapper-tests.txt"),
    "upstream_test_count": 7,
    "upstream_tests_sha256": digest(root / "upstream-tests.txt"),
    "environment_lock_sha256": digest(environment / "E19-ENVIRONMENT-LOCK.txt"),
    "environment_freeze_sha256": digest(environment / "pip-freeze.txt"),
    "e19_decision_preserved": "stop_native_reproduction_failed",
    "outcome_informed": True,
    "official_sage_source_modified": False,
    "checkpoint_modified": False,
    "planner_parameter_modified": False,
    "expected_values_modified": False,
    "tolerance_modified": False,
    "manifest_modified": False,
    "performance_metric_read": False,
    "protected_metric_artifact_read": False,
    "e18_vs_sage_comparison_run": False,
    "d5_read": False,
}
(root / "FREEZE-AUDIT.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

(cd "${BUILD}" && {
  find . -type f ! -path './official-sage/.git/*' \
    ! -name SOURCE-MANIFEST.sha256 -print0 \
    | LC_ALL=C sort -z \
    | xargs -0 sha256sum > SOURCE-MANIFEST.sha256
  sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null
})
SOURCE_HASH=$(sha256sum "${BUILD}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
DESTINATION=${OUTPUT_PARENT}/gdp-cem-e19-discrepancy-${SOURCE_HASH:0:16}
test ! -e "${DESTINATION}"
mv -- "${BUILD}" "${DESTINATION}"
BUILD=
chmod -R a-w "${DESTINATION}"
test ! -w "${DESTINATION}"
(cd "${DESTINATION}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
printf 'snapshot=%s\nsource_manifest_sha256=%s\nprotocol_sha256=%s\n' \
  "${DESTINATION}" "${SOURCE_HASH}" \
  "$(sha256sum "${DESTINATION}/${PROTOCOL}" | cut -d' ' -f1)"
