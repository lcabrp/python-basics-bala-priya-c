
***

```markdown
# Syncing This Fork (python-basics-bala-priya-c)

This repository is a fork of the upstream tutorials at:

- Upstream: `https://github.com/balapriyac/python-basics.git`
- Fork:     `https://github.com/lcabrp/python-basics-bala-priya-c`

Use the **wrapper scripts** to keep your fork updated safely and consistently.  
Wrappers call the **generic, parameter-enforced core** scripts and pin the correct upstream for this repo.

---

## Folder layout

```

docs/
├─ merge-vs-rebase-doc.md
├─ merge-vs-rebase.png
└─ sync-fork-doc.md
scripts/
├─ core/
│  ├─ sync-fork.sh       # Bash core (requires parameters)
│  ├─ sync-fork.ps1      # PowerShell core (requires parameters)
│  └─ sync-fork.bat      # CMD core (requires parameters)
└─ wrappers/
├─ sync-python-basics.sh    # Bash wrapper for this repo
├─ Sync-PythonBasics.ps1    # PowerShell wrapper for this repo
└─ sync-python-basics.bat   # CMD wrapper for this repo

````

> If your scripts are currently in the repo root, you can **move** them into the folder structure above.  
> Update any paths in commands accordingly.

---

## Quick start

From the **repo root**:

### PowerShell (Windows)
```powershell
# Safer default for tutorials: merge + fast-forward when possible, and push
.\LA\scripts\wrappers\Sync-PythonBasics.ps1

# Clean, linear history (resolve conflicts if both changed same lines)
.\LA\scripts\wrappers\Sync-PythonBasics.ps1 rebase
````

> If execution policy blocks scripts:
>
> ```powershell
> PowerShell -ExecutionPolicy Bypass -File .\scripts\wrappers\Sync-PythonBasics.ps1
> ```

### CMD (Windows)

```cmd
REM Merge + push (fast-forward when possible)
scripts\wrappers\sync-python-basics.bat

REM Rebase + push
scripts\wrappers\sync-python-basics.bat rebase
```

### Bash (Git Bash / WSL / Linux / macOS)

```bash
# Merge + push (fast-forward when possible)
./LA/scripts/wrappers/sync-python-basics.sh

# Rebase + push
./LA/scripts/wrappers/sync-python-basics.sh rebase
```

***

## What the wrappers do

Wrappers pass these parameters to the **core**:

*   `--upstream` / `-UpstreamUrl`: `https://github.com/balapriyac/python-basics.git`
*   `--method` / `-Method`: `merge` (default in wrapper; `rebase` optional)
*   `--push` / `-Push`: `true` (pushes to your fork)
*   `--ff-only` / `-FastForwardOnly`: enabled (attempt fast-forward merges before regular merge)

They also:

*   **Prefer upstream** when detecting the default branch (`main`/`master`), then fall back to origin.
*   **Auto-unshallow** if the clone is shallow.
*   Give **clear guidance** if conflicts occur.

***

## Using the **core scripts** directly (for other forks)

Provide all parameters explicitly (no defaults baked in).

### PowerShell core

```powershell
.\LA\scripts\core\sync-fork.ps1 `
  -UpstreamUrl "https://github.com/OWNER/OTHER-REPO.git" `
  -Method merge `
  -Push $true `
  -FastForwardOnly
# Append -SyncTags if you want to mirror tags as well
```

### CMD core

```cmd
scripts\core\sync-fork.bat ^
  --upstream https://github.com/OWNER/OTHER-REPO.git ^
  --method merge ^
  --push true ^
  --ff-only true
REM Add --tags to mirror tags
```

### Bash core

```bash
./LA/scripts/core/sync-fork.sh \
  --upstream https://github.com/OWNER/OTHER-REPO.git \
  --method merge \
  --push true \
  --ff-only true
# Add --tags to mirror tags
```

***

## Verify after sync

```bash
git status
git log --oneline --graph --decorate -n 20
git remote -v

# Compare fork vs upstream
git fetch upstream
git log --oneline --graph origin/main upstream/main -n 30
```

***

## Merge vs Rebase (quick reference)

**Merge**

*   Creates a merge commit joining histories.
*   Safer and preserves your existing commits.
*   Slightly “busier” history.

**Rebase**

*   Moves your commits on top of upstream for a linear history.
*   Cleaner, but rewrites history and may require conflict resolution if both changed the same lines.

### Diagram

./docs/merge-vs-rebase.png "Merge vs Rebase"

For a deeper explanation, see `docs/merge-vs-rebase-doc.md`.

***

## Common issues & fixes

*   **Execution policy blocks PowerShell scripts**
    ```powershell
    PowerShell -ExecutionPolicy Bypass -File .\scripts\wrappers\Sync-PythonBasics.ps1
    ```

*   **Detached HEAD notice**  
    The scripts will automatically checkout the default branch (e.g., `main`) before syncing.

*   **Upstream mismatch**  
    If your existing `upstream` remote differs from the wrapper’s URL:
    ```bash
    git remote set-url upstream https://github.com/balapriyac/python-basics.git
    ```

*   **Shallow clone problems**  
    The core scripts auto‑unshallow. If needed:
    ```bash
    git fetch --unshallow
    ```

*   **Merge conflicts**
    1.  Fix the files (edit, then `git add` the resolved paths).
    2.  Complete merge:
        ```bash
        git commit
        ```
    3.  Abort if needed:
        ```bash
        git merge --abort
        ```

*   **Rebase conflicts**
    1.  Fix the files and `git add` the resolved paths.
    2.  Continue rebase:
        ```bash
        git rebase --continue
        ```
    3.  Abort if needed:
        ```bash
        git rebase --abort
        ```

***

## Optional niceties

*   **Git alias (PowerShell wrapper)**
    ```powershell
    git config --local alias.sync '!powershell -ExecutionPolicy Bypass -File ./scripts/wrappers/Sync-PythonBasics.ps1'
    ```
    Now you can run:
    ```powershell
    git sync
    ```

*   **Ignore local-only files**  
    If you prefer not to version scripts/docs, add to `.gitignore`:
    ```gitignore
    docs/
    scripts/
    ```

***

## Maintenance notes

*   **Core scripts** are **parameter-enforced** and reusable across any fork.
*   **Wrappers** are repo-specific: they pin the upstream and default behavior.
*   If you improve the core logic (e.g., conflict detection), wrappers benefit automatically.

***

**Last updated:** December 30, 2025 (EST)

````

---

### Next steps
- Create `docs/` and `scripts/` folders if you haven’t already, move files accordingly.
- Save the README above (e.g., as `docs/README.md`) and commit:
  ```powershell
  git add docs scripts
  git commit -m "Add sync workflow docs, scripts, and merge-vs-rebase diagram"
  git push origin main
````

If you want, I can tailor the README to your **exact current file names/paths** (e.g., if you’re sticking with root-level scripts for now).
