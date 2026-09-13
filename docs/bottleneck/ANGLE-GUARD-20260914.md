# Exact native angle endpoint admission

The historical benchmark, simulations, recorded outcomes and decision are
unchanged. Failed diagnostic reducer job300959 and all its files are preserved.
This is a reader validation repair, not a simulator or planning correction.

First inventory300960 (sourcecf6f492) scanned57600 runs/12001777 state samples.
Receipt SHA256 bda080e59fc09b2806e5a6fc844eb4048c3958395e8fd643ac92661f52d146db.
Supplement300962 (source126d079; scanner SHA256
54aa7559e2467591fae260eb27d7b2013904a43a78ae9945be24cac6d8a57e40)
completed0:0 and independently verified the exact unique exposed grid and
float64 state/goal dtypes in every run. Both identify1766 samples in24 runs at
exact float64 2*pi, hex0x1.921fb54442d18p+2. No negative/above-bound states or
noncanonical goals. Zero recorded-success, combined-step, episode, or UNMASKED
angular-classification disagreements. Maximum angular formula difference
8.881784197001252e-16; no requirement of numerically identical formulas.

Native installed observation source SHA256
d8d0de35aaab5b846db4e79b0fbfd6b17375178cce40a25df5301c8030ca6d68
uses block.angle%(2*np.pi) in its float64 observation. The pinned-runtime
negative-tiny modulo example returns exact2pi. This supports the representation
mechanism; it does not recover the unrecorded pre-modulo body angle of every
offending sample.

The diagnostic state guard changes only `<2*pi` to `<=2*pi`. No isclose,
epsilon, clipping, normalization, dtype narrowing or changed predicate.
Goal admission remains strictly<2*pi, as all observed goals satisfy it.
The original subtraction/minimum/threshold and t0 exclusion remain intact.
Tests cover both endpoint directions with canonical goals, exact goal endpoint
rejection, adjacent representable values, nonfinite values, threshold neighbors
and byte preservation. New reduction must use a new versioned source/output.

The reasoning-chat review explicitly supported this narrow change conditional
on the supplementary checks above. Those checks completed before the edit.
