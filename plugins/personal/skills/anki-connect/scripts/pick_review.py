"""Pick N random notes from a deck — default filter is `is:due` (cards due today).

Useful for quick offline review or to grab a few cards to talk through.

Usage:
    # 10 random notes due for review in My Vocab
    python pick_review.py -d "German::My Vocab" -n 10

    # 5 random review-state notes (whether due today or not)
    python pick_review.py -d "German::My Vocab" -n 5 --filter "is:review"

    # 20 random notes from the whole deck
    python pick_review.py -d "German::My Vocab" -n 20 --filter ""

    # Reproducible sample
    python pick_review.py -d "German::My Vocab" -n 10 --seed 42

    # Include the example sentence too
    python pick_review.py -d "German::My Vocab" -n 10 --full
"""

import argparse
import random
import re
import sys
from html import unescape

from anki_connect import anki_request, check_connection, notes_info


def clean_html(s: str) -> str:
    return re.sub(r'<[^>]+>', '', unescape(s)).replace('\xa0', ' ').strip()


def first_value(fields: dict, candidates: tuple[str, ...]) -> str:
    for k in candidates:
        v = fields.get(k)
        if isinstance(v, dict):
            v = v.get('value', '')
        if v and v.strip():
            return clean_html(v)
    return ''


WORD_FIELDS = ('Word', 'Слово', 'Front', 'word', 'Infinitiv Singular')
BACK_FIELDS = ('Translation', 'Перевод', 'Back', 'translationRus', 'Translate')
SENT_FIELDS = ('Sentance', 'Sentence', 'Example')


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('-d', '--deck', required=True, help='Deck name.')
    p.add_argument('-n', '--count', type=int, default=10, help='How many to pick.')
    p.add_argument(
        '--filter',
        default='is:due',
        help='Anki search filter ANDed with deck (default: is:due). Pass empty string for all cards.',
    )
    p.add_argument('--seed', type=int, help='Seed for reproducible sampling.')
    p.add_argument('--full', action='store_true', help='Also show sentence/example field.')
    args = p.parse_args()

    if not check_connection():
        print('AnkiConnect unreachable. Is Anki running?', file=sys.stderr)
        sys.exit(1)

    query = f'deck:"{args.deck}"'
    if args.filter.strip():
        query += f' {args.filter}'

    nids = anki_request('findNotes', query=query)
    if not nids:
        print(f'No notes match: {query}')
        return

    if args.seed is not None:
        random.seed(args.seed)
    sample = random.sample(nids, min(args.count, len(nids)))
    notes = notes_info(sample)

    print(f'{len(notes)} of {len(nids)} matching ({query}):')
    for n in notes:
        word = first_value(n['fields'], WORD_FIELDS)
        back = first_value(n['fields'], BACK_FIELDS)
        line = f'  {word:<28} {back}'
        if args.full:
            sent = first_value(n['fields'], SENT_FIELDS)
            if sent:
                line += f'\n    {sent}'
        print(line)


if __name__ == '__main__':
    main()
