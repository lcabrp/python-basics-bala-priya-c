Awesome—let’s make this painless. Below are **two ready-to-use sync scripts**:

*   **Bash** (works in Git Bash on Windows, WSL, Linux, macOS)
*   **Windows** (**PowerShell** and **CMD** batch)

They’re designed to:

*   Add `upstream` if it doesn’t exist (defaults to the original repo you shared).
*   Detect your default branch (`main` or `master`).
*   Fetch from upstream.
*   Let you choose **merge** (safe) or **rebase** (clean history).
*   Push updates back to your fork.
*   Optionally sync tags.
*   Be idempotent (safe to run multiple times).

> **Assumptions for your repo:**
>
> *   Fork: `https://github.com/lcabrp/python-basics-bala-priya-c.git`
> *   Upstream: `https://github.com/balapriyac/python-basics.git`

You can change these via script arguments if needed.

***

## 1) Bash Script — `sync-fork.sh`

Save as `sync-fork.sh` in your repo root and run:  
`bash sync-fork.sh`  
or with options like:  
`bash sync-fork.sh --method rebase --tags --upstream https://github.com/balapriyac/python-basics.git`

```bash
#!/usr/bin/env bash
# Sync a fork with its upstream repo.
# Works in Git Bash (Windows), WSL, Linux, macOS.

set -euo pipefail

# Defaults (can be overridden via flags)
UPSTREAM_URL_DEFAULT="https://github.com/balapriyac/python-basics.git"
METHOD_DEFAULT="merge"    # "merge" or "rebase"
PUSH_DEFAULT="true"       # "true" or "false"
SYNC_TAGS_DEFAULT="false" # "true" or "false"

# Parse flags
UPSTREAM_URL="$UPSTREAM_URL_DEFAULT"
METHOD="$METHOD_DEFAULT"
DO_PUSH="$PUSH_DEFAULT"
SYNC_TAGS="$SYNC_TAGS_DEFAULT"

usage() {
  cat <<EOF
Usage: $0 [--upstream URL] [--method merge|rebase] [--push true|false] [--tags]
Examples:
  $0
  $0 --method rebase --tags
  $0 --upstream https://github.com/owner/repo.git --method merge --push false
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --upstream)
      UPSTREAM_URL="${2:-}"; shift 2 ;;
    --method)
      METHOD="${2:-}"; shift 2 ;;
    --push)
      DO_PUSH="${2:-}"; shift 2 ;;
    --tags)
      SYNC_TAGS="true"; shift 1 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

# Ensure we're inside a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: Not inside a Git repository."
  exit 1
fi

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Warning: You have uncommitted changes. Stash or commit before syncing."
  read -r -p "Continue anyway? [y/N] " ans
  [[ "${ans,,}" == "y" ]] || exit 1
fi

# Ensure 'origin' exists
if ! git remote get-url origin >/dev/null 2>&1; then
  echo "Error: 'origin' remote not found. Add it first: git remote add origin <your-fork-url>"
  exit 1
fi

# Ensure 'upstream' exists (add if missing)
if ! git remote get-url upstream >/dev/null 2>&1; then
  echo "Adding upstream: $UPSTREAM_URL"
  git remote add upstream "$UPSTREAM_URL"
else
  echo "Upstream already set: $(git remote get-url upstream)"
fi

# Detect default branch (main/master)
DEFAULT_BRANCH="$(git symbolic-ref -q refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@' || true)"
if [[ -z "$DEFAULT_BRANCH" ]]; then
  # Fallback: check if main exists, else master
  if git ls-remote --exit-code --heads origin main >/dev/null 2>&1; then
    DEFAULT_BRANCH="main"
  elif git ls-remote --exit-code --heads origin master >/dev/null 2>&1; then
    DEFAULT_BRANCH="master"
  else
    echo "Error: Could not determine default branch (main/master)."
    exit 1
  fi
fi
echo "Default branch detected: $DEFAULT_BRANCH"

# Fetch upstream
echo "Fetching from upstream..."
git fetch upstream --prune

# Optionally sync tags
if [[ "$SYNC_TAGS" == "true" ]]; then
  echo "Fetching tags from upstream..."
  git fetch upstream --tags
fi

# Checkout default branch
git checkout "$DEFAULT_BRANCH"

# Ensure local branch tracks origin
if ! git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
  echo "Setting upstream tracking to origin/$DEFAULT_BRANCH"
  git branch --set-upstream-to "origin/$DEFAULT_BRANCH" "$DEFAULT_BRANCH" || true
fi

# Update local default branch from origin (optional safety)
echo "Fetching latest from origin..."
git fetch origin --prune

# Merge or rebase from upstream/default
case "$METHOD" in
  merge)
    echo "Merging upstream/$DEFAULT_BRANCH into $DEFAULT_BRANCH..."
    git merge --no-edit "upstream/$DEFAULT_BRANCH"
    ;;
  rebase)
    echo "Rebasing $DEFAULT_BRANCH onto upstream/$DEFAULT_BRANCH..."
    git rebase "upstream/$DEFAULT_BRANCH"
    ;;
  *)
    echo "Invalid method: $METHOD (use 'merge' or 'rebase')"
    exit 1
    ;;
esac

# Push updates back to your fork
if [[ "$DO_PUSH" == "true" ]]; then
  echo "Pushing updates to origin/$DEFAULT_BRANCH..."
  git push origin "$DEFAULT_BRANCH"
  if [[ "$SYNC_TAGS" == "true" ]]; then
    echo "Pushing tags to origin..."
    git push origin --tags
  fi
else
  echo "Skipping push (per --push $DO_PUSH)."
fi

echo "✅ Sync complete."
```

