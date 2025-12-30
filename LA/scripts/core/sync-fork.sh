
#!/usr/bin/env bash
# Sync a fork with its upstream repo (general-use, parameter-enforced).
# Works in Git Bash (Windows), WSL, Linux, macOS.

set -euo pipefail

# --- Argument parsing (required; no defaults) ---
UPSTREAM_URL=""
METHOD=""
DO_PUSH=""
SYNC_TAGS="false"   # Only toggled by --tags
FF_ONLY="false"     # Optional

usage() {
  cat <<'EOF'
Usage:
  sync-fork.sh --upstream URL --method merge|rebase --push true|false [--tags] [--ff-only true|false]

Required:
  --upstream URL          Upstream repository URL (e.g., https://github.com/owner/repo.git)
  --method merge|rebase   Sync strategy: 'merge' (safer) or 'rebase' (linear history)
  --push true|false       Push local updates to origin after sync

Optional:
  --tags                  Also fetch/push tags (mirrors upstream tags to your fork)
  --ff-only true|false    For 'merge': attempt fast-forward only first (default false)

Examples:
  sync-fork.sh --upstream https://github.com/balapriyac/python-basics.git --method merge --push true
  sync-fork.sh --upstream https://github.com/owner/repo.git --method rebase --push false --tags
  sync-fork.sh --upstream https://github.com/owner/repo.git --method merge --push true --ff-only true
EOF
}

# Parse flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --upstream) UPSTREAM_URL="${2:-}"; shift 2 ;;
    --method) METHOD="${2:-}"; shift 2 ;;
    --push) DO_PUSH="${2:-}"; shift 2 ;;
    --tags) SYNC_TAGS="true"; shift 1 ;;
    --ff-only) FF_ONLY="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

# Validate required args
err=""
[[ -z "$UPSTREAM_URL" ]] && err="--upstream is required"
[[ -z "$METHOD" ]] && err="${err:+$err; }--method is required"
[[ -z "$DO_PUSH" ]] && err="${err:+$err; }--push true|false is required"
if [[ -n "$err" ]]; then
  echo "Error: $err"
  usage
  exit 1
fi

# Validate METHOD
if [[ "$METHOD" != "merge" && "$METHOD" != "rebase" ]]; then
  echo "Error: --method must be 'merge' or 'rebase'"
  usage; exit 1
fi

# Validate DO_PUSH boolean
if [[ "$DO_PUSH" != "true" && "$DO_PUSH" != "false" ]]; then
  echo "Error: --push must be 'true' or 'false'"
  usage; exit 1
fi

# Validate FF_ONLY boolean if provided
if [[ "$FF_ONLY" != "true" && "$FF_ONLY" != "false" ]]; then
  echo "Error: --ff-only must be 'true' or 'false'"
  usage; exit 1
fi

# --- Guardrails ---
# Ensure we're inside a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: Not inside a Git repository."
  exit 1
fi

# Inform if detached HEAD
if ! git symbolic-ref -q HEAD >/dev/null 2>&1; then
  echo "Note: You are in a detached HEAD state. The script will check out the default branch."
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

# Ensure 'upstream' exists (add if missing; do not override silently)
if ! git remote get-url upstream >/dev/null 2>&1; then
  echo "Adding upstream: $UPSTREAM_URL"
  git remote add upstream "$UPSTREAM_URL"
else
  actual_upstream="$(git remote get-url upstream)"
  echo "Upstream already set: $actual_upstream"
  if [[ "$actual_upstream" != "$UPSTREAM_URL" ]]; then
    echo "Note: Provided --upstream differs from existing remote."
    echo "If you intend to change it, run: git remote set-url upstream \"$UPSTREAM_URL\""
  fi
fi

# Unshallow if needed
if [[ -f .git/shallow ]]; then
  echo "Detected shallow clone. Unshallowing..."
  git fetch --unshallow || git fetch --depth=100000
fi

# Fetch upstream (prune stale refs)
echo "Fetching from upstream..."
git fetch upstream --prune

# Optionally sync tags
if [[ "$SYNC_TAGS" == "true" ]]; then
  echo "Fetching tags from upstream..."
  git fetch upstream --tags
fi

# Determine default branch preferring upstream's HEAD, then origin
DEFAULT_BRANCH="$(
  git symbolic-ref -q refs/remotes/upstream/HEAD | sed 's@^refs/remotes/upstream/@@' || true
)"
if [[ -z "$DEFAULT_BRANCH" ]]; then
  DEFAULT_BRANCH="$(git symbolic-ref -q refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@' || true)"
fi
if [[ -z "$DEFAULT_BRANCH" ]]; then
  if git ls-remote --exit-code --heads upstream main >/dev/null 2>&1 || git ls-remote --exit-code --heads origin main >/dev/null 2>&1; then
    DEFAULT_BRANCH="main"
  elif git ls-remote --exit-code --heads upstream master >/dev/null 2>&1 || git ls-remote --exit-code --heads origin master >/dev/null 2>&1; then
    DEFAULT_BRANCH="master"
  else
    echo "Error: Could not determine default branch (main/master)."
    exit 1
  fi
fi
echo "Default branch detected: $DEFAULT_BRANCH"

# Checkout default branch
git checkout "$DEFAULT_BRANCH"

# Ensure local branch tracks origin
if ! git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
  echo "Setting upstream tracking to origin/$DEFAULT_BRANCH"
  git branch --set-upstream-to "origin/$DEFAULT_BRANCH" "$DEFAULT_BRANCH" || true
fi

# Fetch latest from origin (prune)
echo "Fetching latest from origin..."
git fetch origin --prune

# --- Sync operation ---
case "$METHOD" in
  merge)
    if [[ "$FF_ONLY" == "true" ]]; then
      echo "Attempting fast-forward merge from upstream/$DEFAULT_BRANCH..."
      if git merge --ff-only "upstream/$DEFAULT_BRANCH"; then
        echo "Fast-forward merge completed."
      else
        echo "Fast-forward not possible; performing a regular merge..."
        git merge --no-edit "upstream/$DEFAULT_BRANCH"
      fi
    else
      echo "Merging upstream/$DEFAULT_BRANCH into $DEFAULT_BRANCH..."
      git merge --no-edit "upstream/$DEFAULT_BRANCH"
    fi
    ;;
  rebase)
    echo "Rebasing $DEFAULT_BRANCH onto upstream/$DEFAULT_BRANCH..."
    set +e
    git rebase "upstream/$DEFAULT_BRANCH"
    status=$?
    set -e
    if [[ $status -ne 0 ]]; then
      echo "Rebase encountered conflicts. Resolve them, then run:"
      echo "  git rebase --continue    # when fixed"
      echo "  git rebase --abort       # to undo the rebase"
      exit $status
    fi
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
