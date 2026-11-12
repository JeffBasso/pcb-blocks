# Pester 5 tests for check-blocks.ps1. Needs the PCB design kit's pcb-skidl.ps1 (with its SKiDL venv and
# KiCad 10's kicad-cli): set PCB_KIT_LAUNCHER to the folder that holds it, else C:\dev\pcb is used.
BeforeAll {
    $script:Repo = Split-Path $PSScriptRoot -Parent
    $script:Check = Join-Path $PSScriptRoot 'check-blocks.ps1'
    $script:Kit = $(if ($env:PCB_KIT_LAUNCHER) { $env:PCB_KIT_LAUNCHER } else { 'C:\dev\pcb' })

    # A copy of the repo's checked parts (no .git), so a test can break it.
    function New-RepoCopy {
        $d = Join-Path $TestDrive ('repo-' + [guid]::NewGuid().ToString('N').Substring(0, 6))
        New-Item -ItemType Directory -Force -Path $d | Out-Null
        foreach ($p in 'lib', 'blocks', 'pcb-blocks.kicad_blocks', 'tools') {
            Copy-Item -Recurse -LiteralPath (Join-Path $script:Repo $p) -Destination $d
        }
        return $d
    }
    function Invoke-Check([string]$Root) {
        $out = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script:Check -Root $Root -Kit $script:Kit 2>&1 | Out-String
        return @{ Code = $LASTEXITCODE; Out = $out }
    }
}

Describe 'check-blocks.ps1' {
    It 'parses' {
        $e = $null
        [void][Management.Automation.Language.Parser]::ParseFile($script:Check, [ref]$null, [ref]$e)
        @($e).Count | Should -Be 0
    }
    It 'passes on the repo: parity 0 and every design block identical to its block sheet' {
        $r = Invoke-Check (New-RepoCopy)
        $r.Code | Should -Be 0
        $r.Out | Should -Match 'poe_pd: parity 0, design block identical'
        $r.Out | Should -Match 'All 1 block\(s\) pass'
    }
    It 'fails when a design block differs from its block sheet by one byte' {
        $d = New-RepoCopy
        $f = Join-Path $d 'pcb-blocks.kicad_blocks\poe_pd.kicad_block\poe_pd.kicad_sch'
        [IO.File]::WriteAllBytes($f, [IO.File]::ReadAllBytes($f) + [byte]10)
        $r = Invoke-Check $d
        $r.Code | Should -Be 1
        $r.Out | Should -Match 'poe_pd: the design block differs from blocks\\poe_pd\\poe_pd_sheet\.kicad_sch'
    }
    It 'fails when a design block has no block folder' {
        $d = New-RepoCopy
        Copy-Item -Recurse -LiteralPath (Join-Path $d 'pcb-blocks.kicad_blocks\poe_pd.kicad_block') -Destination (Join-Path $d 'pcb-blocks.kicad_blocks\orphan.kicad_block')
        $r = Invoke-Check $d
        $r.Code | Should -Be 1
        $r.Out | Should -Match 'orphan: a design block with no blocks\\orphan folder'
    }
    It 'fails when a block folder has no design block' {
        $d = New-RepoCopy
        Remove-Item -Recurse -LiteralPath (Join-Path $d 'pcb-blocks.kicad_blocks\poe_pd.kicad_block')
        $r = Invoke-Check $d
        $r.Code | Should -Be 1
        $r.Out | Should -Match 'poe_pd: no design block'
    }
    It 'fails when the Python and the drawing disagree' {
        $d = New-RepoCopy
        $py = Join-Path $d 'blocks\poe_pd\src\blocks\poe_pd.py'
        (Get-Content -Raw -LiteralPath $py) -replace "'24\.9k 1%'", "'25.5k 1%'" | Set-Content -LiteralPath $py -NoNewline
        $r = Invoke-Check $d
        $r.Code | Should -Be 1
        $r.Out | Should -Match "R100 value: '25\.5k 1%' in Python"
        $r.Out | Should -Match 'poe_pd: parity FAILED'
    }
}
