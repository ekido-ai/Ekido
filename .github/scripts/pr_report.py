"""Fails a pull request whose description is missing a report section, or leaves one empty.

Reads the PR body from the PR_BODY environment variable (never interpolated into a shell command) and the author
from PR_AUTHOR. Authors in EXEMPT skip the check: the project lead, whose PRs are reviewed differently, and bots.
"""

from __future__ import annotations

import os
import re
import sys

SECTIONS = ["What changed", "Tests", "Debugging notes", "Measurements", "AI review", "Screenshots"]
EXEMPT = {"piyushgargog", "dependabot[bot]", "github-actions[bot]"}
MIN_CHARS = 12  # Enough for "None: <reason>", too little for an empty-looking placeholder.
PLACEHOLDERS = {"none", "n/a", "na", "-", "todo", "tbd", "same", "."}


def sections(body: str) -> dict[str, str]:
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)  # Template hints don't count as content.
    found: dict[str, str] = {}
    parts = re.split(r"^##\s+(.+?)\s*$", body, flags=re.M)
    for title, text in zip(parts[1::2], parts[2::2]):
        found[title.strip().lower()] = text.strip()
    return found


def problems(body: str) -> list[str]:
    found = sections(body or "")
    result = []
    for name in SECTIONS:
        text = found.get(name.lower())
        if text is None:
            result.append(f"missing section '## {name}'")
        elif len(text) < MIN_CHARS or text.lower().strip(" .:") in PLACEHOLDERS:
            result.append(f"section '## {name}' is empty or a placeholder; write the real content, or 'None: <reason>'")
    return result


def main() -> int:
    author = os.environ.get("PR_AUTHOR", "")
    if author in EXEMPT:
        print(f"{author} is exempt from the report check")
        return 0
    found = problems(os.environ.get("PR_BODY", ""))
    for problem in found:
        print(f"::error::{problem}")
    if found:
        print("No report, no merge: fill in every section of the PR template (see the PR description).")
        return 1
    print("Report complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
