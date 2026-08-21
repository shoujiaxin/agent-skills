#!/usr/bin/env python3
"""Delete Xcode Derived Data owned by a git worktree.

Matching is by each folder's info.plist WorkspacePath, using the longest
git-worktree prefix. Never glob by project name (Karpo-*).
"""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path

SHARED_NAMES = {
    "CompilationCache.noindex",
    "ModuleCache.noindex",
    "SDKExplicitPrecompiledModules",
    "SDKStatCaches.noindex",
    "SymbolCache.noindex",
}

BROAD_TARGETS = {
    Path("/"),
    Path("/Users"),
    Path("/tmp"),
    Path("/private/tmp"),
    Path("/var"),
    Path("/private/var"),
}


def fail(message: str, code: int = 2) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def normalize(path: Path) -> Path:
    path = path.expanduser()
    if path.exists():
        return path.resolve()
    return Path(os.path.normpath(str(path.absolute())))


def first_existing_dir(path: Path) -> Path | None:
    current = normalize(path)
    if current.exists() and not current.is_dir():
        current = current.parent
    while True:
        if current.exists() and current.is_dir():
            return current
        if current.parent == current:
            return None
        current = current.parent


def git_output(cwd: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(cwd), *args],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def git_toplevel(cwd: Path) -> Path | None:
    raw = git_output(cwd, "rev-parse", "--show-toplevel")
    return Path(raw).resolve() if raw else None


def git_worktrees(cwd: Path) -> list[Path]:
    raw = git_output(cwd, "worktree", "list", "--porcelain")
    if not raw:
        return []
    paths: list[Path] = []
    for line in raw.splitlines():
        if line.startswith("worktree "):
            paths.append(normalize(Path(line[len("worktree ") :])))
    return paths


def is_inside_git(path: Path) -> bool:
    probe = path if path.exists() else first_existing_dir(path)
    if probe is None:
        return False
    return git_output(probe, "rev-parse", "--is-inside-work-tree") == "true"


def default_derived_data_root() -> Path:
    return Path.home() / "Library/Developer/Xcode/DerivedData"


