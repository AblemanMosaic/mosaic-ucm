Option Explicit
Dim shell, fso, base, profile, output, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
profile = "RECOMMENDED_LOCAL"
If WScript.Arguments.Count > 0 Then profile = WScript.Arguments(0)
output = base & "\PIPPI-INSTALL-PLAN.json"
If WScript.Arguments.Count > 1 Then output = WScript.Arguments(1)
command = "cmd.exe /d /s /c """ & base & "\PIPPI-HEADLESS.BAT"" """ & profile & """ """ & output & """"
shell.Run command, 0, False
