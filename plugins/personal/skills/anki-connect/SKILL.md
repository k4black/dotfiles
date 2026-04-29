---
name: anki-connect
description: Use when the user invokes /anki-connect, asks to create or look up Anki flashcards, copy cards between decks, or notices something worth remembering long-term (a concept, gotcha, or vocab from a lesson).
---

# Anki-Connect

Look up and create Anki notes via the [Anki-Connect](https://git.sr.ht/~foosoft/anki-connect) add-on (HTTP API on `http://127.0.0.1:8765`, API version 6, Anki 2.1.x).

Two batch-friendly scripts under `./scripts/`:

| Script | Purpose |
|--------|---------|
| `find_cards.py` | Look up many words at once — word-boundary match (default) or `--exact`, deck-aware, target-deck classification |
| `add_card.py`   | Always batch — JSONL on stdin, supports `clone_from` to copy cards between decks |
| `update_card.py` | Partial field updates — JSONL `{"id": <nid>, "fields": {...}}`, leaves other fields/tags alone |
| `anki_connect.py` | Underlying HTTP client. Import for ad-hoc Python (`anki_request("<action>", **params)`). Full API: https://git.sr.ht/~foosoft/anki-connect |

## find_cards.py

```bash
# Word-boundary match in the Word field (default). `Mittag` finds `der Mittag`,
# `am Mittag`, but NOT `Mittagspause`. Unicode-aware (umlauts, Cyrillic).
python ./scripts/find_cards.py Mittag Sommer Klavier auf neben

# Whole-field equality when you need strict matching
python ./scripts/find_cards.py Mittag Sommer --exact

# Multi-field search (any-match across all listed fields)
python ./scripts/find_cards.py лето стол -F Translation -F Word

# Lesson dedupe: classify each word as in-target / elsewhere / missing
python ./scripts/find_cards.py auf neben Mittag Sommer Klavier \
    --target-deck "German::0. My German Vocab"

# Pipe a file in (auto-reads stdin when no positional words)
cat lesson_words.txt | python ./scripts/find_cards.py

# Full details for a single word
python ./scripts/find_cards.py Klavier --detail
```

Summary legend: `=` in `--target-deck`, `+` found elsewhere, `✗` missing.

## add_card.py

Always reads JSONL on stdin (one note per line). Per-line schema:

```json
{"fields": {"<FieldName>": "<value>", ...}, "tags": [...], "deck": "...", "model": "...", "clone_from": <nid>}
```

CLI provides defaults; per-line keys override or extend. Either `fields` or `clone_from` is required per line.

```bash
# Plain new notes
echo '{"fields":{"Word":"der Tisch","Translation":"стол"}}
{"fields":{"Word":"die Wohnung","Translation":"квартира"}}' | \
  python ./scripts/add_card.py -d "German::0. My German Vocab" -m "My German" \
                               -t lesson-2026-04-29

# Clone existing notes into another deck (Sound, Image and tags inherited from source)
echo '{"clone_from": 1442860633303}
{"clone_from": 1442860633583}' | \
  python ./scripts/add_card.py -d "German::0. My German Vocab" \
                               -t lesson-2026-04-29 -t copied-from-db1 \
                               --allow-duplicate

# Dry-run first to preview
... | python ./scripts/add_card.py -d ... -m ... -t ... --dry-run
```

`--allow-duplicate` is **required** when cloning. Anki's first-field duplicate check is global; the duplicate is intentional (you want the same content in another deck).

## update_card.py

Patch only specific fields on existing notes. Other fields and all tags are preserved.

```bash
# Bulk-fix translations on a few cards
cat <<'EOF' | python ./scripts/update_card.py
{"id": 1442860633303, "fields": {"Translation": "полдень (~12:00)"}}
{"id": 1442860633583, "fields": {"Translation": "лето"}}
EOF

# Set Sound on a single note
echo '{"id": 1777466685362, "fields": {"Sound": "[sound:foo.mp3]"}}' | \
  python ./scripts/update_card.py
```

## Common workflows

### Lesson → cards

1. Extract the words you want carded from your notes / lesson photo.
2. **Dedupe**: `find_cards.py <words> --target-deck "<lesson deck>"`. Three buckets fall out:
   - `=` already in target deck → no action
   - `+` exists elsewhere (e.g. `German::Deutsch DB1`) → clone into the lesson deck
   - `✗` missing → create new
3. Build a JSONL with `clone_from` lines for the `+` bucket and `fields` lines for the `✗` bucket.
4. Pipe to `add_card.py` with `-t lesson-<date>` and `--allow-duplicate`.
5. Sound: HyperTTS doesn't expose itself via Anki-Connect — open the lesson deck in Anki, select the new cards (filter by the lesson tag), press `Ctrl+Shift+T` to fill the `Sound` field.

### One-off card

Same script — JSONL with one line:

```bash
echo '{"fields":{"Word":"der Stab","Translation":"палка"}}' | \
  python ./scripts/add_card.py -d "German::0. My German Vocab" -m "My German" -t lesson-2026-04-29
```

### Ad-hoc Anki API call

```bash
python -c "from anki_connect import anki_request; print(anki_request('deckNames'))"
python -c "from anki_connect import anki_request; print(anki_request('modelFieldNames', modelName='My German'))"
```

## Card quality rules

The user has 226 leeches. Quality over quantity.

1. **Atomic** — one fact per card. If the answer has "and", split it.
2. **Short, specific front** — few words, one unambiguous answer.
3. **Minimal back** — no unnecessary text.
4. **Visual over prose** — file trees, code blocks, or diagrams over sentences when the answer is structural.
5. **No trivia** — only things worth remembering long-term.
6. **Tag consistently** — lowercase, comma-separated. Lesson cards: `lesson-YYYY-MM-DD`.
7. **For German nouns: include the article in the front field** (e.g. `der Sommer`, `die Wohnung`) — gender is part of the word.

## Workflow checklist (before creating any card)

1. **Propose** the card(s): show fields/deck/tags as a JSONL preview the user can edit.
2. **Wait** for explicit approval. Never create without confirmation.
3. **Dedupe** with `find_cards.py --target-deck <deck>`.
4. **Create** via `add_card.py` (with `--dry-run` first if the batch is large).
5. **Confirm** with the returned note IDs.

## Troubleshooting

The connection requires Anki desktop running with the [Anki-Connect](https://git.sr.ht/~foosoft/anki-connect) add-on installed (AnkiWeb code [2055492159](https://ankiweb.net/shared/info/2055492159)). Verify reachability — `http://127.0.0.1:8765` should display `Anki-Connect`.

On macOS, disable App Nap so Anki keeps responding when in the background:

```bash
defaults write net.ankiweb.dtop NSAppSleepDisabled -bool true
defaults write net.ichi2.anki NSAppSleepDisabled -bool true
defaults write org.qt-project.Qt.QtWebEngineCore NSAppSleepDisabled -bool true
```
