Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) {
        throw $Message
    }
}

function Assert-Path([string]$PathValue) {
    Assert-True (Test-Path $PathValue) "Missing required path: $PathValue"
}

$integrationDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $integrationDir "..\..")
$runtimeClaude = Join-Path $repoRoot ".pai_runtime\.claude"
$settingsPath = Join-Path $runtimeClaude "settings.json"
$skillPath = Join-Path $runtimeClaude "skills\InvestmentCRO\SKILL.md"
$goalsPath = Join-Path $runtimeClaude "skills\InvestmentCRO\USER\GOALS.md"
$thoughtsPath = Join-Path $runtimeClaude "skills\InvestmentCRO\USER\THOUGHTS.md"
$preferencesPath = Join-Path $runtimeClaude "skills\InvestmentCRO\USER\PREFERENCES.md"
$experiencePath = Join-Path $runtimeClaude "skills\InvestmentCRO\USER\EXPERIENCE.md"
$memoryHookPath = Join-Path $runtimeClaude "hooks\InvestmentMemoryUpdate.hook.ts"

Write-Host "Verifying PAI Super Investment Assistant..." -ForegroundColor Cyan

# 1) Core binaries
$bunCmd = Get-Command bun -ErrorAction SilentlyContinue
if (-not $bunCmd) {
    $userBun = Join-Path $HOME ".bun\bin\bun.exe"
    Assert-Path $userBun
} else {
    Write-Host "bun available: $($bunCmd.Source)"
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
Assert-True ($null -ne $pythonCmd) "python is not available in PATH."
Write-Host "python available: $($pythonCmd.Source)"

# 2) Runtime files
Assert-Path $runtimeClaude
Assert-Path $settingsPath
Assert-Path $skillPath
Assert-Path $goalsPath
Assert-Path $thoughtsPath
Assert-Path $preferencesPath
Assert-Path $experiencePath
Assert-Path $memoryHookPath
Write-Host "runtime files: OK"

# 3) settings sanity
$settings = Get-Content -Raw $settingsPath | ConvertFrom-Json
Assert-True ($settings.env.PAI_DIR -eq $runtimeClaude) "settings.env.PAI_DIR mismatch."
Assert-True ($settings.contextFiles -contains "skills/InvestmentCRO/SKILL.md") "InvestmentCRO context file not registered."
Assert-True ($settings.contextFiles -contains "skills/InvestmentCRO/USER/GOALS.md") "GOALS context file not registered."
Assert-True ($settings.contextFiles -contains "skills/InvestmentCRO/USER/THOUGHTS.md") "THOUGHTS context file not registered."
Assert-True ($settings.contextFiles -contains "skills/InvestmentCRO/USER/PREFERENCES.md") "PREFERENCES context file not registered."
Assert-True ($settings.contextFiles -contains "skills/InvestmentCRO/USER/EXPERIENCE.md") "EXPERIENCE context file not registered."
Assert-True ($null -ne $settings.hooks.Stop) "Stop hook not configured."
$stopCommand = $settings.hooks.Stop[0].hooks[0].command
Assert-True ($stopCommand -like "*InvestmentMemoryUpdate.hook.ts*") "Investment memory stop hook command is missing."
Write-Host "settings checks: OK"

# 4) Python finance libs
python -c "import yfinance, akshare, pandas; print('python modules: OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Python module verification failed."
}

Write-Host "Verification passed." -ForegroundColor Green
