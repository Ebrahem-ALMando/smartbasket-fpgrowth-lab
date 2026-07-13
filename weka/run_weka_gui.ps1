$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$javaw = Join-Path $projectRoot "tools\weka\distribution\jre\jre-25.0.2-full\bin\javaw.exe"
$wekaJar = Join-Path $projectRoot "tools\weka\distribution\weka.jar"
$wekaHome = Join-Path $projectRoot "tools\weka\home"
$arff = Join-Path $projectRoot "weka\datasets\online_retail_uk_binary_sparse.arff"

foreach ($required in @($javaw, $wekaJar, $arff)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required Phase 6 artifact is missing: $required"
    }
}
New-Item -ItemType Directory -Force -Path $wekaHome | Out-Null

$arguments = @(
    "--add-opens=java.base/java.lang=ALL-UNNAMED",
    "-Xmx4g",
    "-DWEKA_HOME=$wekaHome",
    "-cp", $wekaJar,
    "weka.gui.GUIChooser"
)

Write-Host "Starting official WEKA GUIChooser 3.8.7."
Write-Host "Dataset to open in Explorer: $arff"
Start-Process -FilePath $javaw -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Normal
