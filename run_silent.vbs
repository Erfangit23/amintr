' XAUUSD AutoTrader — Silent Launcher (Watchdog Mode)
' Runs run_watchdog.bat invisibly — auto-restarts on any crash
' Use this for Task Scheduler or Startup folder

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' ── CONFIGURE THIS PATH ──
' Change to the actual folder on your VPS:
projectDir = "C:\Users\Administrator\Desktop\xauusd-autotrader"
' If you placed this .vbs inside the project folder itself, use:
' projectDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' ── Ensure log directory exists ──
logDir = projectDir & "\src\logs"
If Not objFSO.FolderExists(logDir) Then
    objFSO.CreateFolder(logDir)
End If

' Log
objFSO.OpenTextFile(logDir & "\startup.log", 8, True).WriteLine _
    Now & " [VBS] Launching watchdog..."

' Run the watchdog bat file (hidden, don't wait)
objShell.Run """" & projectDir & "\run_watchdog.bat""", 0, False

WScript.Quit 0
