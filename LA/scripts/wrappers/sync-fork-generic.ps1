
# Merge, push
.\sync-fork.ps1 -UpstreamUrl https://github.com/owner/other-tutorial.git -Method merge -Push $true -FastForwardOnly

# Rebase, no push (inspect locally first)
.\sync-fork.ps1 -UpstreamUrl https://github.com/owner/other-tutorial.git -Method rebase -Push $false
