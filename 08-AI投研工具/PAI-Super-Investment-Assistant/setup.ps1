Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section([string]$Title) {
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Ensure-Bun {
    Write-Section "Checking Bun"
    $bunCmd = Get-Command bun -ErrorAction SilentlyContinue
    if ($bunCmd) {
        Write-Host "bun found: $($bunCmd.Source)"
        return
    }

    $userBun = Join-Path $HOME ".bun\bin\bun.exe"
    if (Test-Path $userBun) {
        $env:Path = "$($HOME)\.bun\bin;$env:Path"
        Write-Host "bun loaded from $userBun"
        return
    }

    Write-Host "bun not found. Installing with official script..."
    powershell -c "irm bun.sh/install.ps1 | iex"
    $env:Path = "$($HOME)\.bun\bin;$env:Path"
    if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
        throw "bun installation completed but bun is still not available in this session."
    }
}

function Robocopy-Safe([string]$Source, [string]$Target) {
    if (-not (Test-Path $Source)) {
        throw "Source path not found: $Source"
    }
    if (-not (Test-Path $Target)) {
        New-Item -ItemType Directory -Path $Target -Force | Out-Null
    }

    $null = robocopy $Source $Target /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
    $code = $LASTEXITCODE
    if ($code -gt 7) {
        throw "robocopy failed with exit code $code"
    }
}

Write-Section "Resolving Paths"
$integrationDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $integrationDir "..\..")
$aiToolsDir = Split-Path -Parent $integrationDir
$primaryRepo = Join-Path $aiToolsDir "Personal_AI_Infrastructure"
$fallbackRepo = Join-Path $aiToolsDir "Personal_AI_Infrastructure_upstream"
$upstreamRepo = if (Test-Path $primaryRepo) { $primaryRepo } else { $fallbackRepo }
$releaseClaude = Join-Path $upstreamRepo "Releases\v2.5\.claude"
$runtimeRoot = Join-Path $repoRoot ".pai_runtime"
$runtimeClaude = Join-Path $runtimeRoot ".claude"
$templateSkill = Join-Path $integrationDir "templates\InvestmentCRO"
$templateHooks = Join-Path $integrationDir "templates\hooks"
$runtimeSkill = Join-Path $runtimeClaude "skills\InvestmentCRO"
$runtimeHooks = Join-Path $runtimeClaude "hooks"

Write-Host "Repo root:      $repoRoot"
Write-Host "Upstream repo:  $upstreamRepo"
Write-Host "Runtime dir:    $runtimeClaude"

Write-Section "Preparing Dependencies"
Ensure-Bun

Write-Section "Ensuring Upstream PAI Repo"
if (-not (Test-Path $upstreamRepo)) {
    Write-Host "Cloning upstream PAI repo..."
    git clone https://github.com/danielmiessler/Personal_AI_Infrastructure.git $primaryRepo
    $upstreamRepo = $primaryRepo
    $releaseClaude = Join-Path $upstreamRepo "Releases\v2.5\.claude"
} else {
    Write-Host "Upstream repo exists. Pulling latest..."
    git -C $upstreamRepo pull --ff-only
}

if (-not (Test-Path $releaseClaude)) {
    throw "Release .claude directory not found: $releaseClaude"
}

Write-Section "Creating Local Runtime"
if (-not (Test-Path $runtimeRoot)) {
    New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
}

Robocopy-Safe -Source $releaseClaude -Target $runtimeClaude
Robocopy-Safe -Source $templateSkill -Target $runtimeSkill
Robocopy-Safe -Source $templateHooks -Target $runtimeHooks

Write-Section "Patching settings.json for Windows-safe Local Runtime"
$settingsPath = Join-Path $runtimeClaude "settings.json"
if (-not (Test-Path $settingsPath)) {
    throw "settings.json not found: $settingsPath"
}

$settings = Get-Content -Raw $settingsPath | ConvertFrom-Json
$settings.env.PAI_DIR = $runtimeClaude
$settings.env.PROJECTS_DIR = [string]$repoRoot
$settings.daidentity.name = "InvestmentCRO"
$settings.daidentity.displayName = "InvestmentCRO"
$settings.daidentity.fullName = "InvestmentCRO - PAI Investment Assistant"

if (-not $settings.contextFiles) {
    $settings | Add-Member -MemberType NoteProperty -Name "contextFiles" -Value @()
}
if ($settings.contextFiles -notcontains "skills/InvestmentCRO/SKILL.md") {
    $settings.contextFiles += "skills/InvestmentCRO/SKILL.md"
}
foreach ($profileFile in @(
    "skills/InvestmentCRO/USER/GOALS.md",
    "skills/InvestmentCRO/USER/THOUGHTS.md",
    "skills/InvestmentCRO/USER/PREFERENCES.md",
    "skills/InvestmentCRO/USER/EXPERIENCE.md"
)) {
    if ($settings.contextFiles -notcontains $profileFile) {
        $settings.contextFiles += $profileFile
    }
}

# Windows-safe hooks: keep only continuous memory update on Stop.
$settings.hooks = @{
    Stop = @(
        @{
            hooks = @(
                @{
                    type = "command"
                    command = "bun `"`${PAI_DIR}/hooks/InvestmentMemoryUpdate.hook.ts`""
                }
            )
        }
    )
}
if ($settings.PSObject.Properties.Name -contains "statusLine") {
    $settings.PSObject.Properties.Remove("statusLine")
}

$settingsJson = $settings | ConvertTo-Json -Depth 100
Set-Content -Path $settingsPath -Value $settingsJson -Encoding UTF8

$runtimePointer = Join-Path $runtimeRoot "USE_THIS_PAI_DIR.txt"
Set-Content -Path $runtimePointer -Value $runtimeClaude -Encoding UTF8

Write-Section "Setup Complete"
Write-Host "Local runtime ready at: $runtimeClaude" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "1) $integrationDir\verify.ps1"
Write-Host "2) $integrationDir\run.ps1 -Workflow tracker -NewsLimit 8"
Write-Host "3) Review custom skill: $runtimeSkill\SKILL.md"
