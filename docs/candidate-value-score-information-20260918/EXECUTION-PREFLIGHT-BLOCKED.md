# SI1 approved execution — local connection blocked

The researcher approved execution of preparation commit `b1cfcdd8e062ca995feb439e4d8cefe2dac40f08`: one CPU allocation, 4 CPUs, 8 GiB, 7,200 allocation-wall seconds, 24 fits / 43,200 updates, zero GPUs and 1,000,000,000 new-artifact bytes. No automatic retry, extra allocation or scientific changes are authorized.

Before submission, the configured invocation `wsl -d Thesis-Ubuntu -u chris -- ssh prometheus ...` failed locally with `getpwnam(chris) failed 5` and `Wsl/WSL_E_USER_NOT_FOUND`. The remote command was not started. WSL lists Thesis-Ubuntu as running, but cannot resolve its required user. Native Windows SSH does not resolve the established alias to a configured remote hostname (`ssh -G prometheus` returns hostname `prometheus`), so no alternate credential or connection route was improvised.

The designated external volume is connected: THESIS_SSD, identity `0a2f1ba9-0000-0000-0000-100000000000`, approximately 376.6 GB free. All 16 published package members verified against the source manifest, SHA-256 `68145e6458da0b90255dd98e4fa2b9469dea12907797d7830c9bd233314be35c`. The original approval template remains disabled and unchanged.

No SI1 job was submitted, no execution approval was created, and no numerical data, models or outcomes were evaluated. Allocation charged by this execution attempt: zero. Prior remote SI1-attempt absence and namespace state could not yet be verified because SSH was never reached; they must be checked before any submission. This is a pre-submission connection blocker, not a scientific stop or an allocated-job failure.

Required next step: restore the existing Thesis-Ubuntu/chris connection or explicitly identify another configured connection. Do not change users, permissions, environments, credentials or scientific settings implicitly. Once access is restored, continue the outstanding preflight under the existing researcher approval; do not infer that any job is running.
