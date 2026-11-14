param(
    [string]$Game = 'C:\Program Files (x86)\Steam\steamapps\common\Frostpunk',
    [ValidateRange(5, 30)][int]$Seconds = 15,
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\build\startup-check')
)
$ErrorActionPreference = 'Stop'
if (Get-Process Frostpunk -ErrorAction SilentlyContinue) {
    throw 'Frostpunk is already running. This check will not interrupt your session.'
}
$gameFolder = (Resolve-Path -LiteralPath $Game).Path
$diagnosticFolder = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $diagnosticFolder | Out-Null
$consolePath = Join-Path $gameFolder 'ConsoleOutput.html'
$startedUtc = [DateTime]::UtcNow
$gameTest = Start-Process -FilePath (Join-Path $gameFolder 'Frostpunk.exe') -WorkingDirectory $gameFolder -ArgumentList '-devconsole' -WindowStyle Hidden -PassThru
$exitedEarly = $false
$exitCode = $null
try {
    $exitedEarly = $gameTest.WaitForExit($Seconds * 1000)
    if ($exitedEarly) { $exitCode = $gameTest.ExitCode }
} finally {
    if (-not $gameTest.HasExited) {
        $null = $gameTest.CloseMainWindow()
        if (-not $gameTest.WaitForExit(5000)) { $gameTest.Kill(); $gameTest.WaitForExit() }
    }
}
$log = Get-Item -LiteralPath $consolePath
if ($log.LastWriteTimeUtc -lt $startedUtc) { throw 'Frostpunk did not write a fresh console log.' }
$captured = Join-Path $diagnosticFolder 'startup.html'
Copy-Item -LiteralPath $consolePath -Destination $captured
$loaded = [Collections.Generic.HashSet[string]]::new()
$errorsFound = 0
foreach ($line in [IO.File]::ReadLines($captured)) {
    if ($line -match 'Configuration file (Frostpunk\w+Config) loaded') { $null = $loaded.Add($Matches[1]) }
    if ($line.Contains('Class factory cannot create') -or $line.Contains('SERIALIZATIONFLAG_VERSIONTOLERANT') -or $line.Contains('inflate() failed')) { $errorsFound++ }
}
$required = @('FrostpunkScenariosConfig', 'FrostpunkDifficultyConfig', 'FrostpunkTechnologiesConfig', 'FrostpunkBlueprintsConfig', 'FrostpunkModifiersConfig', 'FrostpunkAbilitiesConfig', 'FrostpunkGraphicsConfig')
$missing = @($required | Where-Object { -not $loaded.Contains($_) })
$passed = (-not $exitedEarly) -and $errorsFound -eq 0 -and $missing.Count -eq 0
@{
    passed = $passed; started_utc = $startedUtc.ToString('o'); process_id = $gameTest.Id
    exited_during_startup = $exitedEarly; early_exit_code = $exitCode
    serialization_or_inflate_errors = $errorsFound; loaded_configs = @($loaded | Sort-Object)
    missing_required_configs = $missing; log_bytes = $log.Length
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $diagnosticFolder 'startup.json')
if (-not $passed) { throw "Startup check failed: $errorsFound serialization/inflate errors; missing configs: $($missing -join ', '). See $diagnosticFolder" }
Write-Output "Startup check passed: all seven required configs loaded, zero serialization/inflate errors. Logs: $diagnosticFolder"
