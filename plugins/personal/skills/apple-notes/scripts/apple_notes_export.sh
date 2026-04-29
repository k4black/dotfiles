#!/bin/bash
# Export an Apple Note to Markdown via GUI scripting (File > Export as > Markdown).
# This is the only way to preserve hyperlink URLs — AppleScript `body` strips them.
#
# Requirements: Accessibility permission for the terminal app
#   System Settings > Privacy & Security > Accessibility
#
# Usage:
#   ./apple_notes_export.sh <note_id> <output_dir> [filename]
#
# Arguments:
#   note_id    - Full x-coredata:// note ID
#   output_dir - Directory to save the exported .md file
#   filename   - Optional filename (without .md). Defaults to note title.
#
# Example:
#   ./apple_notes_export.sh "x-coredata://2F9E.../ICNote/p1736" /tmp "my_note"

set -euo pipefail

NOTE_ID="${1:?Usage: $0 <note_id> <output_dir> [filename]}"
OUTPUT_DIR="${2:?Usage: $0 <note_id> <output_dir> [filename]}"
FILENAME="${3:-}"

# Ensure output dir exists
mkdir -p "$OUTPUT_DIR"

osascript <<EOF
tell application "Notes"
    set theNote to note id "$NOTE_ID"
    show theNote
    activate
end tell

delay 1

tell application "System Events"
    tell process "Notes"
        -- Trigger File > Export as > Markdown
        click menu item "Markdown" of menu "Export as" of menu item "Export as" of menu "File" of menu bar 1
    end tell
end tell

delay 2

tell application "System Events"
    tell process "Notes"
        set s to sheet 1 of front window
        set sg to splitter group 1 of s

        -- Set filename if provided
        set filename to "$FILENAME"
        if filename is not "" then
            set focused of text field "Save As:" of sg to true
            keystroke "a" using command down
            keystroke filename
        end if

        -- Navigate to output directory
        keystroke "g" using {command down, shift down}
        delay 0.5
        keystroke "$OUTPUT_DIR"
        delay 0.3
        keystroke return
        delay 1

        -- Click Export
        click button "Export" of sg
    end tell
end tell

delay 1

-- Handle "already exists" Replace dialog if it appears
tell application "System Events"
    tell process "Notes"
        try
            click button "Replace" of sheet 1 of sheet 1 of front window
        end try
    end tell
end tell

delay 0.5
EOF

# Post-process: deduplicate consecutive identical lines in exported .md files
# Apple Notes exports each link twice (once for <a href>, once for display text)
if [ -n "$FILENAME" ]; then
    EXPORT_SUBDIR="$OUTPUT_DIR/$FILENAME"
else
    EXPORT_SUBDIR="$OUTPUT_DIR"
fi

for md_file in "$EXPORT_SUBDIR"/*.md; do
    [ -f "$md_file" ] || continue
    python3 -c "
import sys
lines = open(sys.argv[1], 'r').readlines()
deduped = []
prev = None
for line in lines:
    if line.rstrip() != (prev.rstrip() if prev else None):
        deduped.append(line)
    prev = line
open(sys.argv[1], 'w').writelines(deduped)
print(f'Deduped: {len(lines)} -> {len(deduped)} lines')
" "$md_file"
done

echo "Exported to $EXPORT_SUBDIR/"