**Quick tips:**

*   Run `chmod +x sync-fork.sh` once to make it executable.
*   Use `--method rebase` if you prefer a cleaner history.
*   Use `--tags` if you want tags mirrored to your fork.

***

## 2) Windows PowerShell Script — `Sync-Fork.ps1`

Run from PowerShell in your repo root:  
`.\Sync-Fork.ps1`  
or with options:  
`.\Sync-Fork.ps1 -UpstreamUrl https://github.com/balapriyac/python-basics.git -Method rebase -Push:$true -SyncTags:$true`

```powershell
<#
.SYNOPSIS
  Sync a fork with upstream (PowerShell).
.PARAMETER UpstreamUrl
  URL of upstream repo (defaults to the original repo).
.PARAMETER Method
  'merge' (default) or 'rebase'.
.PARAMETER Push
  Whether to push to origin after updating (default: $true).
.PARAMETER SyncTags
  Whether to sync tags from upstream (default: $false).
#>

param(
  [string]$UpstreamUrl = "https://github.com/balapriyac/python-basics.git",
  [ValidateSet("merge","rebase")] [string]$Method = "merge",
  [bool]$Push = $true,
  [bool]$SyncTags = $false
)

$ErrorActionPreference = "Stop"

function Ensure-GitRepo {
  try {
    git rev-parse --is-inside-work-tree | Out-Null
  } catch {
    throw "Not inside a Git repository."
  }
}

function Confirm-NoUncommitted {
  $hasChanges = $false
  try {
    git diff --quiet
  } catch { $hasChanges = $true }
  try {
    git diff --cached --quiet
  } catch { $hasChanges = $true }

  if ($hasChanges) {
    $ans = Read-Host "Warning: Uncommitted changes detected. Continue anyway? (y/N)"
    if ($ans.ToLower() -ne "y") { exit 1 }
  }
}

function Ensure-Remotes($UpstreamUrl) {
  try { git remote get-url origin | Out-Null }
  catch { throw "'origin' remote not found. Add it: git remote add origin <your-fork-url>" }

  try { $existing = git remote get-url upstream }
  catch {
    Write-Host "Adding upstream: $UpstreamUrl"
    git remote add upstream $UpstreamUrl | Out-Null
  }
}

function Get-DefaultBranch {
  $head = ""
  try {
    $ref = git symbolic-ref -q refs/remotes/origin/HEAD
    if ($LASTEXITCODE -eq 0) {
      $head = $ref -replace "^refs/remotes/origin/", ""
    }
  } catch {}

  if (-not $head) {
    $mainExists = git ls-remote --exit-code --heads origin main
    if ($LASTEXITCODE -eq 0) { return "main" }
    $masterExists = git ls-remote --exit-code --heads origin master
    if ($LASTEXITCODE -eq 0) { return "master" }
    throw "Could not determine default branch (main/master)."
  }
  return $head
}

Ensure-GitRepo
Confirm-NoUncommitted
Ensure-Remotes $UpstreamUrl
$defaultBranch = Get-DefaultBranch
Write-Host "Default branch detected: $defaultBranch"

Write-Host "Fetching from upstream..."
git fetch upstream --prune

if ($SyncTags) {
  Write-Host "Fetching tags from upstream..."
  git fetch upstream --tags
}

Write-Host "Checking out $defaultBranch..."
git checkout $defaultBranch

# Ensure tracking
try {
  git rev-parse --abbrev-ref --symbolic-full-name "@{u}" | Out-Null
} catch {
  Write-Host "Setting upstream tracking to origin/$defaultBranch"
  git branch --set-upstream-to "origin/$defaultBranch" $defaultBranch | Out-Null
}

Write-Host "Fetching latest from origin..."
git fetch origin --prune

switch ($Method) {
  "merge" {
    Write-Host "Merging upstream/$defaultBranch into $defaultBranch..."
    git merge --no-edit "upstream/$defaultBranch"
  }
  "rebase" {
    Write-Host "Rebasing $defaultBranch onto upstream/$defaultBranch..."
    git rebase "upstream/$defaultBranch"
  }
}

if ($Push) {
  Write-Host "Pushing updates to origin/$defaultBranch..."
  git push origin $defaultBranch
  if ($SyncTags) {
    Write-Host "Pushing tags to origin..."
    git push origin --tags
  }
} else {
  Write-Host "Skipping push (Push=$Push)."
}

Write-Host "✅ Sync complete."
```

