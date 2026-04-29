"""Look up many Anki notes at once by a list of words.

Usage:
    # Default: search the `Слово` field, exact match (per word)
    python find_cards.py Mittag Sommer Klavier auf neben

    # Also try der/die/das <word> automatically (for German nouns without article)
    python find_cards.py Mittag Sommer --with-articles

    # Search multiple fields (any of them matches)
    python find_cards.py лето стол -F Перевод -F Слово

    # Compare against a target deck — every found word is marked "= in target"
    # vs "+ elsewhere", which is the lesson-deduplication workflow
    python find_cards.py auf neben Mittag --target-deck "German::0. My German Vocab"

    # Read words from stdin (one per line; blank lines and # comments ignored)
    cat lesson.txt | python find_cards.py --stdin --with-articles

    # Show every match in full, not just one summary line per word
    python find_cards.py Klavier --detail

Legend:
    =  found in --target-deck
    +  found, but not in --target-deck (or --target-deck not set)
    ✗  not found anywhere
"""

import argparse
import io
import sys

from anki_connect import anki_request, check_connection


def card_decks(note_ids):
    if not note_ids:
        return {}
    cids = anki_request("findCards", query="nid:" + ",".join(map(str, note_ids)))
    if not cids:
        return {}
    out = {}
    for c in anki_request("cardsInfo", cards=cids):
        out.setdefault(c["note"], set()).add(c["deckName"])
    return out


def variants(word, with_articles):
    out = [word]
    if with_articles:
        out += [f"der {word}", f"die {word}", f"das {word}"]
    return out


def find_word(word, fields, with_articles, deck=None, tag=None):
    """Return notes whose any of `fields` matches the word (or der/die/das <word>) exactly."""
    qparts = []
    for f in fields:
        for v in variants(word, with_articles):
            qparts.append(f'"{f}:{v}"')
    q = "(" + " OR ".join(qparts) + ")"
    if deck:
        q += f' deck:"{deck}"'
    if tag:
        q += f" tag:{tag}"
    ids = anki_request("findNotes", query=q)
    if not ids:
        return []
    notes = anki_request("notesInfo", notes=ids)
    wanted = {v.lower() for v in variants(word, with_articles)}
    return [
        n
        for n in notes
        if any(
            n["fields"].get(f, {}).get("value", "").strip().lower() in wanted for f in fields
        )
    ]


def status_of(matches, decks_by_nid, target_deck):
    if not matches:
        return "missing"
    if target_deck and any(target_deck in decks_by_nid.get(n["noteId"], set()) for n in matches):
        return "in-target"
    return "elsewhere"


MARKERS = {"in-target": "=", "elsewhere": "+", "missing": "✗"}


def display_summary(word, matches, decks_by_nid, target_deck):
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


def display_detail(word, matches, decks_by_nid):
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


def main():
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
        "--with-articles",
        action="store_true",
        help="Also try der/die/das <word> (German nouns).",
    )
    p.add_argument("-d", "--deck", help="Restrict search to one deck.")
    p.add_argument("-t", "--tag", help="Restrict search to one tag.")
    p.add_argument(
        "--target-deck",
        help="Highlight matches in this deck specially (= vs +).",
    )
    p.add_argument("--detail", action="store_true", help="Full card details instead of summary.")
    p.add_argument("--stdin", action="store_true", help="Also read words from stdin.")
    args = p.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    fields = args.field or ["Слово"]
    words = list(args.words)
    if args.stdin:
        for line in sys.stdin:
            line = line.strip()
            if line and not line.startswith("#"):
                words.append(line)

    if not words:
        p.error("provide words as arguments or via --stdin")

    if not check_connection():
        print("Could not reach AnkiConnect. Is Anki running?")
        sys.exit(1)

    print(
        f"Searching {len(words)} word(s) in fields {fields}"
        f"{' +articles' if args.with_articles else ''}"
        f"{' deck=' + repr(args.deck) if args.deck else ''}"
        f"{' tag=' + args.tag if args.tag else ''}\n"
    )

    counts = {"in-target": 0, "elsewhere": 0, "missing": 0}
    for w in words:
        matches = find_word(w, fields, args.with_articles, deck=args.deck, tag=args.tag)
        d = card_decks([n["noteId"] for n in matches])
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
