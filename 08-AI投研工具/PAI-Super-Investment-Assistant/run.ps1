param(
    [ValidateSet("tracker", "bond", "curve", "macro", "policy")]
    [string]$Workflow = "tracker",
    [int]$NewsLimit = 8
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$integrationDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $integrationDir "..\..")

Push-Location $repoRoot
try {
    switch ($Workflow) {
        "tracker" {
            Write-Host "Running daily idea tracking report..." -ForegroundColor Cyan
            python stock_tracker.py run-daily --news-limit $NewsLimit
        }
        "bond" {
            Write-Host "Running full bond snapshot..." -ForegroundColor Cyan
            python bond_data.py --all
        }
        "curve" {
            Write-Host "Running bond curve snapshot..." -ForegroundColor Cyan
            python bond_data.py --curve
        }
        "macro" {
            Write-Host "Running bond macro snapshot..." -ForegroundColor Cyan
            python bond_data.py --macro
        }
        "policy" {
            Write-Host "Running bond policy snapshot..." -ForegroundColor Cyan
            python bond_data.py --policy
        }
    }
}
finally {
    Pop-Location
}
