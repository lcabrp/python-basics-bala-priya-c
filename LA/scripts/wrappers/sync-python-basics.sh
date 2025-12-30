
#!/usr/bin/env bash
# Thin wrapper around the generic sync-fork.sh for this repo.
# Usage:
#   ./sync-python-basics.sh            # merge (default) - Typical safer sync for tutorials:
#   ./sync-python-basics.sh rebase     # rebase - Linear history (be ready to resolve conflicts if both changed same lines) 

set -euo pipefail

METHOD="${1:-merge}"  # merge or rebase
UPSTREAM_URL="https://github.com/balapriyac/python-basics.git"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/sync-fork.sh" \
  --upstream "$UPSTREAM_URL" \
  --method "$METHOD" \
  --push true \
  --ff-only true
  # Uncomment if you want tags mirrored too:
  # --tags

echo "✅ Sync (bash wrapper) complete."
