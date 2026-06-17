param(
  [switch]$Seed,
  [switch]$Wipe
)

$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Push-Location $backendDir

try {
  $seedArg = @()
  if ($Seed) { $seedArg += "--seed" }
  if ($Wipe) { $seedArg += "--wipe" }
  python "scripts/db_upgrade.py" @seedArg
}
finally {
  Pop-Location
}

