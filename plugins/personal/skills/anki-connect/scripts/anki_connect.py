"""AnkiConnect client — talks to Anki desktop via the AnkiConnect addon (localhost:8765).

Requires: Anki desktop running + AnkiConnect addon installed (code: 2055492159).
No external dependencies — only stdlib.
"""

import json
import urllib.request
from typing import Any, Iterable

ANKI_CONNECT_URL = "http://localhost:8765"


def anki_request(action: str, **params: Any) -> Any:
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(
        ANKI_CONNECT_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
    if body.get("error"):
        raise RuntimeError(f"AnkiConnect error: {body['error']}")
    return body["result"]


def notes_info(note_ids: Iterable[int]) -> list[dict]:
    """notesInfo, but tolerant of empty input."""
    ids = list(note_ids)
    if not ids:
        return []
    return anki_request("notesInfo", notes=ids)


def decks_for_notes(note_ids: Iterable[int]) -> dict[int, set[str]]:
    """{note_id: set(deckName, ...)}. One findCards + one cardsInfo round-trip total."""
    ids = list(note_ids)
    if not ids:
        return {}
    cids = anki_request("findCards", query="nid:" + ",".join(map(str, ids)))
    if not cids:
        return {}
    out: dict[int, set[str]] = {}
    for c in anki_request("cardsInfo", cards=cids):
        out.setdefault(c["note"], set()).add(c["deckName"])
    return out


def add_notes(notes: list[dict]) -> list[tuple[int | None, str | None]]:
    """Add multiple notes in one round-trip. Returns aligned list of (note_id|None, error|None).

    Uses canAddNotesWithErrorDetail for failure reasons only when at least one note fails,
    so the happy path stays at one round-trip.
    """
    if not notes:
        return []
    nids: list[int | None] = anki_request("addNotes", notes=notes)
    if all(n is not None for n in nids):
        return [(n, None) for n in nids]
    details: list[dict] = anki_request("canAddNotesWithErrorDetail", notes=notes)
    out: list[tuple[int | None, str | None]] = []
    for nid, d in zip(nids, details):
        if nid is not None:
            out.append((nid, None))
        elif d.get("canAdd", True):
            out.append((None, "addNotes returned null but canAdd was true"))
        else:
            out.append((None, d.get("error", "unknown error")))
    return out


def note_label(fields: dict, fallback: str = "?") -> str:
    """Pick a human-readable label from a fields dict (My German `Слово` or Basic `Front`).

    Accepts both raw-string fields and notesInfo's {"value": ...} shape.
    """
    for key in ("Word", "Слово", "Front", "word"):
        v = fields.get(key)
        if isinstance(v, dict):
            v = v.get("value")
        if v:
            return v
    return fallback


def list_cards(query: str) -> list[dict]:
    """Search and return notes with flattened fields ({name: value}, no inner dicts)."""
    note_ids = anki_request("findNotes", query=query)
    return [
        {
            "noteId": n["noteId"],
            "modelName": n["modelName"],
            "tags": n["tags"],
            "fields": {name: val["value"] for name, val in n["fields"].items()},
        }
        for n in notes_info(note_ids)
    ]


def list_models() -> list[str]:
    return anki_request("modelNames")


def list_decks() -> list[str]:
    return anki_request("deckNames")


def check_connection() -> bool:
    try:
        anki_request("version")
        return True
    except Exception:
        return False


if __name__ == "__main__":
    if check_connection():
        print("Connected to AnkiConnect.")
        print("Decks:", list_decks())
    else:
        print("Could not reach AnkiConnect. Is Anki running with the addon installed?")
