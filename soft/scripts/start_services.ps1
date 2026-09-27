# FSM Food Monitor - silent service launcher (PowerShell)
# Started by Task Scheduler (autostart) or manual run
# Starts: mqtt_bridge.py (MQTT receiver) + app.py (Flask web)
# Already-running services are skipped

$Base = "c:\Users\Administrator\Desktop\FSM\soft"
$Pyw = "$Base\.venv\Scripts\pythonw.exe"
$LogDir = "$Base\logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$Log = "$LogDir\service.log"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $Log -Value "[$ts] $msg"
}

# ---- Start Flask web (port 5000) if not listening ----
$flask = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if (-not $flask) {
    Log "starting Flask web (app.py)"
    Start-Process -FilePath $Pyw -ArgumentList "`"$Base\server\app.py`"" -WorkingDirectory $Base -WindowStyle Hidden
} else {
    Log "Flask already running, skip"
}

# ---- Start mqtt_bridge if not running ----
$bridge = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -like "*mqtt_bridge*" }
if (-not $bridge) {
    Log "starting mqtt_bridge.py"
    Start-Process -FilePath $Pyw -ArgumentList "`"$Base\server\mqtt_bridge.py`"" -WorkingDirectory $Base -WindowStyle Hidden
} else {
    Log "mqtt_bridge already running, skip"
}
