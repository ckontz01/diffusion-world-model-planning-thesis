# Authorized count-only expansion audit — 6 September 2026

User authorization: count P3/P4 allocation memberships and relevant exposure
categories to assess a larger study. This is not permission to release any
allocation, select a test manifest, read outcomes, or run planning/simulation.

Read only: the global episode partition/length registry; named membership-only
D3/D4/C1/I1/D5 manifests where present; SAGE public split/paper identifiers;
previously permitted exposure identifiers and their producer/configuration
metadata. HDF5 reads must name only episode-identifier or length datasets.
Inspect schemas before membership reads. Reject outcome-bearing TSV/JSON inputs;
do not hash whole outcome artifacts or read their numerical payloads.

Return aggregate counts, incremental exclusions, provenance and limitations.
Do not print or store eligible episode lists, selected starts, or protected
membership values. Protected allocations remain excluded regardless of this
metadata access. Document missing allocation/provenance coverage rather than
invent an independent custodian certification or infer availability from absence.

Keep historical sources/results and three untracked E12 drafts unchanged.
Use this separate branch and a small new audit directory. No package installation,
training, Slurm submission/cancellation, author contact, or confirmation run.
Existing parent package is f818c805b8d0d3b4459c238c780f310b93c6a389.
