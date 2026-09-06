param([Parameter(Mandatory=$true)][string]$InstallRoot,[Parameter(Mandatory=$true)][string]$RollbackAnchor,[string]$RegistrationFile="$InstallRoot\registration.json",[string]$OperationLog="$InstallRoot\rollback-operation.json")
$Python = if ($env:MAFS_PYTHON) { $env:MAFS_PYTHON } else { "python" }
& $Python "$PSScriptRoot\..\lib\release_ops.py" rollback --install-root $InstallRoot --registration-file $RegistrationFile --rollback-anchor $RollbackAnchor --operation-log $OperationLog
exit $LASTEXITCODE
