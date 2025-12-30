
@echo off
REM ============================================================================
REM Sync a fork's default branch with its upstream default branch (general-use).
REM Parameter-enforced: requires --upstream, --method, --push
REM Optional: --tags, --ff-only, --help
REM Works in Windows CMD.
REM ============================================================================

SETLOCAL ENABLEDELAYEDEXPANSION

REM ----------------------
REM Parse arguments
REM ----------------------
SET "UPSTREAM_URL="
SET "METHOD="
SET "DO_PUSH="
SET "SYNC_TAGS=false"
SET "FF_ONLY=false"

:parse
IF "%~1"=="" GOTO validate
IF /I "%~1"=="--help" GOTO usage
IF /I "%~1"=="-h" GOTO usage
IF /I "%~1"=="--upstream" (
  SET "UPSTREAM_URL=%~2"
  SHIFT
  SHIFT
  GOTO parse
)
IF /I "%~1"=="--method" (
  SET "METHOD=%~2"
  SHIFT
  SHIFT
  GOTO parse
)
IF /I "%~1"=="--push" (
  SET "DO_PUSH=%~2"
  SHIFT
  SHIFT
  GOTO parse
)
IF /I "%~1"=="--tags" (
  SET "SYNC_TAGS=true"
  SHIFT
  GOTO parse
)
IF /I "%~1"=="--ff-only" (
  SET "FF_ONLY=%~2"
  SHIFT
  SHIFT
  GOTO parse
)

ECHO Unknown argument: %~1
GOTO usage

