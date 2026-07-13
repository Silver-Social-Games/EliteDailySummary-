# Register Windows Scheduled Task: Elite Sun-Thu morning reports at 10:00 AM (Israel time)
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
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Launcher`"" `
    -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At '10:00AM'
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew `
    -RestartCount 1 `
    -RestartInterval (New-TimeSpan -Minutes 10)
$Description = 'Elite Sun-Thu morning reports: Sunday weekend (Thu-Sat), Mon-Thu daily, Fri/Sat skip. 10:00 AM Israel local time.'

# Interactive/Limited registers without admin; launcher avoids console-session kill on direct python.
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description $Description -Force | Out-Null

Unregister-ScheduledTask -TaskName 'Elite_DailySummary_11AM' -Confirm:$false -ErrorAction SilentlyContinue

Write-Host "Registered scheduled task: $TaskName"
Write-Host '  Runs daily at 10:00 AM (set Windows timezone to Jerusalem for Israel time)'
Write-Host '  Router: Sunday=weekend, Mon-Thu=daily, Fri/Sat=skip'
Write-Host "  Launcher: $Launcher"
Write-Host '  Logs: daily_summary\logs\'
Write-Host '  Output: daily_summary\daily_summaries\'
