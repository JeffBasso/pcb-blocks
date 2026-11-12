<#
.SYNOPSIS
    Checks every pcb-blocks block: its Python and its drawing agree (netlist parity 0), and its KiCad
    design block is a byte-identical copy of the drawn block sheet.

.DESCRIPTION
      check-blocks.ps1 [-Root <repo>] [-Kit <folder with pcb-skidl.ps1>]
    For each blocks\<name>\ it runs the PCB design kit's pcb-skidl.ps1 (-Libs <repo>\lib, so the repo's
    own library is used), then compares pcb-blocks.kicad_blocks\<name>.kicad_block\<name>.kicad_sch with
    blocks\<name>\<name>_sheet.kicad_sch. A block folder without a design block, or a design block
    without a block folder, fails too.
    -Kit defaults to C:\dev\pcb, where the kit installs pcb-skidl.ps1 (it needs the kit's SKiDL venv and
    KiCad 10's kicad-cli). Runs under Windows PowerShell 5.1 or PowerShell 7.
    Exit codes: 0 every block passes; 1 a block fails; 2 pcb-skidl.ps1 wasn't found.
#>
param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent),
    [string]$Kit = 'C:\dev\pcb'
)

$skidl = Join-Path $Kit 'pcb-skidl.ps1'
if (-not (Test-Path -LiteralPath $skidl)) { Write-Host "No pcb-skidl.ps1 in $Kit (install the PCB design kit, or pass -Kit)." -ForegroundColor Red; exit 2 }
$Root = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\')
$lib = Join-Path $Root 'lib'
$dbLib = Join-Path $Root 'pcb-blocks.kicad_blocks'

$blocks = @(Get-ChildItem -LiteralPath (Join-Path $Root 'blocks') -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
$designs = @(Get-ChildItem -LiteralPath $dbLib -Directory -Filter '*.kicad_block' -ErrorAction SilentlyContinue | ForEach-Object { $_.Name -replace '\.kicad_block$', '' })
$failed = 0

foreach ($d in ($designs | Where-Object { $blocks -notcontains $_ })) {
    Write-Host "$d`: a design block with no blocks\$d folder" -ForegroundColor Red
    $failed++
}

foreach ($b in $blocks) {
    $dir = Join-Path $Root "blocks\$b"
    Write-Host "--- $b"
    $out = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $skidl $dir -Libs $lib 2>&1
    $code = $LASTEXITCODE
    # stderr lines come back as ErrorRecords; print their text, and skip the empty ones (Windows
    # PowerShell 5.1 prints an empty stderr line as its type name, System.Management.Automation.RemoteException).
    $out | ForEach-Object { if ($_ -is [Management.Automation.ErrorRecord]) { $_.Exception.Message } else { "$_" } } |
        Where-Object { $_.Trim() -and $_.Trim() -ne 'System.Management.Automation.RemoteException' } |
        ForEach-Object { Write-Host "  $_" }
    $ok = $true
    if ($code -ne 0) { Write-Host "$b`: parity FAILED (pcb-skidl.ps1 exit $code)" -ForegroundColor Red; $ok = $false }
    $sheet = Join-Path $dir "$($b)_sheet.kicad_sch"
    $copy = Join-Path $dbLib "$b.kicad_block\$b.kicad_sch"
    if (-not (Test-Path -LiteralPath $copy)) { Write-Host "$b`: no design block ($dbLib\$b.kicad_block\$b.kicad_sch)" -ForegroundColor Red; $ok = $false }
    elseif (-not (Test-Path -LiteralPath $sheet)) { Write-Host "$b`: no block sheet (blocks\$b\$($b)_sheet.kicad_sch)" -ForegroundColor Red; $ok = $false }
    else {
        $x = [IO.File]::ReadAllBytes($sheet)
        $y = [IO.File]::ReadAllBytes($copy)
        if ($x.Length -ne $y.Length -or [Convert]::ToBase64String($x) -ne [Convert]::ToBase64String($y)) {
            Write-Host "$b`: the design block differs from blocks\$b\$($b)_sheet.kicad_sch (copy the sheet over it)" -ForegroundColor Red
            $ok = $false
        }
    }
    if ($ok) { Write-Host "$b`: parity 0, design block identical" -ForegroundColor Green } else { $failed++ }
}

if ($failed) { Write-Host "$failed problem(s) in $($blocks.Count) block(s)." -ForegroundColor Red; exit 1 }
Write-Host "All $($blocks.Count) block(s) pass." -ForegroundColor Green
exit 0
