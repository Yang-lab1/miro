$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $RepoRoot "backend"
$BackendPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$SmokeScript = Join-Path $RepoRoot "scripts\live-review-smoke.js"
$SmokeOutputDir = Join-Path $RepoRoot "output\playwright\live-smoke"
$SmokeSummaryPath = Join-Path $SmokeOutputDir "run-summary.json"
$BackendOrigin = if ($env:MIRO_BACKEND_URL) { $env:MIRO_BACKEND_URL.TrimEnd("/") } else { "http://127.0.0.1:8000" }
$BackendHealthUrl = "$BackendOrigin/api/v1/health"
$BackendStdoutLog = Join-Path $SmokeOutputDir "verify-all-backend.log"
$BackendStderrLog = Join-Path $SmokeOutputDir "verify-all-backend.err.log"
$SmokeDatabasePath = (Join-Path $BackendDir "smoke.db").Replace("\", "/")
$BackendDatabaseUrl = "sqlite+pysqlite:///$SmokeDatabasePath"

$StartedBackend = $false
$BackendProcess = $null
$OriginalDatabaseUrl = if (Test-Path Env:DATABASE_URL) { $env:DATABASE_URL } else { $null }

function Write-Run([string]$Label) {
  Write-Host "RUN  $Label"
}

function Write-Pass([string]$Label) {
  Write-Host "PASS $Label" -ForegroundColor Green
}

function Write-Fail([string]$Label, [string]$Message) {
  Write-Host "FAIL $Label - $Message" -ForegroundColor Red
}

function Invoke-Step([string]$Label, [scriptblock]$Action) {
  Write-Run $Label
  try {
    & $Action
    Write-Pass $Label
  } catch {
    $message = $_.Exception.Message
    Write-Fail $Label $message
    throw
  }
}

function Test-HealthyEndpoint([string]$Url) {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
    return $response.StatusCode -eq 200
  } catch {
    return $false
  }
}

function Wait-ForHealthyEndpoint([string]$Url, [int]$TimeoutSeconds = 30) {
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-HealthyEndpoint $Url) {
      return $true
    }
    Start-Sleep -Milliseconds 500
  }
  return $false
}

function Start-LocalBackend() {
  if (!(Test-Path $BackendPython)) {
    throw "Backend venv python not found at $BackendPython"
  }

  New-Item -ItemType Directory -Path $SmokeOutputDir -Force | Out-Null
  Set-Content -Path $BackendStdoutLog -Value "" -Encoding UTF8
  Set-Content -Path $BackendStderrLog -Value "" -Encoding UTF8

  $env:DATABASE_URL = $BackendDatabaseUrl
  $script:BackendProcess = Start-Process `
    -FilePath $BackendPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $BackendDir `
    -PassThru `
    -WindowStyle Hidden `
    -RedirectStandardOutput $BackendStdoutLog `
    -RedirectStandardError $BackendStderrLog
  $script:StartedBackend = $true

  if (-not (Wait-ForHealthyEndpoint $BackendHealthUrl 30)) {
    throw "Backend did not become healthy at $BackendHealthUrl. Check $BackendStdoutLog and $BackendStderrLog."
  }
}

function Stop-LocalBackend() {
  if ($script:StartedBackend -and $script:BackendProcess) {
    try {
      if (-not $script:BackendProcess.HasExited) {
        Stop-Process -Id $script:BackendProcess.Id -Force
      }
    } catch {}
  }
}

function Restore-DatabaseUrl() {
  if ($null -ne $OriginalDatabaseUrl) {
    $env:DATABASE_URL = $OriginalDatabaseUrl
    return
  }

  if (Test-Path Env:DATABASE_URL) {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
  }
}

try {
  Invoke-Step "tooling prerequisites" {
    if (!(Test-Path $BackendPython)) {
      throw "Missing backend python: $BackendPython"
    }

    $null = Get-Command node -ErrorAction Stop
  }

  Invoke-Step "backend ruff" {
    Push-Location $BackendDir
    try {
      & $BackendPython -m ruff check app tests
    } finally {
      Pop-Location
    }
  }

  Invoke-Step "backend pytest" {
    Push-Location $BackendDir
    try {
      & $BackendPython -m pytest tests -q
    } finally {
      Pop-Location
    }
  }

  Invoke-Step "backend health" {
    if (-not (Test-HealthyEndpoint $BackendHealthUrl)) {
      Start-LocalBackend
    }
  }

  Invoke-Step "frontend live smoke" {
    Push-Location $RepoRoot
    try {
      & node $SmokeScript
    } finally {
      Pop-Location
    }
  }

  Invoke-Step "smoke summary" {
    if (!(Test-Path $SmokeSummaryPath)) {
      throw "Smoke summary not found at $SmokeSummaryPath"
    }

    $summary = Get-Content $SmokeSummaryPath -Raw | ConvertFrom-Json
    if (-not $summary.passed) {
      throw "Smoke summary reports passed=false"
    }

    Write-Host ("INFO coreStableScenarioCount={0}" -f $summary.coreStableScenarioCount)
    Write-Host ("INFO optionalStableScenarioCount={0}" -f $summary.optionalStableScenarioCount)
    Write-Host ("INFO stableScenarioCount={0}" -f $summary.stableScenarioCount)
    Write-Host ("INFO unstableScenarioCount={0}" -f $summary.unstableScenarioCount)
    Write-Host ("INFO passed={0}" -f $summary.passed)
  }

  Write-Host "PASS verify-all" -ForegroundColor Green
  exit 0
} finally {
  Stop-LocalBackend
  Restore-DatabaseUrl
}
