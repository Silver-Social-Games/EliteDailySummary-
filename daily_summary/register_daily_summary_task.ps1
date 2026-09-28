# Register Windows Scheduled Task: Elite daily morning reports at 10:00 AM (Israel time, Sun-Sat)
#
# User opted out of scheduled daily summary (2026-09-23; locked 2026-09-28 — never enable).
# Task is registered DISABLED only for legacy cleanup; do not enable in Task Scheduler.
# To remove: Disable-ScheduledTask -TaskName 'Elite_DailySummary_10AM_Israel'
#   or Unregister-ScheduledTask -TaskName 'Elite_DailySummary_10AM_Israel'
#
# Prerequisite: Windows timezone = (UTC+02:00) Jerusalem (Israel Standard/Daylight).
# Run once from project root:
#   powershell -ExecutionPolicy Bypass -File daily_summary\register_daily_summary_task.ps1

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Launcher = Join-Path $ProjectRoot 'daily_summary\run_morning_elite_scheduled.ps1'
if (-not (Test-Path $Launcher)) {
    Write-Error "Launcher not found: $Launcher"
    exit 1
}

$TaskName = 'Elite_DailySummary_10AM_Israel'
$Action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Launcher`" -EnablePagesAutoPublish" `
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
$Description = 'Elite daily summary Sun-Sat 10:00 IL: yesterday report + GitHub Pages publish. WakeToRun if lid closed at 10:00.'

# Interactive/Limited registers without admin; launcher avoids console-session kill on direct python.
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description $Description -Force | Out-Null
Disable-ScheduledTask -TaskName $TaskName | Out-Null

Unregister-ScheduledTask -TaskName 'Elite_DailySummary_11AM' -Confirm:$false -ErrorAction SilentlyContinue

Write-Host "Registered scheduled task: $TaskName (left DISABLED — enable in Task Scheduler if you want auto-run)"
Write-Host '  Runs daily at 10:00 AM Sun-Sat (set Windows timezone to Jerusalem for Israel time)'
Write-Host '  WakeToRun + StartWhenAvailable: catch-up if lid closed/asleep at 10:00'
Write-Host '  Router: daily (yesterday) every day; --force weekend for Thu-Sat bundle'
Write-Host '  GitHub Pages: auto-publish enabled (retries with --skip-pull if pull blocked)'
Write-Host "  Launcher: $Launcher"
Write-Host '  Logs: daily_summary\logs\'
Write-Host '  Output: daily_summary\daily_summaries\'
Write-Host ''
Write-Host 'Windows power (plugged in): Settings > System > Power > Lid close = Do nothing'
Write-Host '  (or enable Wake timers under Sleep) so 10:00 jobs can wake the PC.'
