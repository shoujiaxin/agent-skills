---
name: xcode-derived-data
description: Locate and delete Xcode Derived Data that belongs to a given git worktree, so leftover iOS/macOS build artifacts stop using disk. Use when finishing or removing an Xcode worktree, reclaiming disk after worktree development, or cleaning worktree-specific DerivedData. Triggers include "clean Derived Data", "worktree DerivedData", "Xcode cache", "释放磁盘", and /xcode-derived-data.
---

# Xcode Derived Data (worktree)

Delete only the Derived Data folders owned by one git worktree. Xcode keys each folder to a `WorkspacePath`; worktrees of the same project therefore get different folders, and those folders remain after `git worktree remove`.

## Hard rules

- Run `scripts/clean-worktree-derived-data.py`. Do not hand-delete.
- Never `rm -rf ~/Library/Developer/Xcode/DerivedData/<Project>-*`. That wipes every worktree of the project.
- Never delete `ModuleCache.noindex`, `SDKStatCaches.noindex`, `SymbolCache.noindex`, `CompilationCache.noindex`, or `SDKExplicitPrecompiledModules`.
- Never touch simulators, device support, or archives.

## Resolve the worktree

1. Absolute path from the user, even if the directory is already gone.
2. Else a named worktree from `git worktree list` or `<repo>/.worktrees/`.
3. Else the current git toplevel.

The path may no longer exist. That is normal after the worktree was removed.

## Command

Script path is next to this `SKILL.md`.

```bash
python3 "<skill-dir>/scripts/clean-worktree-derived-data.py" --dry-run "<worktree>"
python3 "<skill-dir>/scripts/clean-worktree-derived-data.py" "<worktree>"
```

Current worktree:

```bash
python3 "<skill-dir>/scripts/clean-worktree-derived-data.py" --dry-run
python3 "<skill-dir>/scripts/clean-worktree-derived-data.py"
```

Orphaned folders (WorkspacePath missing on disk):

```bash
python3 "<skill-dir>/scripts/clean-worktree-derived-data.py" --stale --dry-run
python3 "<skill-dir>/scripts/clean-worktree-derived-data.py" --stale
```

Always dry-run first. Delete only when the listed `WorkspacePath` values belong to the intended worktree. Then report each deleted folder and the bytes freed.

## How a folder is owned

Default root: `~/Library/Developer/Xcode/DerivedData`. Also honor `defaults read com.apple.dt.Xcode IDECustomDerivedDataLocation` when set.

Each `<Name>-<hash>/info.plist` has `WorkspacePath` (an `.xcworkspace`, `.xcodeproj`, or package dir). The folder belongs to worktree `T` when `T` is the longest prefix of `WorkspacePath` among:

- `T` itself
- `git worktree list`
- other Derived Data `WorkspacePath` containers under `.worktrees/`

So cleaning the main checkout does not delete `.worktrees/<name>` folders. Cleaning one worktree does not delete siblings.

Skip any directory with no `info.plist` / no `WorkspacePath`.

## Out of scope

Shared module/SDK caches, simulator data, `~/Library/Caches/org.swift.swiftpm`, and `xcuserdata` inside the repo.
