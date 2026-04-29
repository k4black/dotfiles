"""Add Anki notes in batch. Reads JSONL from stdin (one note per line).

Per-line schema:
    {"fields": {"<FieldName>": "<value>", ...}, "tags": [...], "deck": "...", "model": "...", "clone_from": <nid>}

Required: either `fields`, or `clone_from` (which seeds fields from another note).
Per-line keys override the CLI defaults / cloned source.

Usage:
    # Plain new notes — defaults from CLI
    echo '{"fields":{"Слово":"der Tisch","Перевод":"стол"}}
    {"fields":{"Слово":"die Wohnung","Перевод":"квартира"}}' | \\
      python add_card.py -d "German::0. My German Vocab" -m "My German" -t lesson-2026-04-29

    # Clone existing notes (inherits all fields + tags from the source)
    echo '{"clone_from": 1442860633303}
    {"clone_from": 1442860633583}' | \\
      python add_card.py -d "German::0. My German Vocab" -t lesson-2026-04-29 \\
                         -t copied-from-db1 --allow-duplicate

    # Clone with one overridden field
    echo '{"clone_from": 1442860633303, "fields":{"Перевод":"override"}}' | \\
      python add_card.py -d "..." --allow-duplicate

    # --allow-duplicate is required for clone_from across decks: Anki's first-field
    # duplicate check is global, so the "duplicate" is what we want.

    # Comments (`#`) and blank lines on stdin are ignored.
"""

import argparse
import io
import json
import sys
from typing import Iterator

from anki_connect import add_notes, check_connection, note_label, notes_info


def read_items_from_stdin() -> Iterator[tuple[int, dict]]:
    """Yield (line_no, parsed_json) pairs; skip blank/`#` lines; sys.exit on bad JSON."""
    for ln, raw in enumerate(sys.stdin, 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        try:
            yield ln, json.loads(s)
        except json.JSONDecodeError as e:
            print(f"Line {ln}: invalid JSON: {e}", file=sys.stderr)
            sys.exit(2)


def build_note(
    item: dict,
    args: argparse.Namespace,
    sources: dict[int, dict],
) -> tuple[dict | None, dict, str | None]:
    """Resolve one stdin item into a final Anki `note` dict.

    Returns (note_dict, fields_for_label, error). Exactly one of note_dict/error is non-None.
    """
    deck = item.get("deck") or args.deck
    model = item.get("model") or args.model
    fields = {}
    tags = set(args.tag)

    if "clone_from" in item:
        src = sources.get(item["clone_from"])
        if not src:
            return None, {}, f"clone_from {item['clone_from']} not found"
        model = item.get("model") or src["modelName"]
        fields = {k: v["value"] for k, v in src["fields"].items()}
        tags |= set(src.get("tags", []))

    fields.update(item.get("fields", {}))
    tags |= set(item.get("tags", []))

    if not model:
        return None, fields, "no model (-m, line.model, or clone_from)"
    if not fields:
        return None, fields, "no fields"

    note = {
        "deckName": deck,
        "modelName": model,
        "fields": fields,
        "tags": sorted(tags),
        "options": {"allowDuplicate": args.allow_duplicate},
    }
    return note, fields, None


def main() -> None:
    p = argparse.ArgumentParser(
        description="Add Anki notes in batch from JSONL on stdin.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("-d", "--deck", required=True, help="Default deck for every note.")
    p.add_argument(
        "-m",
        "--model",
        help="Default model. Required unless every line has `model` or `clone_from`.",
    )
    p.add_argument(
        "-t",
        "--tag",
        action="append",
        default=[],
        help="Default tag (repeatable), merged into every note.",
    )
    p.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="Allow Anki's first-field duplicate check (required for clone_from across decks).",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Show planned notes; don't call addNotes."
    )
    args = p.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if not check_connection():
        print("Could not reach AnkiConnect. Is Anki running?", file=sys.stderr)
        sys.exit(1)

    items = list(read_items_from_stdin())
    if not items:
        print("No notes on stdin.", file=sys.stderr)
        sys.exit(2)

    clone_ids = sorted({i["clone_from"] for _, i in items if "clone_from" in i})
    sources = {n["noteId"]: n for n in notes_info(clone_ids)}

    planned = []  # (line_no, fields, note_dict)
    failed = []   # (line_no, fields, error)
    for ln, item in items:
        note, fields, err = build_note(item, args, sources)
        if err:
            failed.append((ln, fields, err))
        else:
            planned.append((ln, fields, note))

    if args.dry_run:
        for ln, fields, note in planned:
            print(
                f"  DRY {note_label(fields, str(ln)):<22} "
                f"deck={note['deckName']!r} model={note['modelName']!r} tags={note['tags']}"
            )
        for ln, fields, err in failed:
            print(f"  ✗ line {ln} {note_label(fields, str(ln))}: {err}")
        return

    results = add_notes([n for _, _, n in planned])
    ok = []
    for (ln, fields, _), (nid, err) in zip(planned, results):
        if nid is not None:
            ok.append((ln, fields, nid))
        else:
            failed.append((ln, fields, err or "unknown error"))

    print(f"Created {len(ok)}/{len(items)} notes.")
    for ln, f, nid in ok:
        print(f"  ✓ {note_label(f, str(ln)):<22} #{nid}")
    if failed:
        print(f"\n{len(failed)} failed:")
        for ln, f, err in failed:
            print(f"  ✗ line {ln} {note_label(f, str(ln))}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