:usage
ECHO.
ECHO Usage:
ECHO   sync-fork.cmd --upstream URL --method merge^|rebase --push true^|false [--tags] [--ff-only true^|false]
ECHO.
ECHO Required:
ECHO   --upstream URL          Upstream repository URL (e.g., https://github.com/owner/repo.git)
ECHO   --method merge^|rebase   Sync strategy: 'merge' (safer) or 'rebase' (linear history)
ECHO   --push true^|false       Push local updates to origin after sync
ECHO Optional:
ECHO   --tags                  Also fetch/push tags
ECHO   --ff-only true^|false    For 'merge': attempt fast-forward only first
ECHO.
ECHO Examples:
ECHO   sync-fork.cmd --upstream https://github.com/balapriyac/python-basics.git --method merge --push true
ECHO   sync-fork.cmd --upstream https://github.com/owner/other-tutorial.git --method rebase --push false --tags
ECHO   sync-fork.cmd --upstream https://github.com/owner/other-tutorial.git --method merge --push true --ff-only true
ECHO.
EXIT /B 1

:validate
IF NOT DEFINED UPSTREAM_URL (
  ECHO Error: --upstream is required
  GOTO usage
)
IF /I NOT "%METHOD%"=="merge" IF /I NOT "%METHOD%"=="rebase" (
  ECHO Error: --method must be 'merge' or 'rebase'
  GOTO usage
)
IF /I NOT "%DO_PUSH%"=="true" IF /I NOT "%DO_PUSH%"=="false" (
  ECHO Error: --push must be 'true' or 'false'
  GOTO usage
)
IF /I NOT "%FF_ONLY%"=="true" IF /I NOT "%FF_ONLY%"=="false" (
  ECHO Error: --ff-only must be 'true' or 'false'
  GOTO usage
)

REM ----------------------
REM Guardrails
REM ----------------------
git rev-parse --is-inside-work-tree >NUL 2>&1
IF ERRORLEVEL 1 (
  ECHO Error: Not inside a Git repository.
  EXIT /B 1
)

REM Inform if detached HEAD (symbolic-ref fails)
git symbolic-ref -q HEAD >NUL 2>&1
IF ERRORLEVEL 1 (
  ECHO Note: Detached HEAD detected; will check out the default branch.
)

REM Check for uncommitted changes
SET "HASCHANGES="
git diff --quiet || SET "HASCHANGES=1"
git diff --cached --quiet || SET "HASCHANGES=1"
IF DEFINED HASCHANGES (
  SET "CONT="
  SET /P CONT=Warning: Uncommitted changes detected. Continue anyway? (y/N) 
  IF /I NOT "!CONT!"=="y" EXIT /B 1
)

REM Ensure 'origin' exists
git remote get-url origin >NUL 2>&1
IF ERRORLEVEL 1 (
  ECHO Error: 'origin' remote not found. Add it first: git remote add origin ^<your-fork-url^>
  EXIT /B 1
)

REM Ensure 'upstream' exists (add if missing; do not override silently)
FOR /F "usebackq tokens=*" %%A IN (`git remote get-url upstream 2^>NUL`) DO SET "EXISTING_UP=%%A"
IF NOT DEFINED EXISTING_UP (
  ECHO Adding upstream: %UPSTREAM_URL%
  git remote add upstream "%UPSTREAM_URL%"
) ELSE (
  ECHO Upstream already set: !EXISTING_UP!
  IF /I NOT "!EXISTING_UP!"=="%UPSTREAM_URL%" (
    ECHO Note: Provided --upstream differs from existing upstream remote.
    ECHO       To change it: git remote set-url upstream "%UPSTREAM_URL%"
  )
)

REM Unshallow if needed
IF EXIST ".git\shallow" (
  ECHO Detected shallow clone. Unshallowing...
  git fetch --unshallow
  IF ERRORLEVEL 1 (
    ECHO Fallback: deepening history...
    git fetch --depth=100000
  )
)

REM Fetch upstream (prune stale refs)
ECHO Fetching from upstream...
git fetch upstream --prune
IF /I "%SYNC_TAGS%"=="true" (
  ECHO Fetching tags from upstream...
  git fetch upstream --tags
)

REM ----------------------
REM Determine default branch preferring upstream HEAD
REM ----------------------
SET "DEFAULTBRANCH="
FOR /F "usebackq tokens=*" %%A IN (`git symbolic-ref -q refs/remotes/upstream/HEAD 2^>NUL`) DO SET "UPREF=%%A"
IF DEFINED UPREF (
  SET "DEFAULTBRANCH=!UPREF:refs/remotes/upstream/=!"
)

IF NOT DEFINED DEFAULTBRANCH (
  FOR /F "usebackq tokens=*" %%A IN (`git symbolic-ref -q refs/remotes/origin/HEAD 2^>NUL`) DO SET "ORIGREF=%%A"
  IF DEFINED ORIGREF SET "DEFAULTBRANCH=!ORIGREF:refs/remotes/origin/=!"
)

IF NOT DEFINED DEFAULTBRANCH (
  git ls-remote --exit-code --heads upstream main >NUL 2>&1 && SET "DEFAULTBRANCH=main"
)
IF NOT DEFINED DEFAULTBRANCH (
  git ls-remote --exit-code --heads origin main >NUL 2>&1 && SET "DEFAULTBRANCH=main"
)
IF NOT DEFINED DEFAULTBRANCH (
  git ls-remote --exit-code --heads upstream master >NUL 2>&1 && SET "DEFAULTBRANCH=master"
)
IF NOT DEFINED DEFAULTBRANCH (
  git ls-remote --exit-code --heads origin master >NUL 2>&1 && SET "DEFAULTBRANCH=master"
)
IF NOT DEFINED DEFAULTBRANCH (
  ECHO Error: Could not determine default branch (main/master).
  EXIT /B 1
)
ECHO Default branch detected: %DEFAULTBRANCH%

REM Checkout default branch
ECHO Checking out %DEFAULTBRANCH%...
git checkout "%DEFAULTBRANCH%"

REM Ensure local branch tracks origin
git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >NUL 2>&1 || git branch --set-upstream-to "origin/%DEFAULTBRANCH%" "%DEFAULTBRANCH%" >NUL 2>&1

REM Fetch latest from origin
ECHO Fetching latest from origin...
git fetch origin --prune

REM ----------------------
REM Sync operation (merge or rebase)
REM ----------------------
IF /I "%METHOD%"=="merge" (
  IF /I "%FF_ONLY%"=="true" (
    ECHO Attempting fast-forward merge from upstream/%DEFAULTBRANCH%...
    git merge --ff-only "upstream/%DEFAULTBRANCH%"
    IF ERRORLEVEL 1 (
      ECHO Fast-forward not possible; performing a regular merge...
      git merge --no-edit "upstream/%DEFAULTBRANCH%"
      IF ERRORLEVEL 1 (
        ECHO Merge failed. Resolve conflicts, then commit the merge or abort with: git merge --abort
        EXIT /B 1
      )
    )
  ) ELSE (
    ECHO Merging upstream/%DEFAULTBRANCH% into %DEFAULTBRANCH%...
    git merge --no-edit "upstream/%DEFAULTBRANCH%"
    IF ERRORLEVEL 1 (
      ECHO Merge failed. Resolve conflicts, then commit the merge or abort with: git merge --abort
      EXIT /B 1
    )
  )
) ELSE (
  ECHO Rebasing %DEFAULTBRANCH% onto upstream/%DEFAULTBRANCH%...
  git rebase "upstream/%DEFAULTBRANCH%"
  IF ERRORLEVEL 1 (
    ECHO Rebase encountered conflicts.
    ECHO Fix conflicts, then:
    ECHO   git rebase --continue
    ECHO Or abort:
    ECHO   git rebase --abort
    EXIT /B 1
  )
)

REM ----------------------
REM Push if requested
REM ----------------------
IF /I "%DO_PUSH%"=="true" (
  ECHO Pushing updates to origin/%DEFAULTBRANCH%...
  git push origin "%DEFAULTBRANCH%"
  IF ERRORLEVEL 1 (
    ECHO Push failed.
    EXIT /B 1
  )
  IF /I "%SYNC_TAGS%"=="true" (
    ECHO Pushing tags to origin...
    git push origin --tags
    IF ERRORLEVEL 1 (
      ECHO Pushing tags failed.
      EXIT /B 1
    )
  )
) ELSE (
  ECHO Skipping push (per --push %DO_PUSH%).
)

ECHO ✅ Sync complete.
ENDLOCAL
EXIT /B 0
