
REM Merge, push, no tags
sync-fork.bat --upstream https://github.com/owner/other-tutorial.git --method merge --push true

REM Rebase, no push
sync-fork.bat --upstream https://github.com/owner/other-tutorial.git --method rebase --push false

REM Merge with fast-forward-only, push
sync-fork.bat --upstream https://github.com/owner/other-tutorial.git --method merge --push true --ff-only true

REM Include tags
sync-fork.bat --upstream https://github.com/owner/other-tutorial.git --method merge --push true --tags
