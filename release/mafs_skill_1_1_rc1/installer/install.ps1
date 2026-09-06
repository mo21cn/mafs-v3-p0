param([Parameter(Mandatory=$true)][string]$InstallRoot,[string]$RegistrationFile="$InstallRoot\registration.json",[string]$OperationLog="$InstallRoot\install-operation.json")
$Python = if ($env:MAFS_PYTHON) { $env:MAFS_PYTHON } else { "python" }
& $Python "$PSScriptRoot\..\lib\release_ops.py" install --package-root "$PSScriptRoot\.." --install-root $InstallRoot --registration-file $RegistrationFile --operation-log $OperationLog
exit $LASTEXITCODE
