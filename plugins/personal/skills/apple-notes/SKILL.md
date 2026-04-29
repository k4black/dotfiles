---
name: apple-notes
description: Use when the user wants to read, search, rename, move, or reorganize Apple Notes — especially notes containing hyperlinks, where naive AppleScript/MCP body operations silently strip URLs.
---

# Apple Notes

Read and manipulate Apple Notes safely. The naive paths (AppleScript `body`, MCP `update-note`, `set name`) all have non-obvious failure modes — every one of them can silently destroy URLs, prepend instead of replace, or operate on a stale ID. This skill encodes the workarounds.

Scripts are bundled in `./scripts/`.

## Critical gotchas

### `body` does not contain link URLs

AppleScript `body` returns HTML where links appear as `<u>Title</u>` **without `href` URLs**. The actual URLs are stored in Apple Notes' internal CoreData format and are inaccessible via AppleScript.

**Consequence**: read-modify-write of a note that contains hyperlinks will lose every URL. If a note has links, you MUST export to markdown first (see workflow below) — or use the MCP tool `get-note-markdown`, which preserves URLs and is the preferred path when available.

### The title is a styled `<div>`, not `<h1>`

Apple Notes derives the displayed title from the first line of the body. That first line is:

```html
<div><b><span style="font-size: 24px">Title</span></b></div>
```

Do **not** search for `<h1>` — it won't match, and any "replace `<h1>...</h1>`" logic will silently fall through and *prepend* a new title instead of replacing the old one, corrupting the note.

### `set name` only updates the list preview

`set name of note id X to "Y"` updates the sidebar preview only — the actual title (rendered from the body) is unchanged. To rename properly, edit the title `<div>` inside the body.

### MCP `move-note` creates a new ID

The MCP `move-note` tool creates a new note (new ID) at the destination; the old ID lands in Recently Deleted. Re-fetch the note by search/list after every move before doing further operations.

### MCP `update-note` requires `newContent`

You can't update just the title via MCP without rewriting the entire body — risks formatting loss. For title-only changes, use the AppleScript-on-body pattern below.

### Search includes trash

`search-notes` (MCP) returns multiple matches and includes Recently Deleted. Always verify folder + ID before operating; old IDs from `move-note` end up in trash.

## Workflows

### Edit a note that contains links

```
1. Export   →  ./scripts/apple_notes_export.sh <note_id> <output_dir> [filename]
                (or MCP get-note-markdown if it works for the note)
2. Read     →  the .md file; links are [Title](URL) (Apple emits ++[Title](URL)++)
3. Modify   →  classify, reorganize, merge, etc.
4. Re-import →  python3 ./scripts/apple_notes_import.py <md_file> --note-id <id>
               (creates new note: omit --note-id, pass --folder <name>)
```

The import script converts markdown links to `<a href>` and writes the body via a temp file (avoids shell escaping issues). It also writes the title as the styled `<div>` Apple expects.

### Rename a note (title only, preserve body)

Don't use MCP `update-note`. Do a body-edit via AppleScript:

```python
import subprocess, tempfile, os

note_id = "x-coredata://..."
new_title = "🎲 PnP: My Game"

body = subprocess.run(
    ['osascript', '-e', f'tell application "Notes" to get body of note id "{note_id}"'],
    capture_output=True, text=True
).stdout.strip()

# Replace the title <div> only — match the styled span, not <h1>.
# (Adapt the regex to your exact existing title.)

with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
    f.write(body)
    tmp = f.name

subprocess.run(['osascript', '-e', f'''
set f to POSIX file "{tmp}"
set fRef to open for access f
set newBody to read fRef as «class utf8»
close access fRef
tell application "Notes"
    set body of note id "{note_id}" to newBody
end tell
'''])
os.unlink(tmp)
```

If the note has links, do NOT round-trip through `body` — use the export → modify → import workflow instead.

### Reorganize (move + rename + preserve links)

1. **Export** to markdown (only if note has links).
2. **Move** via MCP `move-note`.
3. **Re-fetch** the new ID (search/list — the move created a new note).
4. **Rename** the title `<div>` via the AppleScript pattern above.
5. **Re-import** the markdown into the new note if links must survive.

## Export script (`scripts/apple_notes_export.sh`)

GUI-scripted File → Export as → Markdown. Requires Accessibility permission for the terminal app (System Settings → Privacy & Security → Accessibility).

```
./scripts/apple_notes_export.sh "x-coredata://.../ICNote/p1736" /tmp my_export
```

Notes:
- Output lands in `<output_dir>/<filename>/<filename>.md`.
- Links export as `++[Title](URL)++` (Apple's flavor with strikethrough markers).
- Apple sometimes duplicates links (one for `<a href>`, one for display text); the script deduplicates consecutive identical lines as post-processing.

## Import script (`scripts/apple_notes_import.py`)

```
# Create a new note in a folder
python3 ./scripts/apple_notes_import.py path/to.md --folder "Projects"

# Update an existing note by ID (preserves the ID; replaces body)
python3 ./scripts/apple_notes_import.py path/to.md --note-id "x-coredata://...ICNote/p1234"
```

Converts `[Title](URL)` and `++[Title](URL)++` to `<a href="URL">Title</a>`, headers (`# Title`) to the styled-div Apple expects, and `**bold**` to `<b>`. Apple Notes converts the HTML `<a>` tags back into clickable links on import.

## Codex vs Claude Code

The MCP `apple-notes` plugin (Claude Code only) provides `get-note-markdown`, `move-note`, `search-notes`, etc. — prefer those when available; they're faster and don't need GUI scripting.

Under Codex (no MCP), use the bundled scripts + raw AppleScript.

## Requirements

- macOS, Apple Notes app
- For export: Accessibility permission for the terminal
- Python 3 (stdlib only) for the import script
