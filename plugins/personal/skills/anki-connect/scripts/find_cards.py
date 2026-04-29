"""Look up many Anki notes at once by a list of words.

Match modes:
    * Default: word-boundary substring. `Mittag` matches `der Mittag`, `am Mittag`, but not
      `Mittagspause`. Boundaries are Unicode-aware (works with German umlauts and Cyrillic).
    * --exact: whole-field equality. `Mittag` matches only fields whose value is exactly `Mittag`.

Usage:
    # Search the `Слово` field for any of these words (default field)
    python find_cards.py Mittag Sommer Klavier auf neben

    # Strict whole-field match (e.g. when looking up exact card duplicates)
    python find_cards.py Mittag Sommer --exact

    # Search multiple fields (any of them matches)
    python find_cards.py лето стол -F Перевод -F Слово

    # Compare against a target deck — words are marked "= in target" / "+ elsewhere" / "✗ missing"
    python find_cards.py auf neben Mittag --target-deck "German::0. My German Vocab"

    # Read words from stdin if no positional args (one per line; blank lines and `#` ignored)
    cat lesson.txt | python find_cards.py

    # Show every match in full
    python find_cards.py Klavier --detail

Legend:
    =  found in --target-deck
    +  found, but not in --target-deck (or --target-deck not set)
    ✗  not found anywhere
"""

import argparse
import io
import re
import sys
from typing import Callable

from anki_connect import (
    anki_request,
    check_connection,
    decks_for_notes,
    notes_info,
)


def make_matcher(word: str, exact: bool) -> Callable[[str], bool]:
    """Return a predicate that tests a field value for the given word.

    --exact: case-insensitive whole-field equality (after strip).
    Default: case-insensitive Unicode word-boundary search (`\\b<word>\\b`).
    """
    if exact:
        wl = word.lower()
        return lambda v: v.strip().lower() == wl
    pat = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    return lambda v: bool(pat.search(v))


def build_query(
    words: list[str],
    fields: list[str],
    exact: bool,
    deck: str | None = None,
    tag: str | None = None,
) -> str:
    """OR query over every (word × field). `*word*` (substring) for the wide search,
    `field:word` (whole-field) when --exact. Final filtering happens in Python."""
    qparts = [
        f'"{f}:{w}"' if exact else f'"{f}:*{w}*"'
        for w in words
        for f in fields
    ]
    q = "(" + " OR ".join(qparts) + ")"
    if deck:
        q += f' deck:"{deck}"'
    if tag:
        q += f" tag:{tag}"
    return q


def bucket_notes_by_word(
    notes: list[dict],
    words: list[str],
    fields: list[str],
    exact: bool,
) -> dict[str, list[dict]]:
    """Assign each note to every input word it matches on any of `fields`."""
    matchers = {w: make_matcher(w, exact) for w in words}
    result: dict[str, list[dict]] = {w: [] for w in words}
    for n in notes:
        values = [n["fields"].get(f, {}).get("value", "") for f in fields]
        for w in words:
            m = matchers[w]
            if any(m(v) for v in values):
                result[w].append(n)
    return result


MARKERS: dict[str, str] = {"in-target": "=", "elsewhere": "+", "missing": "✗"}


def status_of(
    matches: list[dict],
    decks_by_nid: dict[int, set[str]],
    target_deck: str | None,
) -> str:
    if not matches:
        return "missing"
    if target_deck and any(
        target_deck in decks_by_nid.get(n["noteId"], set()) for n in matches
    ):
        return "in-target"
    return "elsewhere"


def display_summary(
    word: str,
    matches: list[dict],
    decks_by_nid: dict[int, set[str]],
    target_deck: str | None,
) -> str:
    s = status_of(matches, decks_by_nid, target_deck)
    marker = MARKERS[s]
    if not matches:
        print(f"  {marker} {word}")
        return s
    decks = sorted({d for n in matches for d in decks_by_nid.get(n["noteId"], set())})
    n0 = matches[0]
    slovo = n0["fields"].get("Слово", {}).get("value", "")
    perevod = n0["fields"].get("Перевод", {}).get("value", "")
    if len(perevod) > 50:
        perevod = perevod[:50] + "…"
    suffix = f"  ({len(matches)} notes)" if len(matches) > 1 else ""
    print(f"  {marker} {word:<22} → {slovo!r} = {perevod!r}  in {decks}{suffix}")
    return s


def display_detail(
    word: str, matches: list[dict], decks_by_nid: dict[int, set[str]]
) -> None:
    if not matches:
        print(f"\n✗ {word}: not found")
        return
    print(f"\n• {word}: {len(matches)} note(s)")
    for n in matches:
        decks = sorted(decks_by_nid.get(n["noteId"], set()))
        print(f"    nid={n['noteId']}  model={n['modelName']}  decks={decks}")
        for k, v in n["fields"].items():
            val = v["value"].strip()
            if val:
                if len(val) > 120:
                    val = val[:120] + "…"
                print(f"      {k}: {val}")
        if n["tags"]:
            print(f"      tags: {', '.join(n['tags'])}")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Find Anki notes by a list of words across one or more fields.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("words", nargs="*", help="Words to look up.")
    p.add_argument(
        "-F",
        "--field",
        action="append",
        default=[],
        help="Field name to match (repeatable). Default: Слово.",
    )
    p.add_argument(
        "--exact",
        action="store_true",
        help="Whole-field match instead of word-boundary substring.",
    )
    p.add_argument("-d", "--deck", help="Restrict search to one deck.")
    p.add_argument("-t", "--tag", help="Restrict search to one tag.")
    p.add_argument(
        "--target-deck", help="Mark matches in this deck specially (= vs +)."
    )
    p.add_argument(
        "--detail", action="store_true", help="Full card details instead of summary."
    )
    args = p.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    fields = args.field or ["Слово"]
    words = list(args.words)
    if not words and not sys.stdin.isatty():
        for line in sys.stdin:
            s = line.strip()
            if s and not s.startswith("#"):
                words.append(s)
    if not words:
        p.error("provide words as arguments or via stdin")

    if not check_connection():
        print("Could not reach AnkiConnect. Is Anki running?")
        sys.exit(1)

    print(
        f"Searching {len(words)} word(s) in fields {fields}"
        f" mode={'exact' if args.exact else 'word-boundary'}"
        f"{' deck=' + repr(args.deck) if args.deck else ''}"
        f"{' tag=' + args.tag if args.tag else ''}\n"
    )

    query = build_query(words, fields, args.exact, args.deck, args.tag)
    all_notes = notes_info(anki_request("findNotes", query=query))
    all_decks = decks_for_notes([n["noteId"] for n in all_notes])

    word_to_notes = bucket_notes_by_word(all_notes, words, fields, args.exact)

    counts = {"in-target": 0, "elsewhere": 0, "missing": 0}
    for w in words:
        matches = word_to_notes[w]
        d = {n["noteId"]: all_decks.get(n["noteId"], set()) for n in matches}
        if args.detail:
            display_detail(w, matches, d)
        else:
            counts[display_summary(w, matches, d, args.target_deck)] += 1

    if not args.detail:
        if args.target_deck:
            print(
                f"\n= {counts['in-target']} in {args.target_deck!r}  "
                f"+ {counts['elsewhere']} elsewhere  "
                f"✗ {counts['missing']} missing"
            )
        else:
            print(f"\n+ {counts['elsewhere']} found  ✗ {counts['missing']} missing")


if __name__ == "__main__":
    main()
