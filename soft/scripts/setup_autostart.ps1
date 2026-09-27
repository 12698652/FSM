# FSM Food Monitor - Windows Task Scheduler setup
# Usage:
#   register : create autostart task (run at logon) + start now
#   remove   : delete the task
#   run      : start services now
#   status   : show task + service status
# Task name: FSM_FoodMonitor_Services
# Services : mqtt_bridge.py (MQTT receiver) + app.py (Flask web, port 5000)

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("register", "remove", "run", "status")]
    [string]$Action
)

$TaskName = "FSM_FoodMonitor_Services"
$LauncherPath = "c:\Users\Administrator\Desktop\FSM\soft\scripts\start_services.ps1"

switch ($Action) {
    "register" {
        $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($existing) {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
            Write-Output "[ok] old task removed"
        }
        $taskAction = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$LauncherPath`""
        $taskTrigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
        $taskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero)
        Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $taskTrigger `
            -Settings $taskSettings -Description "FSM Food Monitor: MQTT bridge + Flask autostart" | Out-Null
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 4
        $taskOk = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        $flask = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
        if ($taskOk -and $flask) {
            Write-Output "[ok] task registered, Flask listening on port 5000"
            Write-Output "[ok] phone access: http://172.16.3.42:5000"
        } elseif ($taskOk) {
            Write-Output "[ok] task registered, Flask starting... check logs\service.log"
        } else {
            Write-Output "[fail] task NOT registered"
        }
    }
    "remove" {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Output "[ok] autostart removed"
    }
    "run" {
        Start-ScheduledTask -TaskName $TaskName
        Write-Output "[ok] services starting"
    }
    "status" {
        Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
            Format-List TaskName, State | Out-String
        $flask = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
        Write-Output ("Flask port 5000 : " + $(if ($flask) { "LISTENING [ok]" } else { "not running" }))
        $bridge = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" |
            Where-Object { $_.CommandLine -like "*mqtt_bridge*" }
        Write-Output ("mqtt_bridge     : " + $(if ($bridge) { "RUNNING [ok]" } else { "not running" }))
    }
}
