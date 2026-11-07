param(
 [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')]
 [string]$ExpectedRuntimeRoot,
 [string]$InstallRoot = "$env:LOCALAPPDATA\Ableman Mosaic\Pippi\v0.1\r027",
 [string]$DataRoot = "$env:LOCALAPPDATA\Ableman Mosaic\Pippi\data",
 [string]$GovernorLabel,
 [string]$MosaicID,
 [string]$DKNPublicKey,
 [string]$GitHubAccount,
 [string]$GitHubCredentialReference,
 [switch]$NonInteractive,
 [switch]$NoShortcut
)
$ErrorActionPreference='Stop'
$Source=(Resolve-Path (Split-Path -Parent $PSScriptRoot)).Path
Write-Host 'P/PPI v0.1 r027 externally pinned modular runtime installer'

Write-Host '[1/9] Selecting Python 3.12 or 3.13...'
$PythonExe=$null;$PythonPrefix=@()
foreach($candidate in @(@('py','-3.13'),@('py','-3.12'),@('python'))){
  try{$exe=$candidate[0];$prefix=@($candidate|Select-Object -Skip 1);& $exe @prefix -c 'import sys;assert (3,12)<=sys.version_info[:2]<(3,14)' 2>$null;if($LASTEXITCODE -eq 0){$PythonExe=$exe;$PythonPrefix=$prefix;break}}catch{}
}
if(!$PythonExe){throw 'PIPPI_PYTHON_312_OR_313_REQUIRED'}

Write-Host '[2/9] Verifying the complete extracted UCM runtime...'
$Verifier=Join-Path $Source 'tools\verify_runtime_tree.py'
if(!(Test-Path -LiteralPath $Verifier)){throw 'PIPPI_RUNTIME_VERIFIER_MISSING'}
& $PythonExe @PythonPrefix $Verifier $Source
if($LASTEXITCODE -ne 0){throw 'PIPPI_RUNTIME_SOURCE_REFUSED'}
$Manifest=Get-Content -Raw (Join-Path $Source 'MANIFEST.json')|ConvertFrom-Json
if(([string]$Manifest.root).ToLowerInvariant() -ne $ExpectedRuntimeRoot.ToLowerInvariant()){
  throw 'PIPPI_RUNTIME_EXTERNAL_ROOT_MISMATCH'
}

Write-Host '[3/9] Staging the exact immutable runtime...'
$InstallRoot=[IO.Path]::GetFullPath($InstallRoot)
$InstallParent=[IO.Path]::GetFullPath((Split-Path -Parent $InstallRoot))
New-Item -ItemType Directory -Force -Path $InstallParent|Out-Null
$Stage=[IO.Path]::GetFullPath("$InstallRoot.pending.$PID")
if(!$Stage.StartsWith($InstallParent+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'PIPPI_STAGE_PATH_REFUSED'}
if(Test-Path -LiteralPath $Stage){$resolved=(Resolve-Path -LiteralPath $Stage).Path;if($resolved-ne$Stage){throw 'PIPPI_STAGE_PATH_REFUSED'};Remove-Item -LiteralPath $resolved -Recurse -Force}
New-Item -ItemType Directory -Path $Stage|Out-Null
Copy-Item -LiteralPath (Join-Path $Source 'MANIFEST.json') -Destination $Stage
foreach($row in $Manifest.members){
  $relative=[string]$row.path
  $sourcePath=[IO.Path]::GetFullPath((Join-Path $Source $relative))
  $targetPath=[IO.Path]::GetFullPath((Join-Path $Stage $relative))
  if(!$sourcePath.StartsWith($Source+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or !$targetPath.StartsWith($Stage+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'PIPPI_RUNTIME_MEMBER_PATH_REFUSED'}
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $targetPath)|Out-Null
  Copy-Item -LiteralPath $sourcePath -Destination $targetPath
}
& $PythonExe @PythonPrefix (Join-Path $Stage 'tools\verify_runtime_tree.py') $Stage
if($LASTEXITCODE -ne 0){throw 'PIPPI_STAGED_RUNTIME_REFUSED'}
$StagedManifest=Get-Content -Raw (Join-Path $Stage 'MANIFEST.json')|ConvertFrom-Json
if(([string]$StagedManifest.root).ToLowerInvariant() -ne $ExpectedRuntimeRoot.ToLowerInvariant()){
  throw 'PIPPI_STAGED_RUNTIME_EXTERNAL_ROOT_MISMATCH'
}

Write-Host '[4/9] Activating the immutable r027 runtime...'
if(Test-Path -LiteralPath $InstallRoot){
  & $PythonExe @PythonPrefix (Join-Path $InstallRoot 'tools\verify_runtime_tree.py') $InstallRoot
  if($LASTEXITCODE -ne 0){throw 'PIPPI_EXISTING_RUNTIME_REFUSED'}
  $ExistingManifest=Get-Content -Raw (Join-Path $InstallRoot 'MANIFEST.json')|ConvertFrom-Json
  if(([string]$ExistingManifest.root).ToLowerInvariant() -ne $ExpectedRuntimeRoot.ToLowerInvariant()){
    throw 'PIPPI_EXISTING_RUNTIME_EXTERNAL_ROOT_MISMATCH'
  }
  $existing=(Get-FileHash (Join-Path $InstallRoot 'MANIFEST.json') -Algorithm SHA256).Hash
  $incoming=(Get-FileHash (Join-Path $Stage 'MANIFEST.json') -Algorithm SHA256).Hash
  if($existing-ne$incoming){throw 'PIPPI_IMMUTABLE_REVISION_CONFLICT'}
  Remove-Item -LiteralPath $Stage -Recurse -Force
}else{
  $resolvedStage=(Resolve-Path -LiteralPath $Stage).Path
  if($resolvedStage-ne$Stage){throw 'PIPPI_STAGE_PATH_REFUSED'}
  Move-Item -LiteralPath $resolvedStage -Destination $InstallRoot
}

Write-Host '[5/9] Onboarding this user installation...'
if(!(Test-Path "$DataRoot\ONBOARDING.json")){
  if($NonInteractive){
    if(!$GovernorLabel){throw 'PIPPI_NONINTERACTIVE_GOVERNOR_LABEL_REQUIRED'}
  }else{
    if(!$GovernorLabel){$GovernorLabel=Read-Host 'Local Governor label'}
    Write-Host 'Optional public bindings may be left blank and added later. Never paste a private key or token.'
    if($null-eq$MosaicID){$MosaicID=Read-Host 'MosaicID public identifier (optional; Enter to skip for now)'}
    if($null-eq$DKNPublicKey){$DKNPublicKey=Read-Host 'DKN public key / namespace anchor (optional; Enter to skip; never enter a private key)'}
    if($null-eq$GitHubAccount){$GitHubAccount=Read-Host 'GitHub account (optional; Enter to skip for now)'}
    if($null-eq$GitHubCredentialReference){$GitHubCredentialReference=Read-Host 'External credential reference (optional; Enter to skip for now)'}
  }
  $arglist=@('--data-root',$DataRoot,'onboard','--governor-label',$GovernorLabel)
  if($MosaicID){$arglist+=@('--mosaic-id',$MosaicID)};if($DKNPublicKey){$arglist+=@('--dkn-public-key',$DKNPublicKey)}
  if($GitHubAccount){$arglist+=@('--github-account',$GitHubAccount)};if($GitHubCredentialReference){$arglist+=@('--github-credential-reference',$GitHubCredentialReference)}
  & "$InstallRoot\PIPPI.cmd" @arglist
  if($LASTEXITCODE -ne 0){throw 'PIPPI_ONBOARDING_REFUSED'}
}

Write-Host '[6/9] Creating no-console native shortcuts...'
if(!$NoShortcut){
  $Shell=New-Object -ComObject WScript.Shell
  $Shortcut=$Shell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\P-PPI.lnk")
  $Shortcut.TargetPath="$env:SystemRoot\System32\wscript.exe";$Shortcut.Arguments="`"$InstallRoot\PIPPI-DASHBOARD.vbs`"";$Shortcut.WorkingDirectory=$InstallRoot;$Shortcut.Description='Mosaic P/PPI constitutional project dashboard';$Shortcut.Save()
  $InstallerShortcut=$Shell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\P-PPI Setup.lnk")
  $InstallerShortcut.TargetPath="$env:SystemRoot\System32\wscript.exe";$InstallerShortcut.Arguments="`"$InstallRoot\PIPPI-INSTALLER.vbs`"";$InstallerShortcut.WorkingDirectory=$InstallRoot;$InstallerShortcut.Description='Mosaic P/PPI capability pack setup';$InstallerShortcut.Save()
  $Startup=$Shell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\P-PPI-Service.lnk")
  $Startup.TargetPath="$env:SystemRoot\System32\wscript.exe";$Startup.Arguments="`"$InstallRoot\PIPPI-SERVICE.vbs`"";$Startup.WorkingDirectory=$InstallRoot;$Startup.Description='Mosaic P/PPI local coordination service';$Startup.Save()
}

Write-Host '[7/9] Verifying installed runtime and governed state...'
& $PythonExe @PythonPrefix (Join-Path $InstallRoot 'tools\verify_runtime_tree.py') $InstallRoot
if($LASTEXITCODE -ne 0){throw 'PIPPI_INSTALL_RUNTIME_VERIFY_REFUSED'}
$InstalledManifest=Get-Content -Raw (Join-Path $InstallRoot 'MANIFEST.json')|ConvertFrom-Json
if(([string]$InstalledManifest.root).ToLowerInvariant() -ne $ExpectedRuntimeRoot.ToLowerInvariant()){
  throw 'PIPPI_INSTALLED_RUNTIME_EXTERNAL_ROOT_MISMATCH'
}
& "$InstallRoot\PIPPI.cmd" --data-root $DataRoot verify
if($LASTEXITCODE -ne 0){throw 'PIPPI_INSTALL_STATE_VERIFY_REFUSED'}

Write-Host '[8/9] Initializing the optional pack inventory...'
& "$InstallRoot\PIPPI.cmd" --data-root $DataRoot pack-inventory | Out-Null
if($LASTEXITCODE -ne 0){throw 'PIPPI_PACK_INVENTORY_INITIALIZATION_REFUSED'}

Write-Host '[9/9] Installation complete.'
Write-Host "Dashboard: $InstallRoot\PIPPI-DASHBOARD.vbs"
Write-Host "Capability installer: $InstallRoot\PIPPI-INSTALLER.vbs"
Write-Host "Headless planner: $InstallRoot\PIPPI-HEADLESS.vbs"
Write-Host "CLI: $InstallRoot\PIPPI.cmd"

