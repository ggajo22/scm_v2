' Launch a batch file with no visible console window.
'
' Task Scheduler runs our tasks under an Interactive logon (S4U would avoid
' the window entirely but requires elevation to configure), so the .bat would
' otherwise flash a cmd window on the desktop on every run -- every 5 minutes
' for sync_orders. wscript.exe is the windowless script host, and Run's third
' argument (0) hides the child window.
'
' Usage: wscript.exe run_hidden.vbs "C:\path\to\script.bat"

Option Explicit

Dim shell, target, rc

If WScript.Arguments.Count < 1 Then
    ' No target given: fail loudly rather than silently doing nothing.
    WScript.Quit 2
End If

target = WScript.Arguments(0)
Set shell = CreateObject("WScript.Shell")

' 0    = hidden window
' True = wait for the child to finish, so its exit code can be propagated.
'        Task Scheduler's "Last Run Result" is the only failure signal these
'        jobs have, so swallowing the exit code here would hide every failure.
rc = shell.Run("""" & target & """", 0, True)

WScript.Quit rc
