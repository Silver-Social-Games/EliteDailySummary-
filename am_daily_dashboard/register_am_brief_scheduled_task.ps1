# Register Windows Scheduled Task: Elite AM Brief Sun-Thu at 10:00 AM (Israel time)
#
# Prerequisite: Windows timezone = (UTC+02:00) Jerusalem (Israel Standard/Daylight).
# Run once from project root:
#   powershell -ExecutionPolicy Bypass -File am_daily_dashboard\register_am_brief_scheduled_task.ps1
#
# Generates yesterday's brief, verifies, and mirrors to Elite_Cursor (OneDrive).
# Slack is OFF — pass -EnableAmBriefSlack to run_am_brief_scheduled.ps1 manually if needed.

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Launcher = Join-Path $ProjectRoot 'am_daily_dashboard\run_am_brief_scheduled.ps1'
if (-not (Test-Path $Launcher)) {
    Write-Error "Launcher not found: $Launcher"
    exit 1
}

$TaskName = 'Elite_AMBrief_10AM_Israel'
$Action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Launcher`"" `
    -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At '10:00AM'
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -WakeToRun `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew `
    -RestartCount 1 `
    -RestartInterval (New-TimeSpan -Minutes 10)
$Description = 'Elite AM Brief daily 10:00 IL: catch-up + verify + OneDrive mirror. Wake catch-up if PC slept at 10:00. Slack off by default.'

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description $Description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host '  Runs daily at 10:00 AM (set Windows timezone to Jerusalem for Israel time)'
Write-Host '  WakeToRun + StartWhenAvailable: catch-up if lid closed/asleep at 10:00'
Write-Host '  RunOnlyIfNetworkAvailable: waits for network after wake'
Write-Host '  Daily catch-up + verify + Elite_Cursor mirror (Sun-Sat)'
Write-Host "  Launcher: $Launcher"
Write-Host '  Logs: am_daily_dashboard\logs\'
Write-Host '  Output: Elite_Cursor\AM Brief\{Manager|Coral|Gabriel|Lee|Rachel}\'
Write-Host '  Slack: disabled (manual only via run_am_brief_scheduled.ps1 -EnableAmBriefSlack)'
