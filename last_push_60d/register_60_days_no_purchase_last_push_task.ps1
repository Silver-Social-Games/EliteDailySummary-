# Register Windows Scheduled Task: 60 Days No Purchase Last Push (quarterly, 1st of month)
# Run once from project root (Administrator may be required):
#   powershell -ExecutionPolicy Bypass -File last_push_60d\register_60_days_no_purchase_last_push_task.ps1
#
# Schedule: 1st of Jan, Apr, Jul, Oct at 09:00 — next run 2026-10-01

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) {
    $Python = (Get-Command python3 -ErrorAction SilentlyContinue).Source
}
if (-not $Python) {
    Write-Error "Python not found on PATH."
    exit 1
}

$Script = Join-Path $ProjectRoot "last_push_60d\generate_60_days_no_purchase_last_push.py"
$TaskName = "60 Days No Purchase Last Push"
$User = $env:USERNAME

$TaskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Quarterly Elite export: no purchase in 60d, active accounts. Output: last_push_60d/exports/</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-10-01T09:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <Months>
          <January />
          <April />
          <July />
          <October />
        </Months>
        <DaysOfMonth>
          <Day>1</Day>
        </DaysOfMonth>
      </ScheduleByMonth>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$User</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$Python</Command>
      <Arguments>"$Script"</Arguments>
      <WorkingDirectory>$ProjectRoot</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Xml $TaskXml -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "  Runs: 1st of Jan, Apr, Jul, Oct at 09:00"
Write-Host "  Next run: 2026-10-01 09:00"
Write-Host "  Script: $Script"
Write-Host "  Output: $ProjectRoot\last_push_60d\exports\"
