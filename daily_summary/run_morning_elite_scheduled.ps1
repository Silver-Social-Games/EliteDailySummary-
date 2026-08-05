# Launcher for Windows Task Scheduler — sets credentials, logs output, runs router.
param(
    [switch]$EnablePagesAutoPublish
)

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
$PublishGit = Join-Path $ProjectRoot 'daily_summary\publish_pages_git.py'
Set-Location $ProjectRoot
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
Write-Log "Running: $Python $Script"

& $Python $Script 2>&1 | ForEach-Object {
    Write-Log $_
    $_
}

$code = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 0 }
Write-Log "Morning script exit code: $code"

# Only auto-publish Pages after a successful morning run (includes Fri/Sat skip = 0).
if ($code -ne 0) {
    Write-Log "Skipping docs/ git publish because morning script failed"
    exit $code
}

# Auto-publish is opt-in and currently disabled for the registered scheduled task.
# Keep the implementation available for future use after security/reliability approval.
if (-not $EnablePagesAutoPublish) {
    Write-Log "GitHub Pages auto-publish is disabled; skipping commit and push"
    exit $code
}

if (-not (Test-Path $PublishGit)) {
    Write-Log "WARN: publish helper missing: $PublishGit"
    exit $code
}

Write-Log "Running: $Python $PublishGit"
& $Python $PublishGit 2>&1 | ForEach-Object {
    Write-Log $_
    $_
}
$publishCode = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 0 }
Write-Log "Docs git publish exit code: $publishCode"
if ($publishCode -ne 0) {
    exit $publishCode
}
exit $code
