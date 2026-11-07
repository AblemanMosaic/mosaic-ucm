param(
 [string]$InstallRoot = "$env:LOCALAPPDATA\Ableman Mosaic\Pippi\v0.1\r014",
 [string]$DataRoot = "$env:LOCALAPPDATA\Ableman Mosaic\Pippi\data",
 [switch]$RemoveUserData,
 [switch]$NoShortcut
)
$ErrorActionPreference='Stop'
$Shortcut="$env:APPDATA\Microsoft\Windows\Start Menu\Programs\P-PPI.lnk"
$Startup="$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\P-PPI-Service.lnk"
if(!$NoShortcut){
 if(Test-Path $Shortcut){Remove-Item -LiteralPath $Shortcut -Force}
 if(Test-Path $Startup){Remove-Item -LiteralPath $Startup -Force}
}
if(Test-Path $InstallRoot){$resolved=(Resolve-Path $InstallRoot).Path;if($resolved -ne $InstallRoot){throw 'PIPPI_UNINSTALL_PATH_REFUSED'};Remove-Item -LiteralPath $resolved -Recurse -Force}
if($RemoveUserData -and (Test-Path $DataRoot)){$resolved=(Resolve-Path $DataRoot).Path;if($resolved -ne $DataRoot){throw 'PIPPI_DATA_PATH_REFUSED'};Remove-Item -LiteralPath $resolved -Recurse -Force}
Write-Host 'P/PPI runtime removed. User data was preserved unless -RemoveUserData was supplied.'


