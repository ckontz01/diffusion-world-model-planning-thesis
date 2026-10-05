# Builds reviewed OS-only NoCloud media. No Hyper-V call or guest execution.
[CmdletBinding()]
param([switch]$Build)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (-not $Build) { [pscustomobject]@{Mode='PLAN_ONLY';StartsVM=$false;InstallsRuntime=$false} | ConvertTo-Json; return }
$c0SeedRoot='C:\Users\Chris\thesis-vm\wm-diag0-a2-c0-runtime-v1\guest-boot-v1'
if (Test-Path -LiteralPath $c0SeedRoot) { throw 'Seed build already attempted; preserve, no overwrite.' }
New-Item -ItemType Directory -Path $c0SeedRoot | Out-Null
$c0SeedFiles=Join-Path $c0SeedRoot 'seed'
New-Item -ItemType Directory -Path $c0SeedFiles | Out-Null
$c0GuestBytes=[IO.File]::ReadAllBytes((Join-Path $PSScriptRoot 'guest_report.py'))
if ($c0GuestBytes.Length -gt 16384) { throw 'Guest probe too large.' }
$c0Base64=[Convert]::ToBase64String($c0GuestBytes)
$c0UserData=@"
#cloud-config
users: []
disable_root: true
ssh_pwauth: false
package_update: false
package_upgrade: false
network:
  config: disabled
write_files:
  - path: /opt/c0-boot-report.py
    permissions: '0700'
    encoding: b64
    content: $c0Base64
runcmd:
  - [ /usr/bin/python3, -I, -B, /opt/c0-boot-report.py ]
"@
$c0Metadata="instance-id: c0-boot-v1-9cd3026b-dc45-4adc-b7c4-e2942308bf94`nlocal-hostname: c0-offline-prep`n"
foreach ($c0SeedPair in @(@('user-data',$c0UserData),@('meta-data',$c0Metadata))) {
    $c0SeedData=[Text.Encoding]::UTF8.GetBytes($c0SeedPair[1].Replace("`r`n","`n"))
    $c0SeedStream=[IO.File]::Open((Join-Path $c0SeedFiles $c0SeedPair[0]),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $c0SeedStream.Write($c0SeedData,0,$c0SeedData.Length) } finally { $c0SeedStream.Dispose() }
}
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
public static class C0SeedStreamV1 {
    public static long Save(object input, string output, long cap) {
        IStream stream = (IStream)input;
        IntPtr count = Marshal.AllocCoTaskMem(4);
        long total = 0;
        try {
            using (FileStream file = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.None)) {
                byte[] buffer = new byte[32768];
                for (;;) {
                    Marshal.WriteInt32(count, 0);
                    stream.Read(buffer, buffer.Length, count);
                    int read = Marshal.ReadInt32(count);
                    if (read < 0 || read > buffer.Length || total + read > cap) throw new InvalidDataException("ISO byte cap exceeded");
                    if (read == 0) break;
                    file.Write(buffer, 0, read); total += read;
                }
            }
        } finally { Marshal.FreeCoTaskMem(count); }
        return total;
    }
}
'@
$c0Image=New-Object -ComObject IMAPI2FS.MsftFileSystemImage
$c0Image.FileSystemsToCreate=3 # ISO9660 + Joliet: long NoCloud names preserved.
$c0Image.VolumeName='CIDATA'
$c0Image.Root.AddTree($c0SeedFiles,$false)
$c0Result=$c0Image.CreateResultImage()
$c0ISO=Join-Path $c0SeedRoot 'cidata.iso'
$c0ISOBytes=[C0SeedStreamV1]::Save($c0Result.ImageStream,$c0ISO,2097152)
[pscustomobject]@{Mode='OS_ONLY_SEED_BUILT';ISOPath=$c0ISO;Bytes=$c0ISOBytes;SHA256=(Get-FileHash -LiteralPath $c0ISO).Hash;GuestProbeSHA256=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'guest_report.py')).Hash;GuestExecuted=$false} | ConvertTo-Json
