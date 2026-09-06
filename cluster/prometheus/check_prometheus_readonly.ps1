# Narrow operational probe. No jobs, settings, files, or outcomes are changed.
# Invoke only through an available, authorized terminal action.
[CmdletBinding()]
param([switch]$SelfTest)
$ErrorActionPreference = 'Stop'
$root = '/lustreFS/data/superworld/ckontzias/thesis/experiments/independent-pusht/final-20260906-4a608e5'
$commands = @(
    'set -eu',
    'printf CHECK_UTC=; date -u +%Y-%m-%dT%H:%M:%SZ',
    'printf HOST=; hostname; printf USER=; id -un',
    "squeue -r -h -j 300339 -o '%T|%r' | sort | uniq -c",
    'sacct -X -n -P -j 300339,300340,300341 -o State,ExitCode | sort | uniq -c'
)
foreach ($stage in 0,1,2) {
    $dir = "$root/stage-$stage"
    $commands += "printf STAGE_${stage}_SEALED=; if test -d $dir; then find $dir -mindepth 2 -maxdepth 2 -name DONE.json -type f | wc -l; else echo 0; fi"
    $file = "$root/analysis-$stage/INDEPENDENT-VERIFICATION.json"
    $commands += "if test -f $file; then echo STAGE_${stage}_VERIFIER_FILE_PRESENT; else echo STAGE_${stage}_NOT_VERIFIED; fi"
}
$commands += "if test -f $root/TERMINAL.json; then echo TERMINAL_FILE_PRESENT; else echo NO_TERMINAL; fi"
$remote = $commands -join '; '
# This fixed command has no Windows quote characters requiring escaping.
if ($remote.Contains('"')) { throw 'Unexpected quote in fixed probe' }
$arguments = '-d Thesis-Ubuntu -u chris -- ssh -n -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 prometheus "' + $remote + '"'
if ($SelfTest) {
    $checks = [ordered]@{
        exact_wsl_route = $arguments.StartsWith('-d Thesis-Ubuntu -u chris -- ssh -n ')
        strict_host_check = $arguments.Contains('-o StrictHostKeyChecking=yes')
        noninteractive_auth = $arguments.Contains('-o BatchMode=yes')
        bounded_connect = $arguments.Contains('-o ConnectTimeout=10')
        no_mutating_command = ($remote -notmatch '\b(sbatch|scancel|scontrol|rm|chmod|tee|git|sudo|mount|umount)\b')
        no_outcome_payload_read = ($remote -notmatch '\b(cat|head|tail)\b|SUMMARY\.json|RESULT\.json')
        fixed_endpoint = $arguments.Contains(' prometheus "')
    }
    if ($checks.Values -contains $false) { throw 'Probe self-test failed' }
    [pscustomobject]@{self_test_passed=$true; checks=$checks; scientific_changes=$false} | ConvertTo-Json -Depth 4
    return
}
$info = New-Object System.Diagnostics.ProcessStartInfo
$info.FileName = Join-Path $env:WINDIR 'System32\wsl.exe'
$info.Arguments = $arguments
$info.UseShellExecute = $false
$info.CreateNoWindow = $true
$info.RedirectStandardOutput = $true
$info.RedirectStandardError = $true
$process = New-Object System.Diagnostics.Process
$process.StartInfo = $info
if (-not $process.Start()) { throw 'WSL probe did not start' }
$stdout = $process.StandardOutput.ReadToEndAsync()
$stderr = $process.StandardError.ReadToEndAsync()
if (-not $process.WaitForExit(90000)) {
    # Stop only this local status client, never a cluster job.
    $process.Kill()
    throw 'Read-only status client timed out; cluster jobs were not changed'
}
$report = [ordered]@{
    checked_utc = [DateTime]::UtcNow.ToString('o')
    route = 'Desktop Commander -> Windows WSL -> Thesis-Ubuntu/chris -> ssh prometheus'
    ssh_exit = $process.ExitCode
    stdout = $stdout.Result
    stderr = $stderr.Result
    scientific_changes = $false
    analysis_payloads_read = $false
    verification_note = 'Verifier/terminal file presence is not verification of their contents.'
    scope_note = 'Scheduler totals concern original stage-0 jobs. Seals and file flags cover all stages.'
}
$report | ConvertTo-Json -Depth 4
if ($process.ExitCode -ne 0) { exit $process.ExitCode }
