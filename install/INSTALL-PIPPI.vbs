Option Explicit
Dim shell, fso, base, expectedRoot, governor, mosaicId, dknKey, githubAccount, credentialRef, logPath, command, exitCode, installed, manifestText, revision, regex, matches
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
If WScript.Arguments.Count > 0 Then
  expectedRoot = WScript.Arguments(0)
Else
  expectedRoot = InputBox("Paste the 64-character runtime manifest root from UCM-v0.1-release.json.", _
                          "P/PPI Setup — verify exact runtime")
End If
If Len(expectedRoot) <> 64 Then
  MsgBox "Installation refused: an exact 64-character external runtime root is required.", 16, "P/PPI Setup"
  WScript.Quit 64
End If
governor = InputBox("Name this local Governor profile. This label grants no authority.", _
                    "P/PPI Setup — local profile", "Local Governor")
If Len(Trim(governor)) = 0 Then
  MsgBox "Installation refused: a local Governor label is required.", 16, "P/PPI Setup"
  WScript.Quit 64
End If
mosaicId = InputBox("Optional MosaicID public identifier. Leave blank to bind later.", "P/PPI Setup")
dknKey = InputBox("Optional DKN public key or namespace anchor. Never enter a private key.", "P/PPI Setup")
githubAccount = InputBox("Optional GitHub account name. Leave blank to bind later.", "P/PPI Setup")
credentialRef = InputBox("Optional external credential-provider reference. Never enter a token or password.", "P/PPI Setup")
If Not SafeValue(expectedRoot & governor & mosaicId & dknKey & githubAccount & credentialRef) Then
  MsgBox "Installation refused: onboarding fields contain command-control characters.", 16, "P/PPI Setup"
  WScript.Quit 64
End If
manifestText = fso.OpenTextFile(fso.GetParentFolderName(base) & "\MANIFEST.json", 1, False).ReadAll
Set regex = New RegExp
regex.Pattern = """engineering_revision"":""(r[0-9]{3})"""
regex.Global = False
Set matches = regex.Execute(manifestText)
If matches.Count <> 1 Then
  MsgBox "Installation refused: runtime revision is missing or invalid.", 16, "P/PPI Setup"
  WScript.Quit 64
End If
revision = matches(0).SubMatches(0)
logPath = shell.ExpandEnvironmentStrings("%TEMP%") & "\PIPPI-" & revision & "-INSTALL.log"
command = "cmd.exe /d /s /c powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & _
          base & "\INSTALL-PIPPI.ps1"" -ExpectedRuntimeRoot """ & expectedRoot & _
          """ -NonInteractive -GovernorLabel """ & governor & """ -MosaicID """ & mosaicId & _
          """ -DKNPublicKey """ & dknKey & """ -GitHubAccount """ & githubAccount & _
          """ -GitHubCredentialReference """ & credentialRef & """ 1>""" & logPath & """ 2>&1"
exitCode = shell.Run(command, 0, True)
If exitCode <> 0 Then
  MsgBox "Installation was refused. Diagnostic log:" & vbCrLf & logPath, 16, "P/PPI Setup"
  WScript.Quit exitCode
End If
installed = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Ableman Mosaic\Pippi\v0.1\" & revision & "\PIPPI-INSTALLER.vbs"
MsgBox "P/PPI core installed and verified. The capability-pack installer will open next.", 64, "P/PPI Setup"
If fso.FileExists(installed) Then shell.Run "wscript.exe """ & installed & """", 0, False

Function SafeValue(value)
  Dim forbidden, i
  forbidden = Array(Chr(34), vbCr, vbLf, "&", "|", "<", ">", "^", "%", "!")
  SafeValue = True
  For i = 0 To UBound(forbidden)
    If InStr(value, forbidden(i)) > 0 Then SafeValue = False
  Next
End Function
