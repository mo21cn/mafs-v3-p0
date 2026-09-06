param([Parameter(Mandatory=$true)][string]$InstallPath,[string]$OperationLog="$InstallPath\..\verify-operation.json")
$Python = if ($env:MAFS_PYTHON) { $env:MAFS_PYTHON } else { "python" }
& $Python "$PSScriptRoot\..\lib\release_ops.py" verify-package --package-root $InstallPath --operation-log $OperationLog
exit $LASTEXITCODE
