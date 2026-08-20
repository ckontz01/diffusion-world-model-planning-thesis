#!/usr/bin/env bash

#SBATCH --job-name=setup-osmesa
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/setup-osmesa-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/setup-osmesa-%j.err

set -euo pipefail
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SCRIPT="${ROOT}/scripts/setup_osmesa_user_prefix.sh"
test -s "${SCRIPT}"
bash "${SCRIPT}"
