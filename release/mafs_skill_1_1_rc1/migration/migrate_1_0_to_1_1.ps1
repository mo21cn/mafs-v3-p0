param([Parameter(Mandatory=$true)][string]$LegacyRoot,[Parameter(Mandatory=$true)][string]$LegacyManifest,[Parameter(Mandatory=$true)][string]$InstallRoot,[string]$RegistrationFile="$InstallRoot\registration.json",[string]$RollbackAnchor="$InstallRoot\rollback-anchor.json",[string]$OperationLog="$InstallRoot\migration-operation.json")
$Python = if ($env:MAFS_PYTHON) { $env:MAFS_PYTHON } else { "python" }
& $Python "$PSScriptRoot\..\lib\release_ops.py" migrate --package-root "$PSScriptRoot\.." --legacy-root $LegacyRoot --legacy-manifest $LegacyManifest --install-root $InstallRoot --registration-file $RegistrationFile --rollback-anchor $RollbackAnchor --operation-log $OperationLog
exit $LASTEXITCODE
