# WSL storage and Git recovery — 6 September 2026

## Verified results

- User authorized WSL repair and restoration of Git commits/pushes.
- Initial Linux mount had `emergency_ro`, repeated virtual-disk I/O errors, and unreadable utilities/drafts.
- WSL was shut down before copying its complete 45,310,017,536-byte virtual disk.
- Offline original and copy SHA-256 matched: `47dffad01b546ec3d7d584fe2b5e43bf9fc7dd88e9e87328b57c2d0d9f93a5dd`.
- Backup: `D:\WSL-Recovery\Thesis-Ubuntu-20260906-before-repair\ext4.vhdx`.
- This full-disk copy is on the same physical USB drive; it is rollback protection, not an independent physical-device backup.
- After WSL reattachment, the original filesystem mounted read/write without `emergency_ro`; `/usr/bin/ps` executed normally.
- All three previously unreadable E12 drafts were recovered and independently hash-verified in `C:\Users\Chris\thesis-recovery\repair-20260906\recovered-E12-drafts`. Their source files were not edited or added to Git.
- For offline validation, an official Debian helper named `Thesis-Recovery` was installed on C with an 8 GB maximum virtual disk. The original distribution was not replaced or unregistered.
- The exact original filesystem UUID `e6cd857b-485c-44e3-bf60-5b82100b75ff` was identified and verified unmounted.
- A full read-only `e2fsck -f -n` completed all five passes and returned exit 0 at `2026-09-06T15:36:58Z`.
- No destructive or automatic filesystem-repair command was needed or run. The fault's underlying physical/virtual attachment trigger remains unproven.

## Git access

- Existing Windows GitHub CLI authentication works without exposing credentials.
- The isolated Windows recovery checkout passed `git fsck --full`.
- Commit `2c99551b0e31312ca1bd014a2a4669b5a00abde6` was pushed successfully and read back through the GitHub connector.
- Direct connector contents writes still return HTTP 403. The working write route is authenticated Git/CLI, not a claimed repair of the connector's app-token scopes.

## Pending operational step

A tool safety block prevented creation of the final disk-detachment script. The original VHD remains bare-attached/offline pending a manual administrator detach. Original-WSL post-recovery Git validation and raw-backup revalidation/catch-up therefore remain pending. Archival writers have not been restarted against a disk still under offline inspection.
No Slurm submission, cancellation, scientific setting, model, or historical-result modification occurred during recovery.
