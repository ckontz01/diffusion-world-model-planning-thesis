# LGP1 scoped controller-import correction

The user approved the proposed deferred-import fix with "yes fix", following
the pre-submission blocker recorded at 5de71b27404898264a9c35dbbaa79545dd9906e6.
That approval authorizes retesting, refreezing and proceeding under the existing
conditional scientific approval, not a change to the experiment or its caps.

`lgp1_verify.cache` now imports NumPy locally. The host controller's `task`
verifier retains the same seal, identity, budget and completion checks without
requiring unused scientific dependencies. Cache validation still requires
NumPy and runs in the unchanged pinned worker environment. No environment,
dependency installation, permission, scientific arithmetic or worker setting
is changed. The exact observed-angle endpoint correction is retained.

A focused subprocess regression uses isolated Python with site packages
disabled. It imports the actual dispatcher and verifies a synthetic sealed
task, confirms no NumPy was loaded, and confirms cache verification still
requires NumPy. The entire existing artificial test suite is also rerun from
the checkout and the new immutable export. Actual host Python 3.9 additionally
checks the exported controller import and separate approval before launch.

Old source packages, disabled templates and execution records remain intact.
New source/package/test identities are recorded separately in HOST-IMPORT
records. No retry, resume, scientific change or additional allocation is
authorized. Research execution uses the existing fixed grid only after source
publication, exported tests and fresh no-prior-attempt checks pass.
