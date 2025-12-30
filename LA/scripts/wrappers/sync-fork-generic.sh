
# Merge, push, no tags:
./sync-fork.sh --upstream https://github.com/owner/other-tutorial.git --method merge --push true

# Rebase, no push (just update locally):
./sync-fork.sh --upstream https://github.com/owner/other-tutorial.git --method rebase --push false

# Merge with fast-forward-only:
./sync-fork.sh --upstream https://github.com/owner/other-tutorial.git --method merge --push true --ff-only true
