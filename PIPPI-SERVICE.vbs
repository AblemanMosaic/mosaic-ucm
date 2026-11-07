Option Explicit
Dim shell, fso, base, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
command = "cmd.exe /d /s /c """ & base & "\PIPPI.cmd"" serve"
shell.Run command, 0, False
