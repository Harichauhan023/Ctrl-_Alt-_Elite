"""
Comprehensive cleanup + bug scan for geoready-ai.
1. Removes emoji lines (outside docstrings)
2. Strips decorative separator comments (# -----, # ====, etc.)
3. Reports files changed and lines removed
Run: py scan_and_clean.py
"""
import pathlib
import re
import sys

EMOJI = re.compile(
    r"[\U0001F300-\U0001FAFF"
    r"\u2600-\u26FF"
    r"\u2700-\u27BF"
    r"\u00AE\u00A9\u203C\u2049\u20E3\u2122\u2139"
    r"\u2194-\u2199\u21A9-\u21AA\u231A-\u231B\u23E9-\u23F3"
    r"\u24C2\u25AA-\u25AB\u25B6\u25C0\u25FB-\u25FE"
    r"\u260E\u2611\u2614-\u2615\u2648-\u2653\u267F"
    r"\u2702\u2705\u2708-\u270D\u270F\u2712\u2714\u2716\u2728"
    r"\u2733-\u2734\u2744\u2747\u274C\u274E\u2753-\u2755\u2757\u2764"
    r"\u2795-\u2797\u27A1\u27B0\u2934-\u2935\u2B05-\u2B07"
    r"\u2B1B-\u2B1C\u2B50\u2B55\u3030\u303D\u3297\u3299"
    r"]"
)

DECO_SEP = re.compile(r"^\s*#\s*[─\-=]{3,}\s*$")


def is_docstring_toggle(stripped: str) -> bool:
    """Return True if this line opens/closes a triple-quote block."""
    return stripped.startswith('"""') or stripped.startswith("'''")


def clean_file(path: pathlib.Path) -> tuple[int, list[str]]:
    """Return (removed_count, new_lines)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  [SKIP] {path}: {e}")
        return 0, None

    lines = text.splitlines(keepends=True)
    new_lines = []
    in_doc = False
    removed = 0

    for line in lines:
        stripped = line.strip()

        # Track docstring state (simple but works for well-formed code)
        if is_docstring_toggle(stripped):
            # Count occurrences to detect single-line triple-quote strings
            dq = stripped.count('"""')
            sq = stripped.count("'''")
            if dq % 2 == 1:   # odd → toggles state
                in_doc = not in_doc
            elif sq % 2 == 1:
                in_doc = not in_doc
            new_lines.append(line)
            continue

        if in_doc:
            new_lines.append(line)
            continue

        # Outside docstrings: apply filters
        if EMOJI.search(line):
            removed += 1
            continue
        if DECO_SEP.match(line):
            removed += 1
            continue

        new_lines.append(line)

    return removed, new_lines


def main():
    root = pathlib.Path(__file__).resolve().parent
    total_removed = 0
    changed_files = []

    for py_file in sorted(root.rglob("*.py")):
        if py_file == pathlib.Path(__file__).resolve():
            continue

        removed, new_lines = clean_file(py_file)
        if new_lines is None:
            continue
        if removed > 0:
            py_file.write_text("".join(new_lines), encoding="utf-8")
            changed_files.append((str(py_file), removed))
            total_removed += removed
            print(f"  cleaned  {py_file}  (-{removed} lines)")

    print(f"\nDone. {len(changed_files)} files changed, {total_removed} lines removed.")
    if changed_files:
        print("\nChanged files:")
        for fp, n in changed_files:
            print(f"  {fp}  (-{n})")


if __name__ == "__main__":
    main()
