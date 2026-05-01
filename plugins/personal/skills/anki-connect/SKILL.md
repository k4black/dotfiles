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
    --target-deck "German::My Vocab"

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
  python ./scripts/add_card.py -d "German::My Vocab" -m "My German"

# Clone existing notes into another deck (Sound, Image and tags inherited from source)
echo '{"clone_from": 1442860633303}
{"clone_from": 1442860633583}' | \
  python ./scripts/add_card.py -d "German::My Vocab" \
                               -t copied-from-db1 \
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
   - `+` exists elsewhere (e.g. `Archive::Deutsch DB1`) → clone into the lesson deck
   - `✗` missing → create new
3. Build a JSONL with `clone_from` lines for the `+` bucket and `fields` lines for the `✗` bucket.
4. Pipe to `add_card.py` with `--allow-duplicate` (only needed when cloning).
5. Sound: HyperTTS doesn't expose itself via Anki-Connect — open the lesson deck in Anki, select the new cards (e.g. by recent `mod:` filter), press `Ctrl+Shift+T` to fill the `Sound` field.

### One-off card

Same script — JSONL with one line:

```bash
echo '{"fields":{"Word":"der Stab","Translation":"палка"}}' | \
  python ./scripts/add_card.py -d "German::My Vocab" -m "My German"
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
6. **Don't auto-tag** — keep tagging manual and intentional. Don't add `lesson-YYYY-MM-DD` or similar by default.
7. **For German nouns: include the article in the front field** (e.g. `der Sommer`, `die Wohnung`) — gender is part of the word.

## Workflow checklist (before creating any card)

1. **Propose** the card(s): show fields/deck/tags as a JSONL preview the user can edit.
2. **Wait** for explicit approval. Never create without confirmation.
3. **Dedupe** with `find_cards.py --target-deck <deck>`.
4. **Create** via `add_card.py` (with `--dry-run` first if the batch is large).
5. **Confirm** with the returned note IDs.

## Personal Preferences

How the user wants cards built. These override the generic rules above when in tension.

### External data sources

- **German verb forms CSV**: <https://github.com/viorelsfetea/german-verbs-database/blob/master/output/verbs.csv> (raw: <https://raw.githubusercontent.com/viorelsfetea/german-verbs-database/master/output/verbs.csv>) — 8 047 verbs with `Präsens_ich`, `Präsens_du`, `Präsens_er, sie, es`, `Präteritum_ich`, `Partizip II`, `Konjunktiv II_ich`, `Imperativ Singular`, `Imperativ Plural`, `Hilfsverb`. **Use this as the canonical source for any irregular-verb conjugation** — never hand-author strong-verb forms (vowel changes are unpredictable). `sein` is missing from the CSV; hardcode it. Plural Präsens (wir/ihr/sie) isn't in the CSV either — derive via the rule documented under the `Umregelmäßige Verben` model below.

  Quick lookup snippet:
  ```bash
  curl -sL https://raw.githubusercontent.com/viorelsfetea/german-verbs-database/master/output/verbs.csv -o /tmp/verbs.csv
  python3 -c "import csv; print([r for r in csv.DictReader(open('/tmp/verbs.csv')) if r['Infinitive']=='gehen'][0])"
  ```

### Decks and models

- **Active German vocab deck**: `German::My Vocab` (was `German::0. My German Vocab` — renamed). Old DB1 deck archived as `Archive::Deutsch DB1`.
- **Active irregular-verbs deck**: `German::Irregular Verbs` — separate model, separate workflow.
- **HyperTTS** for `Sound` — fill via Anki GUI (`Ctrl+Shift+T`), not reachable via Anki-Connect.

#### Model `My German` (vocab)

- **Fields**: `Word`, `Translation`, `Sound`, `Image`, `Sentance` (the `Sentance` typo is the canonical field name — match it exactly).
- **Templates** (4 cards per note):
  - `German->Russian` — DE→RU
  - `Russian->German` — RU→DE
  - `Russian->type German` — type-the-answer
  - `FillSentence` — cloze fill-in, renders `[word]` brackets in `Sentance` as `[…]` on Front (with `{{Translation}}` shown as hint) and reveals on Back

#### Model `Umregelmäßige Verben` (irregular verbs)

- **Fields** (13):
  - `Infinitiv Singular`, `Translate`
  - Präsens 6 personal forms: `Präsens 1. Pers`, `Präsens 2. Pers`, `Präsens 3. Pers`, `Präsens 1. Pl`, `Präsens 2. Pl`, `Präsens 3. Pl`
  - Other tenses: `Präteritum 3. Pers`, `Perfekt 3. Pers`, `Konjunktiv II`, `Imperativ Singular`, `Imperativ Plural`
- **Templates** (2 cards per note):
  - `Russian->forms German` — RU translation prompt → Stammformen (Infinitiv + 3 × 3rd person).
  - `Infinitiv->all forms` — RU + Infinitiv prompt → full Präsens conjugation table with grey `[ich] / [du] / [er/sie/es] / [wir] / [ihr] / [sie/Sie]` pronoun labels.
- **Data sources**:
  - **CSV (verbatim)**: ich / du / 3rd-Sg Präsens, Präteritum, Partizip II, Konjunktiv II, Imperativ Sg/Pl, Hilfsverb — from [viorelsfetea/german-verbs-database](https://github.com/viorelsfetea/german-verbs-database/blob/master/output/verbs.csv).
  - **Rule-derived**: wir / ihr / sie-Sie Präsens (German plurals never carry the singular vowel-change, so this is deterministic). Rule: `wir = base [+ separable prefix]`, `ihr = stem + ('et' if stem ends in t/d else 't') [+ prefix]`, `sie/Sie = wir`. Separable detection: presence of a space in `Präsens_ich` from the CSV.
  - **Hardcoded**: `sein` (not in the CSV; standard forms `bin/bist/ist/sind/seid/sind` etc.).
- **Lookup-time normalization** when matching to the CSV: strip parenthetical `(mit D.)`, strip leading `sich `, fix the `umzihen→umziehen` typo on lookup only — leave the stored field unchanged.
- **Caveat — never hand-author CSV-sourced forms** (Präsens singular, Präteritum, Konjunktiv II, Imperativ). Strong-verb stem changes are not derivable. Re-import from the CSV when adding new verbs.
- **Plurals are safe to extend**: the rule above generalizes to any new German verb except `sein` and a tiny number of historical irregulars not in the deck. Verify after import.

### Sentence/cloze format (Sentance field)

- **Bracket notation only**: target form wrapped in `[…]` square brackets, e.g. `Ich lege das Buch [auf] den Tisch.`
- Do **not** use Anki's `{{c1::word}}` cloze syntax — `My German` is a Standard model and the editor warning is annoying.
- The `FillSentence` template renders `[word]` as `[…]` on Front and reveals it on Back via a small bracket-regex JS in the template (already wired). Don't reach for `{{c1::}}` even though it would also work — keep the field clean text.
- Separable verbs in split position: bracket each part, e.g. `Der Bus [kommt] um neun Uhr [an].`

### Sentence design rules

1. **Real-world, natural** — sentences a native speaker would actually say. No textbook filler ("Der Mann ist gut.").
2. **Focus on the target word** — every other word in the sentence should be A1/A2 vocabulary so the learner only has to puzzle out the bracketed form. Don't introduce new vocabulary in support words.
3. **Vary the form across the deck** — across all cards, rotate through:
   - Tenses: Präsens (1/2/3 Sg, 1/3 Pl), Perfekt, Präteritum, Plusquamperfekt, Futur I
   - Mood: Indikativ, Konjunktiv II (`würde`-form, `hätte/wäre + PII`), Imperativ (du / ihr / Sie)
   - Voice: Aktiv, Vorgangspassiv (`wird gebaut`), Zustandspassiv
   - Modal + Infinitiv (können / müssen / wollen / sollen / mögen / dürfen)
   - Verb structure: separable split, separable zusammen with modal, untrennbar, reflexive (`sich`)
   - Sentence types: Aussage, W-Frage, Ja/Nein-Frage, Imperativsatz, Nebensatz (weil / dass / wenn / sobald / während / obwohl), Relativsatz
   - Cases: Nom, Akk, Dat (incl. Wechselpräp Dat-stative vs Akk-motion), Genitiv (`wegen / während / trotz`)
   - Adjectives: predicative, declined attributive (strong / mixed / weak), Komparativ, Superlativ
4. **One bracket-group per card by default** — split into multiple `[…]` only when grammar demands it (separable verbs).
5. **For nouns: include the German article in the `Word` field** (`der Sommer`, `die Wohnung`, `das Klavier`). Gender is part of the word.
6. **Don't tag lesson cards by date** (or anything else automatic) — keep tagging manual and intentional.

### Verification habit

After bulk sentence updates, run a morphology-aware match check:
- Strip article from `Word`, normalize umlauts, handle `ge-` Partizip prefix and separable prefixes when comparing to bracketed forms
- Random-sample ~20 cards for manual eyeball
- Strong-verb irregulars (`wissen→weiß`, `nehmen→nimm`, `geben→gibt`) won't match algorithmically — verify these manually

## Troubleshooting

The connection requires Anki desktop running with the [Anki-Connect](https://git.sr.ht/~foosoft/anki-connect) add-on installed (AnkiWeb code [2055492159](https://ankiweb.net/shared/info/2055492159)). Verify reachability — `http://127.0.0.1:8765` should display `Anki-Connect`.

On macOS, disable App Nap so Anki keeps responding when in the background:

```bash
defaults write net.ankiweb.dtop NSAppSleepDisabled -bool true
defaults write net.ichi2.anki NSAppSleepDisabled -bool true
defaults write org.qt-project.Qt.QtWebEngineCore NSAppSleepDisabled -bool true
```
