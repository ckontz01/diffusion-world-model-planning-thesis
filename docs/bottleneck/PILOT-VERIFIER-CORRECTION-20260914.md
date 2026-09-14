# Offline decoder-checker correction

All eight pilot simulations300964_0 and300965_[1-7] completed0:0. Their source,
banks, physical actions and metrics remain unchanged. Independent verifier
300966 failed before publishing an aggregate. Preserve its source and logs.

The failed equality compared the saved float32 physical first bank with the
checker's float32 in-place operations using float64 decoder coefficients.
There were659/1920 differing coordinates in the first inspected bank, maximum
difference5.960464477539063e-08. No intervention outcome was interpreted.

Inspection of the INSTALLED pinned StandardScaler.inverse_transform showed:
`X *= xp.astype(self.scale_, X.dtype)` then
`X += xp.astype(self.mean_, X.dtype)`.
The checker had omitted these coefficient casts. In a read-only technical
check of that exact preserved bank, adding the casts produced exact equality,
maximum difference0.0. Merely flattening the input did not fix the discrepancy.

Correction is confined to the independent verifier, with a synthetic float64-
coefficient regression fixture that rejects the old arithmetic. Both first-
and selected second-action verification use the corrected independent decoder.
Exact equality remains required. No tolerance change, production decoder change,
new model call, normalization fitting or simulation rerun. Reanalysis must use
a new source staging directory and a new output directory. The diagnostic
specification's assertion of reproducing pinned sklearn semantics is unchanged;
the implementation of that check now follows the actual pinned source.
