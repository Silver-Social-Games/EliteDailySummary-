# Launcher for Windows Task Scheduler — sets credentials, logs output, runs router.
$ErrorActionPreference = 'Continue'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot 'daily_summary\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir ("morning_elite_{0:yyyy-MM-dd_HHmmss}.log" -f (Get-Date))

function Write-Log([string]$Message) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $Message
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

Write-Log "Starting morning elite (cwd=$ProjectRoot)"

if (-not $env:GOOGLE_APPLICATION_CREDENTIALS) {
    $DefaultKey = 'c:\Users\Owner\Downloads\key.json.json'
    if (Test-Path $DefaultKey) {
        $env:GOOGLE_APPLICATION_CREDENTIALS = $DefaultKey
        Write-Log "Set GOOGLE_APPLICATION_CREDENTIALS=$DefaultKey"
    } else {
        Write-Log "WARN: GOOGLE_APPLICATION_CREDENTIALS unset and default key missing"
    }
} else {
    Write-Log "GOOGLE_APPLICATION_CREDENTIALS=$($env:GOOGLE_APPLICATION_CREDENTIALS)"
}

$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) {
    $Python = (Get-Command python3 -ErrorAction SilentlyContinue).Source
}
if (-not $Python) {
    Write-Log "ERROR: Python not found on PATH"
    exit 1
}

$Script = Join-Path $ProjectRoot 'daily_summary\generate_morning_elite.py'
Set-Location $ProjectRoot
Write-Log "Running: $Python $Script"

& $Python $Script 2>&1 | ForEach-Object {
    Write-Log $_
    $_
}

$code = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 0 }
Write-Log "Exit code: $code"
exit $code
