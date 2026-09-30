#!/usr/bin/env python3
"""Prioritize mutmut survivors by file and filter low-value paths.

Run after `mutmut run`. Parses `mutmut results` output, groups surviving mutants
by source file, applies exclusion globs, and prints a ranked list of files with
the most survivors. Pipes survivor IDs to stdout for downstream `mutmut show`.

Usage:
    python prioritize_survivors.py
    python prioritize_survivors.py --exclude "**/spark/**" --exclude "**/logging.py"
    python prioritize_survivors.py --top 10 --show-diffs
    python prioritize_survivors.py --exclude-from .mutmut-ignore
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

SURVIVED_HEADER = re.compile(r"^Survived\s+\(", re.IGNORECASE)
KILLED_HEADER = re.compile(r"^(Killed|Timeout|Suspicious|Skipped|No tests)\b", re.IGNORECASE)
MUTANT_LINE = re.compile(r"^\s*([^\s,]+(?:\.py)?)[\s,]+(?:line\s+)?(\d+)?")
ID_LINE = re.compile(r"^\s*([\w./\-]+\.py)[:\s]+(\d+)\s*$")


def run_mutmut_results() -> str:
    """Invoke `mutmut results` and return stdout."""
    try:
        proc = subprocess.run(
            ["mutmut", "results"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        sys.exit("error: mutmut not found on PATH. install with `pip install mutmut`.")
    if proc.returncode != 0 and not proc.stdout:
        sys.exit(f"error: `mutmut results` failed:\n{proc.stderr}")
    return proc.stdout


def parse_survivors(output: str) -> list[str]:
    """Extract survivor mutant identifiers from `mutmut results` output.

    mutmut output format varies across versions. We accept either:
      - One id per line under a `Survived (...)` header
      - Comma-separated ids on a single line after the header
    """
    survivors: list[str] = []
    in_survived = False
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        if SURVIVED_HEADER.match(line):
            in_survived = True
            continue
        if KILLED_HEADER.match(line):
            in_survived = False
            continue
        if in_survived:
            # split on commas + whitespace for compact format, else one per line
            parts = [p.strip() for p in re.split(r"[,\s]+", line) if p.strip()]
            survivors.extend(parts)
    return survivors


def show_mutant(mutant_id: str) -> str:
    """Run `mutmut show <id>` to fetch the diff for one mutant."""
    proc = subprocess.run(
        ["mutmut", "show", mutant_id],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout


def file_for_mutant(mutant_id: str) -> str | None:
    """Resolve a mutant id to its source file path.

    mutmut ids encode the file in different formats depending on version:
      - `path/to/file.py:42` (newer)
      - numeric ids (older — fall back to parsing `mutmut show`)
    """
    if ":" in mutant_id and mutant_id.split(":", 1)[0].endswith(".py"):
        return mutant_id.split(":", 1)[0]
    # fallback: parse `mutmut show` header
    out = show_mutant(mutant_id)
    for line in out.splitlines():
        m = re.match(r"^---\s+(\S+\.py)", line)
        if m:
            return m.group(1)
    return None


def load_excludes(args_excludes: list[str], exclude_from: Path | None) -> list[str]:
    """Combine --exclude flags with patterns from --exclude-from file."""
    patterns = list(args_excludes)
    if exclude_from and exclude_from.exists():
        for line in exclude_from.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def is_excluded(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--exclude", action="append", default=[], help="glob pattern to exclude (repeatable)"
    )
    ap.add_argument("--exclude-from", type=Path, help="file with one glob pattern per line")
    ap.add_argument("--top", type=int, default=20, help="show top N files by survivor count")
    ap.add_argument(
        "--show-diffs", action="store_true", help="print `mutmut show` diff for each survivor"
    )
    ap.add_argument("--ids-only", action="store_true", help="print survivor ids only (for piping)")
    args = ap.parse_args()

    excludes = load_excludes(args.exclude, args.exclude_from)
    raw = run_mutmut_results()
    survivors = parse_survivors(raw)

    if not survivors:
        print("no survivors found (or output format unrecognized). raw results:")
        print(raw)
        return 0

    by_file: dict[str, list[str]] = defaultdict(list)
    unresolved: list[str] = []
    for mid in survivors:
        path = file_for_mutant(mid)
        if path is None:
            unresolved.append(mid)
            continue
        if is_excluded(path, excludes):
            continue
        by_file[path].append(mid)

    if args.ids_only:
        for ids in by_file.values():
            for mid in ids:
                print(mid)
        return 0

    ranked = sorted(by_file.items(), key=lambda kv: len(kv[1]), reverse=True)
    total = sum(len(ids) for _, ids in ranked)
    print(f"\nSurvivors after exclusions: {total} across {len(ranked)} files")
    print(f"Excluded patterns: {excludes or '(none)'}\n")

    for path, ids in ranked[: args.top]:
        print(f"  {len(ids):4d}  {path}")
        if args.show_diffs:
            for mid in ids:
                print(f"\n--- mutant {mid} ---")
                print(show_mutant(mid))

    if unresolved:
        print(f"\nUnresolved ids (could not map to file): {len(unresolved)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
