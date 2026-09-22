[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "..\dist")
)

$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$worldSource = Join-Path $repositoryRoot "apworld"
$stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) "wsr-apworld-build"
$stageWorld = Join-Path $stageRoot "wii_sports_resort"
$archivePath = Join-Path $stageRoot "wii_sports_resort.zip"
$outputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$outputPath = Join-Path $outputDirectory "wii_sports_resort.apworld"

if (-not (Test-Path (Join-Path $worldSource "archipelago.json"))) {
    throw "Missing apworld/archipelago.json manifest."
}

Remove-Item $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path (Join-Path $stageWorld "docs") -Force | Out-Null
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

Copy-Item (Join-Path $worldSource "*.py") $stageWorld
Copy-Item (Join-Path $worldSource "archipelago.json") $stageWorld
Copy-Item (Join-Path $worldSource "docs\*.md") (Join-Path $stageWorld "docs")

Compress-Archive -Path $stageWorld -DestinationPath $archivePath -Force
Move-Item $archivePath $outputPath -Force
Remove-Item $stageRoot -Recurse -Force

Write-Host "Built $outputPath"