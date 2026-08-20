#!/usr/bin/env bash
# Data-transfer-only staging for the two small official flat LeWM model artifacts.

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SOURCE_ROOT="${ROOT}/downloads/acid-alternative/flat-lewm-models"

stage_model() {
  local task="$1"
  local repo="$2"
  local revision="$3"
  local expected_weights_sha256="$4"
  local destination="${SOURCE_ROOT}/${task}-${revision}"
  local filename

  mkdir -p "${destination}"
  for filename in config.json weights.pt; do
    if [[ ! -f "${destination}/${filename}" ]]; then
      curl --fail --location --silent --show-error \
        --retry 8 --retry-delay 10 \
        --continue-at - \
        --output "${destination}/${filename}.partial" \
        "https://huggingface.co/${repo}/resolve/${revision}/${filename}?download=true"
      mv -- "${destination}/${filename}.partial" "${destination}/${filename}"
    fi
  done

  printf '%s  %s\n' \
    "${expected_weights_sha256}" "${destination}/weights.pt" \
    | sha256sum --check --strict
  printf '%s\n' \
    "repo=${repo}" \
    "revision=${revision}" \
    "staged_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    > "${destination}/source.txt"
  sha256sum "${destination}/config.json" "${destination}/weights.pt" \
    > "${destination}/sha256.txt"
}

stage_model \
  pusht \
  quentinll/lewm-pusht \
  22b330c28c27ead4bfd1888615af1340e3fe9052 \
  48938400ae3464c9680731287f583a9cb516f55a8ec64ea13a91be47fb15b607

stage_model \
  cube \
  quentinll/lewm-cube \
  b0747c5002e86d2ce8f3cd8178004b97524c587d \
  2839a907362f403f9136383016e91774373a295d958ae75121791f22a9fddf89

find "${SOURCE_ROOT}" -mindepth 2 -maxdepth 2 -type f \
  -printf '%p|%s bytes\n' | sort