***

## 3) Windows CMD Batch — `sync-fork.cmd`

Run from CMD in your repo root:  
`sync-fork.cmd`  
or with method:  
`sync-fork.cmd rebase`  
(Arguments: `%1` = `merge` or `rebase`; defaults to `merge`)

```batch
@echo off
REM Sync a fork with upstream (CMD batch). Minimal features.
REM Usage: sync-fork.cmd [merge|rebase]

SETLOCAL ENABLEDELAYEDEXPANSION

SET METHOD=%1
IF NOT DEFINED METHOD SET METHOD=merge

REM Ensure in git repo
git rev-parse --is-inside-work-tree >NUL 2>&1
IF ERRORLEVEL 1 (
  echo Error: Not inside a Git repository.
  EXIT /B 1
)

REM Check uncommitted changes (simplified)
git diff --quiet || SET HASCHANGES=1
git diff --cached --quiet || SET HASCHANGES=1
IF DEFINED HASCHANGES (
  set /p CONT=Warning: Uncommitted changes detected. Continue anyway? (y/N) 
  IF /I NOT "%CONT%"=="y" EXIT /B 1
)

REM Ensure origin exists
git remote get-url origin >NUL 2>&1
IF ERRORLEVEL 1 (
  echo Error: 'origin' remote not found. Add it: git remote add origin <your-fork-url>
  EXIT /B 1
)

REM Ensure upstream exists; add default if missing
git remote get-url upstream >NUL 2>&1
IF ERRORLEVEL 1 (
  echo Adding upstream: https://github.com/balapriyac/python-basics.git
  git remote add upstream https://github.com/balapriyac/python-basics.git
)

REM Detect default branch
FOR /F "usebackq tokens=*" %%A IN (`git symbolic-ref -q refs/remotes/origin/HEAD`) DO SET ORIGINHEAD=%%A
IF NOT DEFINED ORIGINHEAD (
  git ls-remote --exit-code --heads origin main >NUL 2>&1 && SET DEFAULTBRANCH=main
  IF NOT DEFINED DEFAULTBRANCH (
    git ls-remote --exit-code --heads origin master >NUL 2>&1 && SET DEFAULTBRANCH=master
  )
  IF NOT DEFINED DEFAULTBRANCH (
    echo Error: Could not determine default branch (main/master).
    EXIT /B 1
  )
) ELSE (
  SET DEFAULTBRANCH=%ORIGINHEAD:refs/remotes/origin/=%
)
echo Default branch detected: %DEFAULTBRANCH%

echo Fetching from upstream...
git fetch upstream --prune

echo Checking out %DEFAULTBRANCH%...
git checkout %DEFAULTBRANCH%

REM Try to set tracking (best effort)
git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >NUL 2>&1 || git branch --set-upstream-to origin/%DEFAULTBRANCH% %DEFAULTBRANCH% >NUL 2>&1

echo Fetching latest from origin...
git fetch origin --prune

IF /I "%METHOD%"=="rebase" (
  echo Rebasing %DEFAULTBRANCH% onto upstream/%DEFAULTBRANCH%...
  git rebase upstream/%DEFAULTBRANCH%
) ELSE (
  echo Merging upstream/%DEFAULTBRANCH% into %DEFAULTBRANCH%...
  git merge --no-edit upstream/%DEFAULTBRANCH%
)

echo Pushing updates to origin/%DEFAULTBRANCH%...
git push origin %DEFAULTBRANCH%

echo ✅ Sync complete.
ENDLOCAL
```

***

## How to use with your repositories

1.  **Place the script** in the root of your local clone of `lcabrp/python-basics-bala-priya-c`.
2.  Run it periodically to sync:
    *   Bash: `bash sync-fork.sh --method merge` (or `rebase`)
    *   PowerShell: `.\Sync-Fork.ps1 -Method merge`
    *   CMD: `sync-fork.cmd rebase`

> If the upstream remote isn’t set, the scripts will add:
> `https://github.com/balapriyac/python-basics.git` automatically.

***

## Optional enhancements (tell me if you want these added)

*   Sync **a specific branch** other than default (e.g., `--branch feature-x`).
*   Automatically **create tracking branches** for all upstream branches.
*   **Conflict-safe mode** that aborts on conflicts and prints next steps.
*   A **pre-check** for diverged histories and a summary of commits that will be applied.

If you’d like, I can tailor the scripts to your exact workflow—for example, always rebasing, syncing tags, or handling multiple tutorial branches.
