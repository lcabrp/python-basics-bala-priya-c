
<#
Thin wrapper for this repository. Calls the generic sync-fork.ps1 with the
correct upstream and defaults.

Usage:
  .\Sync-PythonBasics.ps1          # merge (default)
  .\Sync-PythonBasics.ps1 rebase   # rebase
#>

[CmdletBinding()]
param(
  [ValidateSet("merge","rebase")]
  [string]$Method = "merge"
)

$UpstreamUrl = "https://github.com/balapriyac/python-basics.git"
$Core = Join-Path $PSScriptRoot 'sync-fork.ps1'

# Safer default for tutorial workflow: merge + fast-forward when possible, and push.
& $Core -UpstreamUrl $UpstreamUrl -Method $Method -Push $true -FastForwardOnly

# If you want tags mirrored too, add: -SyncTags
Write-Host "✅ Sync (PowerShell wrapper) complete."
