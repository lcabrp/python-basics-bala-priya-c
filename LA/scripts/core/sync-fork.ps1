
<#
.SYNOPSIS
  Sync a fork's default branch with its upstream default branch (general-use, parameter-enforced).

.DESCRIPTION
  - Requires explicit parameters (no baked-in defaults).
  - Prefers upstream for default-branch detection; falls back to origin.
  - Unshallows shallow clones automatically.
  - Supports fast-forward-only merges when requested.
  - Gives clear guidance if a rebase hits conflicts.

.PARAMETER UpstreamUrl
  REQUIRED. The upstream repository URL (e.g., https://github.com/owner/repo.git).

.PARAMETER Method
  REQUIRED. 'merge' (safer) or 'rebase' (linear, rewrites local history).

.PARAMETER Push
  REQUIRED. $true to push updates to origin after syncing; $false to keep local only.

.PARAMETER SyncTags
  OPTIONAL. If present, fetch/push tags (mirrors upstream tags to your fork).

.PARAMETER FastForwardOnly
  OPTIONAL. For 'merge': try a fast-forward-only merge first; if not possible, perform a normal merge.

.EXAMPLES
  PS> .\sync-fork.ps1 -UpstreamUrl https://github.com/balapriyac/python-basics.git -Method merge -Push $true
  PS> .\sync-fork.ps1 -UpstreamUrl https://github.com/owner/other-tutorial.git -Method rebase -Push $false
  PS> .\sync-fork.ps1 -UpstreamUrl https://github.com/owner/other-tutorial.git -Method merge -Push $true -FastForwardOnly

.NOTES
  Run from the repository root. If execution policy blocks the script:
    PowerShell -ExecutionPolicy Bypass -File .\sync-fork.ps1 ...
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$UpstreamUrl,

  [Parameter(Mandatory = $true)]
  [ValidateSet("merge","rebase")]
  [string]$Method,

  [Parameter(Mandatory = $true)]
  [bool]$Push,

  [switch]$SyncTags,
  [switch]$FastForwardOnly
)

$ErrorActionPreference = "Stop"

function Ensure-GitRepo {
  try {
    git rev-parse --is-inside-work-tree | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Not inside a Git repository." }
  } catch { throw "Not inside a Git repository." }
}

function Confirm-NoUncommitted {
  $hasChanges = $false
  try { git diff --quiet } catch { $hasChanges = $true }
  try { git diff --cached --quiet } catch { $hasChanges = $true }

  if ($hasChanges) {
    $ans = Read-Host "Warning: Uncommitted changes detected. Continue anyway? (y/N)"
    if ($ans.ToLower() -ne "y") { exit 1 }
  }
}

function Ensure-Remotes {
  # origin must exist
  try { git remote get-url origin | Out-Null }
  catch { throw "'origin' remote not found. Add it: git remote add origin <your-fork-url>" }

  # upstream add if missing
  try {
    $existing = git remote get-url upstream
    if ($LASTEXITCODE -eq 0) {
      Write-Host "Upstream already set: $existing"
      if ($existing -ne $UpstreamUrl) {
        Write-Host "Note: Provided -UpstreamUrl differs from existing upstream remote."
        Write-Host "      To change it: git remote set-url upstream $UpstreamUrl"
      }
    }
  } catch {
    Write-Host "Adding upstream: $UpstreamUrl"
    git remote add upstream $UpstreamUrl | Out-Null
  }
}

function Unshallow-IfNeeded {
  $shallowPath = Join-Path (git rev-parse --git-dir).Trim() "shallow"
  if (Test-Path $shallowPath) {
    Write-Host "Detected shallow clone. Unshallowing..."
    git fetch --unshallow
    if ($LASTEXITCODE -ne 0) {
      Write-Host "Fallback: deepening history..."
      git fetch --depth=100000
    }
  }
}

