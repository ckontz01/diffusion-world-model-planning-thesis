# WSL storage and Git recovery — 6 September 2026

The user authorized WSL repair and restoration of reliable Git commits/pushes.

## Initial diagnosis

- `Thesis-Ubuntu` had a read-only/emergency_ro ext4 mount and repeated kernel disk-read errors.
- The distribution disk is `D:\WSL\Thesis-Ubuntu\ext4.vhdx` (45,310,017,536 bytes).
- Windows reports free capacity on D; no disk-full cause has been established.
- WSL was stopped and an offline pre-repair VHD copy started before filesystem repair.
- The existing Windows GitHub CLI session is authenticated as the repository owner and reports push permission. No credential was printed or copied into this repository.
- A separate Windows recovery checkout cloned successfully and passed `git fsck --full`.
- The ChatGPT GitHub connector still rejected a contents write with HTTP 403, `Resource not accessible by integration`. User account rights and installed-app token permissions are distinct.
- Git operations through the user's existing authenticated CLI are the recovery write route; no app scope, credential, or branch protection is bypassed.
- No cluster job, experiment setting, model checkpoint, or final result has been changed.

This is an in-progress operational record, not a claim that WSL repair is complete.
