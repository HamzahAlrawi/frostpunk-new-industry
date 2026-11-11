param([ValidateSet('install','uninstall','status')][string]$Action = 'install')
$ErrorActionPreference = 'Stop'
try {
    $binary = Join-Path $PSScriptRoot 'Frostpunk-New-Industry.exe'
    $arguments = @($Action, '--pause')
    if (!(Test-Path -LiteralPath $binary)) {
        $python = Get-Command py -ErrorAction SilentlyContinue
        if ($python) {
            $binary = $python.Source
            $arguments = @('-3', (Join-Path $PSScriptRoot 'installer.py')) + $arguments
        } else {
            $python = Get-Command python -ErrorAction SilentlyContinue
            if (!$python) { throw 'Install Python 3.9 or later, or download the release ZIP that includes Frostpunk-New-Industry.exe.' }
            $binary = $python.Source
            $arguments = @((Join-Path $PSScriptRoot 'installer.py')) + $arguments
        }
    }
    $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if ($Action -ne 'status' -and !$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        $quoted = @($arguments | ForEach-Object { '"' + $_.Replace('"', '\"') + '"' })
        $child = Start-Process -FilePath $binary -ArgumentList $quoted -Verb RunAs -Wait -PassThru
        exit $child.ExitCode
    }
    & $binary @arguments
    exit $LASTEXITCODE
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}
