#!/usr/bin/env bash
#SBATCH --job-name=gdp-e13-d4-manifest
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --array=0-2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e13-d4-manifest-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e13-d4-manifest-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E13 snapshot}"
: "${PREFLIGHT_JOB_ID:?missing successful E13 preflight job}"
: "${SMOKE_JOB_ID:?missing successful E13 P1 smoke array}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
PREFLIGHT=${ROOT}/results/acid-alternative/gdp-cem-e13/preflight/job-${PREFLIGHT_JOB_ID}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${PREFLIGHT}" && sha256sum -c sha256.txt >/dev/null)

# Revalidate every P1-only smoke cell before any D4 identifier is selected.
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  "${ENV_DIR}/bin/python" - "${ROOT}" "${PREFLIGHT_JOB_ID}" \
  "${SMOKE_JOB_ID}" <<'PY'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
preflight_job = sys.argv[2]
smoke_job = sys.argv[3]
arms = (
    "latent_gaussian_select_k300",
    "vp_select_k300",
    "prism_dp_select_k300",
    "vp_select_k16",
    "prism_dp_select_k16",
)
preflight_path = root / "results/acid-alternative/gdp-cem-e13/preflight" / f"job-{preflight_job}" / "summary.json"
preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
assert preflight["status"] == "ok"
assert preflight["kind"] == "gdp_cem_e13_outcome_free_preflight"
assert preflight["authorized_e12_prism_dp_artifacts"] == 9
assert len(preflight["artifacts"]) == 27
assert preflight["untouched_p3_capacity"] == {"pusht": 1360, "reacher": 556, "cube": 489}
assert preflight["d4_read"] is False
assert preflight["protected_p4_c1_i1_read"] is False
protocol_sha = "65d56b613f12ad896c395e6feb4fc6d39f404bc802045369d0a88b638690af58"
e12_audit_sha = "14b4e4ad00bbbe9f51205541a5fa812334f843995ca9ed7a2acec2acd090b480"
candidate_count = {
    "latent_gaussian_select_k300": 300,
    "vp_select_k300": 300,
    "prism_dp_select_k300": 300,
    "vp_select_k16": 16,
    "prism_dp_select_k16": 16,
}
expected_files = {
    "summary.json",
    "episodes.tsv",
    "resolved-config.json",
    "solver-diagnostics.jsonl",
    "proposal-diagnostics.jsonl",
    "audit.txt",
}
for task_index, task in enumerate(("pusht", "reacher", "cube")):
    for arm_index, arm in enumerate(arms):
        array_index = task_index * len(arms) + arm_index
        directory = root / "results/acid-alternative/gdp-cem-e13/p1-smoke" / task / arm / f"job-{smoke_job}-{array_index}"
        declared = {}
        for line in (directory / "sha256.txt").read_text(encoding="utf-8").splitlines():
            digest, name = line.split(maxsplit=1)
            declared[pathlib.Path(name.lstrip("* ")).name] = digest
        assert set(declared) == expected_files
        for name, digest in declared.items():
            observed = hashlib.sha256((directory / name).read_bytes()).hexdigest()
            assert observed == digest
        summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
        assert summary["status"] == "ok"
        assert summary["kind"] == "gdp_cem_e13_p1_integration_smoke_shard"
        assert summary["analysis_role"] == "non_confirmatory_P1_integration_only"
        assert summary["mode"] == "p1_smoke"
        assert summary["task"] == task and summary["arm"] == arm
        assert summary["model_seed"] == 6101 and summary["shard"] == 0
        assert summary["episode_count"] == 4
        assert summary["protocol_sha256"] == protocol_sha
        assert summary["source_manifest_sha256"] == preflight["source_manifest_sha256"]
        assert summary["e12_stage_b_audit_sha256"] == e12_audit_sha
        assert summary["d4_read"] is False
        assert summary["d3_outcomes_read"] is False
        assert summary["protected_p4_c1_i1_read"] is False
        assert str(summary["runtime"]["slurm_array_job_id"]) == smoke_job
        assert int(summary["runtime"]["slurm_array_task_id"]) == array_index
        assert summary["runtime"]["gpu"] == "NVIDIA RTX 6000 Ada Generation"
        assert summary["runtime"]["hostname"] == "gpu09.cluster"
        config = summary["resolved_config"]
        assert config["integration"] == "pure_one_pool_selector"
        assert config["candidate_count"] == candidate_count[arm]
        assert config["optimizer_steps"] == 1
        assert config["horizon"] == config["receding_horizon"] == config["action_block"] == 5
        diagnostics = summary["proposal_diagnostics"]
        assert diagnostics["candidate_counts"] == [candidate_count[arm]]
        assert diagnostics["all_finite"] is True
        assert diagnostics["mean_coordinate_std_min"] > 0.0
print("E13 Stages B-C validated without D4")
PY

case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht; DATASET=pusht_expert_train.h5; PARTITION=pusht-v1 ;;
  1) TASK=reacher; DATASET=reacher.h5; PARTITION=reacher-v1 ;;
  2) TASK=cube; DATASET=cube_single_expert.h5; PARTITION=cube-v1 ;;
  *) exit 2 ;;
esac
OUT=${ROOT}/manifests/gdp-cem-e13-d4/${TASK}/job-${SLURM_ARRAY_JOB_ID}
test ! -e "${OUT}"
mkdir -p "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/create_gdp_cem_e13_d4_manifest.py" \
  --task "${TASK}" --dataset "${ROOT}/data/stablewm/${DATASET}" \
  --partition-manifest "${ROOT}/manifests/partitions/${PARTITION}/episodes-seed-20260728.tsv" \
  --exclusion r0 "${ROOT}/manifests/acid-alternative-v1/${TASK}/r0-official-seed42.tsv" \
  --exclusion d1 "${ROOT}/manifests/acid-alternative-v1/${TASK}/d1-fresh-development.tsv" \
  --exclusion d2 "${ROOT}/manifests/acid-alternative-v3-d2/${TASK}/job-297535/d2-fresh.tsv" \
  --exclusion d3 "${ROOT}/manifests/gdp-cem-e11-d3/${TASK}/job-297834/d3-untouched.tsv" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-tsv "${OUT}/d4-untouched.tsv" \
  --output-json "${OUT}/provenance.json"
printf '%s\n' "study=gdp_cem_e13_d4_manifest" "task=${TASK}" \
  "job_id=${SLURM_ARRAY_JOB_ID}" "array_task_id=${SLURM_ARRAY_TASK_ID}" \
  "preflight_job_id=${PREFLIGHT_JOB_ID}" "p1_smoke_job_id=${SMOKE_JOB_ID}" \
  'identifier_inputs_only=true' 'outcome_columns_read=false' \
  'd3_outcomes_read=false' 'd4_outcomes_read=false' \
  'protected_p4_c1_i1_read=false' > "${OUT}/audit.txt"
(cd "${OUT}" && sha256sum d4-untouched.tsv provenance.json audit.txt > sha256.txt)
chmod a-w "${OUT}/d4-untouched.tsv" "${OUT}/provenance.json" \
  "${OUT}/audit.txt" "${OUT}/sha256.txt" "${OUT}"
