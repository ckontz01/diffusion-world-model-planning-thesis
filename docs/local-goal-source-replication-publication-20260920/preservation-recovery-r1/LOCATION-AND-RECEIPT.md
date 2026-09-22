# R1 preservation complete — 22 September 2026

The single R1 session succeeded. The independently bounded worker and supervisor
exited zero; both verification and session-complete receipts are present, with
no failure record or unresolved remote operation. The original failed transfer
did **not** succeed and its entire directory remains unchanged.

## Exact location mapping

- Verified archive: `D:/THESIS-BACKUPS/local-goal-source-replication-20260920/run-a8fa92772272e11a-recovery-r1/final.tar`.
- Original failed directory, retained: `D:/THESIS-BACKUPS/local-goal-source-replication-20260920/run-a8fa92772272e11a`.
- The original authenticated request is copied unchanged; its old destination
  field is superseded only by this mapping and the recovery receipt, not edited.
- Remote archive and scientific source/output/analysis closures are unchanged.

Whole archive: 2,875,822,080 bytes, 32,393 exact regular members, SHA256
`fa17faef59d068b6a71d0ca40a3178b7f1be0a4e78688282a1bd846eb8a8b2aa`.
Every member passed the original inventory. The complete LGP1 archive
(`24609c83f6c21d99edc579229ab990db184c6e0fa1133ebad4336882c35189fd`)
and RB1 archive (`72c2717be4a10b0e103a05c6575710832e5ae4c9e9a21be573c8cb3c4441f175`)
also passed whole-file and exact-member verification against their original
inventories/receipts. No archive was extracted or regenerated for recovery.

## Authority, attempts and accounting

Frozen implementation/tests/authority commit:
`c35beb5b5dcafb7baebc3f2aec9a803f3be4ea54`, pushed and remote-verified before
production. This is the selected reasoning conversation's explicit R1 direction
under the user's standing delegation, not a fresh direct user signature.

Session `a06863419bcd4b4e855539aeb4ee2be6` began Unix 1790076036.7824562.
All 25 suffix ranges succeeded on attempt 1; 3 setup/metadata invocations, zero
retries, zero failed operations and zero unresolved processes. Exactly
1,673,383,936 archive-payload bytes were received; encryption/protocol overhead
was not measured. Original 1,202,438,144-byte prefix was independently
authenticated remotely and locally and copied under an exclusive read lock.
All successful chunks and logs remain on the SSD.

Session wall through completion: 347.703 seconds. Windows worker process CPU
through final sealing: 127.5 seconds (117.28125 before receipt/sealing).
Final verification phase before receipt: 50.640 seconds. Aggregate measured
remote helper process CPU: 12.313433332 seconds; new remote disk bytes: zero.
Inclusive remote occupancy: 9,320,146,032 bytes, below 24 GB. Final SSD recovery
directory: 4,560,503,669 bytes, below 8 GB. Final designated THESIS_SSD free space:
323,615,612,928 bytes; required volume identity and minimum 40 GB passed again.

Verification receipt SHA256:
`f37008725443d44a883f7a3035c67070e2560dacedf2cbad3fccf0c23d688cb6`.
Separate recovery seal SHA256:
`226aab3c8e95a309ad3da4d155b30b20cdbf97564b42ca567a4370e66a9b063b`.
The exact receipt, completion, seal, range manifest and preserved-original
records are included beside this document. The receipt contains every operation,
PID/start identity, byte count, return code and timing. No research allocation,
model call, analyzer rerun or scientific-content access occurred in R1.

After this receipt is committed/pushed and remote-verified, the existing
authority to read and publish the already-computed fixed aggregate resumes
using the verified recovery location. No further recovery session or new
experiment is authorized by R1.
