"""Update Anki note fields in batch. Reads JSONL from stdin.

Per-line schema:
    {"id": <nid>, "fields": {"<FieldName>": "<value>", ...}}

Only the listed fields are touched; other fields and tags are preserved.
Wraps AnkiConnect's `updateNoteFields` action.

Usage:
    # One update
    echo '{"id": 1777466685362, "fields": {"Sound": "[sound:foo.mp3]"}}' | \\
      python update_card.py

    # Many updates
    cat <<'EOF' | python update_card.py
    {"id": 1442860633303, "fields": {"Перевод": "полдень (~12:00)"}}
    {"id": 1442860633583, "fields": {"Перевод": "лето"}}
    EOF

Comments (`#`) and blank lines on stdin are ignored.
"""

import argparse
import io
import json
import sys
from typing import Iterator

from anki_connect import anki_request, check_connection


def read_items_from_stdin() -> Iterator[tuple[int, dict]]:
    """Yield (line_no, parsed_json); skip blank/`#` lines; sys.exit on bad JSON."""
    for ln, raw in enumerate(sys.stdin, 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        try:
            yield ln, json.loads(s)
        except json.JSONDecodeError as e:
            print(f"Line {ln}: invalid JSON: {e}", file=sys.stderr)
            sys.exit(2)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Update Anki note fields in batch from JSONL on stdin.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned updates; don't call updateNoteFields.",
    )
    args = p.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if not check_connection():
        print("Could not reach AnkiConnect. Is Anki running?", file=sys.stderr)
        sys.exit(1)

    items = list(read_items_from_stdin())
    if not items:
        print("No updates on stdin.", file=sys.stderr)
        sys.exit(2)

    valid: list[tuple[int, dict]] = []
    failed: list[tuple[int, dict, str]] = []
    for ln, item in items:
        if "id" not in item:
            failed.append((ln, item, "missing 'id'"))
        elif not isinstance(item.get("fields"), dict) or not item["fields"]:
            failed.append((ln, item, "missing or empty 'fields'"))
        else:
            valid.append((ln, item))

    if args.dry_run:
        for ln, item in valid:
            print(f"  DRY #{item['id']:<18} fields={list(item['fields'].keys())}")
        for ln, item, err in failed:
            print(f"  ✗ line {ln}: {err}")
        return

    ok: list[tuple[int, dict]] = []
    for ln, item in valid:
        try:
            anki_request(
                "updateNoteFields",
                note={"id": item["id"], "fields": item["fields"]},
            )
            ok.append((ln, item))
        except Exception as e:
            failed.append((ln, item, str(e)))

    print(f"Updated {len(ok)}/{len(items)} notes.")
    for ln, item in ok:
        print(f"  ✓ #{item['id']:<18} fields={list(item['fields'].keys())}")
    if failed:
        print(f"\n{len(failed)} failed:")
        for ln, item, err in failed:
            nid = item.get("id", "?") if isinstance(item, dict) else "?"
            print(f"  ✗ line {ln} #{nid}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
