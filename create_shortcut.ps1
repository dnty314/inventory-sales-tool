param(
    [Parameter(Mandatory=$true)]
    [string]$TargetExe,

    [Parameter(Mandatory=$true)]
    [string]$ShortcutPath,

    [string]$WorkingDirectory = "",
    [string]$Arguments = "",
    [string]$IconPath = ""
)

if (-not (Test-Path $TargetExe)) {
    throw "Target exe not found: $TargetExe"
}

$TargetExe = (Resolve-Path $TargetExe).Path
$TargetDir = Split-Path -Parent $TargetExe

if ([string]::IsNullOrWhiteSpace($WorkingDirectory)) {
    $WorkingDirectory = $TargetDir
}
if ([string]::IsNullOrWhiteSpace($IconPath)) {
    $IconPath = $TargetExe
}

$ShortcutDir = Split-Path -Parent $ShortcutPath
if (-not (Test-Path $ShortcutDir)) {
    New-Item -ItemType Directory -Path $ShortcutDir | Out-Null
}

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetExe
$Shortcut.WorkingDirectory = $WorkingDirectory
$Shortcut.Arguments = $Arguments
$Shortcut.IconLocation = $IconPath
$Shortcut.Save()

Write-Host "Created shortcut: $ShortcutPath"
Write-Host "Target: $TargetExe"
Write-Host "Start in: $WorkingDirectory"