function Get-DefaultBranch {
  # Prefer upstream's HEAD
  $upRef = ""
  try {
    $upRef = git symbolic-ref -q refs/remotes/upstream/HEAD
    if ($LASTEXITCODE -eq 0) {
      $branch = $upRef -replace "^refs/remotes/upstream/", ""
      if ($branch) { return $branch }
    }
  } catch {}

  # Fallback: origin's HEAD
  $origRef = ""
  try {
    $origRef = git symbolic-ref -q refs/remotes/origin/HEAD
    if ($LASTEXITCODE -eq 0) {
      $branch = $origRef -replace "^refs/remotes/origin/", ""
      if ($branch) { return $branch }
    }
  } catch {}

  # Final fallback: check common names on upstream first, then origin
  git ls-remote --exit-code --heads upstream main | Out-Null
  if ($LASTEXITCODE -eq 0) { return "main" }
  git ls-remote --exit-code --heads origin main | Out-Null
  if ($LASTEXITCODE -eq 0) { return "main" }
  git ls-remote --exit-code --heads upstream master | Out-Null
  if ($LASTEXITCODE -eq 0) { return "master" }
  git ls-remote --exit-code --heads origin master | Out-Null
  if ($LASTEXITCODE -eq 0) { return "master" }

  throw "Could not determine default branch (main/master)."
}

function Ensure-Tracking($branch) {
  try {
    git rev-parse --abbrev-ref --symbolic-full-name "@{u}" | Out-Null
    if ($LASTEXITCODE -ne 0) {
      throw "no-upstream"
    }
  } catch {
    Write-Host "Setting upstream tracking to origin/$branch"
    git branch --set-upstream-to "origin/$branch" $branch | Out-Null
  }
}

# --- Run ---
Ensure-GitRepo
# If detached HEAD, inform
try { git symbolic-ref -q HEAD | Out-Null } catch { Write-Host "Note: Detached HEAD detected; will check out default branch." }
Confirm-NoUncommitted
Ensure-Remotes
Unshallow-IfNeeded

Write-Host "Fetching from upstream..."
git fetch upstream --prune
if ($SyncTags) {
  Write-Host "Fetching tags from upstream..."
  git fetch upstream --tags
}

$defaultBranch = Get-DefaultBranch
Write-Host "Default branch detected: $defaultBranch"

Write-Host "Checking out $defaultBranch..."
git checkout $defaultBranch

Ensure-Tracking $defaultBranch

Write-Host "Fetching latest from origin..."
git fetch origin --prune

switch ($Method) {
  "merge" {
    if ($FastForwardOnly) {
      Write-Host "Attempting fast-forward merge from upstream/$defaultBranch..."
      git merge --ff-only "upstream/$defaultBranch"
      if ($LASTEXITCODE -ne 0) {
        Write-Host "Fast-forward not possible; performing a regular merge..."
        git merge --no-edit "upstream/$defaultBranch"
        if ($LASTEXITCODE -ne 0) {
          throw "Merge failed. Resolve conflicts, then commit the merge or abort with 'git merge --abort'."
        }
      }
    } else {
      Write-Host "Merging upstream/$defaultBranch into $defaultBranch..."
      git merge --no-edit "upstream/$defaultBranch"
      if ($LASTEXITCODE -ne 0) {
        throw "Merge failed. Resolve conflicts, then commit the merge or abort with 'git merge --abort'."
      }
    }
  }
  "rebase" {
    Write-Host "Rebasing $defaultBranch onto upstream/$defaultBranch..."
    git rebase "upstream/$defaultBranch"
    if ($LASTEXITCODE -ne 0) {
      Write-Host "Rebase encountered conflicts."
      Write-Host "Fix conflicts, then:"
      Write-Host "  git rebase --continue    # continue after resolving"
      Write-Host "  git rebase --abort       # abort the rebase"
      exit 1
    }
  }
}

if ($Push) {
  Write-Host "Pushing updates to origin/$defaultBranch..."
  git push origin $defaultBranch
  if ($LASTEXITCODE -ne 0) { throw "Push failed." }

  if ($SyncTags) {
    Write-Host "Pushing tags to origin..."
    git push origin --tags
    if ($LASTEXITCODE -ne 0) { throw "Pushing tags failed." }
  }
} else {
  Write-Host "Skipping push (-Push = $Push)."
}

Write-Host "✅ Sync complete."