def custom_derived_data_root() -> Path | None:
    try:
        raw = subprocess.check_output(
            ["defaults", "read", "com.apple.dt.Xcode", "IDECustomDerivedDataLocation"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_dir() else None


def derived_data_roots(override: Path | None) -> list[Path]:
    if override is not None:
        root = normalize(override)
        if not root.is_dir():
            fail(f"Derived Data root does not exist: {root}")
        return [root]
    roots: list[Path] = []
    custom = custom_derived_data_root()
    if custom is not None:
        roots.append(normalize(custom))
    default = default_derived_data_root()
    if default.is_dir() and default not in roots:
        roots.append(default)
    if not roots:
        fail(f"no Derived Data root found (looked at {default})")
    return roots


def too_broad(target: Path) -> bool:
    home = Path.home().resolve()
    broad = set(BROAD_TARGETS)
    broad.update(
        {
            home,
            home / "Developer",
            home / "Library",
            home / "Library/Developer",
            home / "Library/Developer/Xcode",
            home / "Library/Developer/Xcode/DerivedData",
        }
    )
    return target in broad or len(target.parts) <= 3


def resolve_target(raw: str | None) -> Path:
    if raw:
        path = Path(raw)
    else:
        cwd = Path.cwd()
        top = git_toplevel(cwd)
        path = top if top is not None else cwd
    target = normalize(path)
    if too_broad(target):
        fail(f"refusing broad path: {target}")
    if not is_inside_git(target):
        fail(f"not associated with a git worktree: {target}")
    if target.exists():
        top = git_toplevel(target)
        if top is not None:
            target = top
    return target


def workspace_container(workspace_path: Path) -> Path:
    name = workspace_path.name
    if (
        name.endswith(".xcworkspace")
        or name.endswith(".xcodeproj")
        or name == "Package.swift"
    ):
        return workspace_path.parent
    return workspace_path


def known_worktrees(target: Path, workspace_paths: list[Path]) -> list[Path]:
    prefixes = {target}
    probe = target if target.exists() else first_existing_dir(target)
    if probe is not None:
        prefixes.update(git_worktrees(probe))
    for workspace in workspace_paths:
        container = workspace_container(workspace)
        if container == target or ".worktrees" in container.parts:
            prefixes.add(normalize(container))
    return list(prefixes)


def longest_prefix(workspace_path: Path, prefixes: list[Path]) -> Path | None:
    workspace = str(normalize(workspace_path))
    matches = [
        prefix
        for prefix in prefixes
        if workspace == str(prefix) or workspace.startswith(str(prefix) + os.sep)
    ]
    if not matches:
        return None
    return max(matches, key=lambda prefix: len(str(prefix)))


def dir_bytes(path: Path) -> int:
    try:
        raw = subprocess.check_output(["du", "-sk", str(path)], text=True)
    except subprocess.CalledProcessError:
        return 0
    return int(raw.split()[0]) * 1024


def fmt_bytes(num: int) -> str:
    value = float(num)
    for unit in ("B", "K", "M", "G", "T"):
        if value < 1024 or unit == "T":
            if unit == "B":
                return f"{int(value)}B"
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{num}B"


def read_workspace_path(info_plist: Path) -> Path | None:
    try:
        with info_plist.open("rb") as handle:
            data = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException):
        return None
    raw = data.get("WorkspacePath")
    if not raw:
        return None
    return Path(str(raw))


def collect_entries(roots: list[Path]) -> list[tuple[Path, Path]]:
    entries: list[tuple[Path, Path]] = []
    for root in roots:
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name in SHARED_NAMES:
                continue
            workspace = read_workspace_path(child / "info.plist")
            if workspace is None:
                continue
            entries.append((child, workspace))
    return entries


def select_matches(
    entries: list[tuple[Path, Path]],
    target: Path | None,
    stale: bool,
) -> list[tuple[Path, Path]]:
    workspace_paths = [workspace for _, workspace in entries]
    if stale:
        return [
            (folder, workspace)
            for folder, workspace in entries
            if not workspace.exists()
        ]
    assert target is not None
    prefixes = known_worktrees(target, workspace_paths)
    matches: list[tuple[Path, Path]] = []
    for folder, workspace in entries:
        owner = longest_prefix(workspace, prefixes)
        if owner == target:
            matches.append((folder, workspace))
    return matches


def delete_folder(path: Path) -> None:
    result = subprocess.run(["rm", "-rf", str(path)], check=False)
    if result.returncode != 0 or path.exists():
        fail(f"failed to delete {path}", code=1)


def print_report(
    target: Path | None,
    roots: list[Path],
    matches: list[tuple[Path, Path, int]],
    stale: bool,
    dry_run: bool,
    freed: int | None,
) -> None:
    if stale:
        print("Mode: stale (WorkspacePath missing on disk)")
    else:
        print(f"Target: {target}")
    print("Derived Data roots:")
    for root in roots:
        print(f"  {root}")
    if not matches:
        print("Matches: 0")
        return
    print(f"Matches ({len(matches)}):")
    for folder, workspace, size in matches:
        exists = "missing" if not workspace.exists() else "present"
        print(f"  {fmt_bytes(size):>8}  {folder.name}")
        print(f"            WorkspacePath ({exists}): {workspace}")
    if dry_run:
        total = sum(size for _, _, size in matches)
        print(f"Dry run; would free {fmt_bytes(total)}")
        return
    if freed is not None:
        print(f"Freed: {fmt_bytes(freed)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete Xcode Derived Data owned by a git worktree"
    )
    parser.add_argument(
        "worktree",
        nargs="?",
        help="Worktree path (defaults to current git toplevel). May already be deleted.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List matches without deleting",
    )
    parser.add_argument(
        "--stale",
        action="store_true",
        help="Delete Derived Data whose WorkspacePath no longer exists",
    )
    parser.add_argument(
        "--derived-data-root",
        type=Path,
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stale and args.worktree:
        fail("pass either a worktree path or --stale, not both")
    roots = derived_data_roots(args.derived_data_root)
    entries = collect_entries(roots)
    target = None if args.stale else resolve_target(args.worktree)
    selected = select_matches(entries, target, stale=args.stale)
    sized = [(folder, workspace, dir_bytes(folder)) for folder, workspace in selected]
    if args.dry_run or not sized:
        print_report(target, roots, sized, args.stale, dry_run=args.dry_run, freed=None)
        return
    print_report(target, roots, sized, args.stale, dry_run=False, freed=None)
    freed = 0
    for folder, _, size in sized:
        print(f"Deleting {folder}")
        delete_folder(folder)
        freed += size
    print(f"Freed: {fmt_bytes(freed)}")


if __name__ == "__main__":
    main()
