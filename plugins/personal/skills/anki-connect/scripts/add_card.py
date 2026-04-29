"""Add Anki notes in batch. Reads JSONL from stdin (one note per line).

Per-line schema:
    {"fields": {"<FieldName>": "<value>", ...}, "tags": [...], "deck": "...", "model": "...", "clone_from": <nid>}

Required: either `fields`, or `clone_from` (which seeds fields from another note).
Per-line `deck`, `model`, `tags`, `fields` override the CLI defaults / cloned source.

Usage:
    # Plain new notes — defaults from CLI
    echo '{"fields":{"Слово":"der Tisch","Перевод":"стол"}}
    {"fields":{"Слово":"die Wohnung","Перевод":"квартира"}}' | \\
      python add_card.py -d "German::0. My German Vocab" -m "My German" \\
                         -t lesson-2026-04-29

    # Clone an existing note (inherits all fields + tags from source)
    echo '{"clone_from": 1442860633303}' | \\
      python add_card.py -d "German::0. My German Vocab" -t lesson-2026-04-29 \\
                         --allow-duplicate

    # Mixed batch: some new, some cloned, with per-line overrides
    cat <<'EOF' | python add_card.py -d "German::0. My German Vocab" -m "My German" \\
                                     -t lesson-2026-04-29 --allow-duplicate
    {"clone_from": 1442860633303}
    {"clone_from": 1442860633583}
    {"fields":{"Слово":"der Stab","Перевод":"палка"}}
    {"fields":{"Слово":"die Schweiz","Перевод":"Швейцария"}, "tags":["geography"]}
    EOF

Notes:
    --allow-duplicate is needed when cloning, because Anki's first-field duplicate
    check is global (across all decks). The duplicate is intentional — you want the
    same content present in another deck.

    Comments (`#`) and blank lines in stdin are ignored.
"""

import argparse
import json
import sys

from anki_connect import anki_request, check_connection


def label_of(fields, line_no):
    return fields.get("Слово") or fields.get("Front") or f"line-{line_no}"


def main():
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
    p.add_argument("--dry-run", action="store_true", help="Show planned notes; don't call addNote.")
    args = p.parse_args()

    if not check_connection():
        print("Could not reach AnkiConnect. Is Anki running?", file=sys.stderr)
        sys.exit(1)

    # --- parse stdin ---
    items = []
    for ln, raw in enumerate(sys.stdin, 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        try:
            items.append((ln, json.loads(s)))
        except json.JSONDecodeError as e:
            print(f"Line {ln}: invalid JSON: {e}", file=sys.stderr)
            sys.exit(2)
    if not items:
        print("No notes on stdin.", file=sys.stderr)
        sys.exit(2)

    # --- prefetch clone sources in one batch (saves RTTs) ---
    clone_ids = sorted({i["clone_from"] for _, i in items if "clone_from" in i})
    sources = {}
    if clone_ids:
        for n in anki_request("notesInfo", notes=clone_ids):
            sources[n["noteId"]] = n

    # --- process ---
    ok, failed = [], []
    for ln, item in items:
        deck = item.get("deck") or args.deck
        model = item.get("model") or args.model
        fields = {}
        tags = set(args.tag)

        if "clone_from" in item:
            src = sources.get(item["clone_from"])
            if not src:
                failed.append((ln, {}, f"clone_from {item['clone_from']} not found"))
                continue
            model = item.get("model") or src["modelName"]
            fields = {k: v["value"] for k, v in src["fields"].items()}
            tags |= set(src.get("tags", []))

        fields.update(item.get("fields", {}))
        tags |= set(item.get("tags", []))

        if not model:
            failed.append((ln, fields, "no model (-m, line.model, or clone_from)"))
            continue
        if not fields:
            failed.append((ln, fields, "no fields"))
            continue

        note = {
            "deckName": deck,
            "modelName": model,
            "fields": fields,
            "tags": sorted(tags),
            "options": {"allowDuplicate": args.allow_duplicate},
        }

        if args.dry_run:
            print(f"  DRY {label_of(fields, ln):<22} deck={deck!r} model={model!r} tags={sorted(tags)}")
            continue

        try:
            nid = anki_request("addNote", note=note)
            ok.append((ln, fields, nid))
        except Exception as e:
            failed.append((ln, fields, str(e)))

    # --- report ---
    total = len(items)
    if not args.dry_run:
        print(f"Created {len(ok)}/{total} notes.")
        for ln, f, nid in ok:
            print(f"  ✓ {label_of(f, ln):<22} #{nid}")
    if failed:
        print(f"\n{len(failed)} failed:")
        for ln, f, err in failed:
            print(f"  ✗ line {ln} {label_of(f, ln)}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
