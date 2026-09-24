#!/bin/bash
set -euo pipefail
[[ $# == 5 && -n ${SLURM_JOB_ID:-} && ${SLURM_CPUS_PER_TASK:-} == 4 ]] || exit 2
exec /usr/bin/python3.9 -B "$1/supervise.py" --approval "$2" --run "$3" --task "$4"
