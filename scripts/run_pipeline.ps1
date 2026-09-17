param(
    [string]$Config,
    [string]$AsOf,
    [switch]$Retrain,
    [switch]$RegenerateScenario,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) { throw 'SupplyGuard virtual environment is missing.' }
$pipelineArgs = @('-B', '-m', 'supplyguard.pipeline')
if ($Config) { $pipelineArgs += @('--config', $Config) }
if ($AsOf) { $pipelineArgs += @('--as-of', $AsOf) }
if ($Retrain) { $pipelineArgs += '--retrain' }
if ($RegenerateScenario) { $pipelineArgs += '--regenerate-scenario' }
if ($DryRun) { $pipelineArgs += '--dry-run' }
Push-Location -LiteralPath $projectRoot
try {
    & $pythonPath @pipelineArgs
    $pipelineExit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $pipelineExit
