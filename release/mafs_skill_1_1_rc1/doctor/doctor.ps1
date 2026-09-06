param([Parameter(Mandatory=$true)][string]$InstallPath,[ValidateSet('unknown','offline','online')][string]$ProviderNetworkStatus='unknown',[string]$OperationLog="$InstallPath\..\doctor-operation.json")
$Python = if ($env:MAFS_PYTHON) { $env:MAFS_PYTHON } else { "python" }
& $Python "$PSScriptRoot\..\lib\release_ops.py" doctor --install-path $InstallPath --provider-network-status $ProviderNetworkStatus --operation-log $OperationLog
exit $LASTEXITCODE
