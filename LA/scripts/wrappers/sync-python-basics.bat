
@echo off
REM Thin wrapper for the python-basics fork.
REM Calls the generic sync-fork.cmd with pinned upstream and preferred behavior.

SETLOCAL
SET "UPSTREAM_URL=https://github.com/balapriyac/python-basics.git"
SET "METHOD=%~1"
IF NOT DEFINED METHOD SET "METHOD=merge"

REM Safer default for tutorial workflow: merge + fast-forward when possible, and push.
CALL "%~dp0sync-fork.cmd" --upstream "%UPSTREAM_URL%" --method "%METHOD%" --push true --ff-only true
REM If you want to mirror tags as well, append: --tags

ECHO ✅ Sync (CMD wrapper) complete.
ENDLOCAL
