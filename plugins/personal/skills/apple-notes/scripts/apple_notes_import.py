#!/usr/bin/env python3
"""Import a Markdown file into Apple Notes with clickable links.

Reads a markdown file, converts links to HTML <a href> tags, and creates or
updates an Apple Note. Apple Notes converts <a> tags into internal clickable links.

Usage:
    # Create a new note
    python3 apple_notes_import.py <md_file> --folder "Projects"

    # Update an existing note by ID
    python3 apple_notes_import.py <md_file> --note-id "x-coredata://...ICNote/p1234"

The markdown file should use standard link syntax: [Title](URL)
Apple's export format ++[Title](URL)++ is also supported.
"""

import argparse
import re
import subprocess
import sys
import tempfile
import os


def md_to_html(md_content: str) -> str:
    """Convert markdown content to HTML suitable for Apple Notes."""
    lines = md_content.strip().split('\n')
    html_lines = []

    for line in lines:
        line = line.rstrip()

        # Skip empty lines -> <br>
        if not line.strip():
            html_lines.append('<div><br></div>')
            continue

        # Convert markdown links: ++[Title](URL)++ or [Title](URL)
        line = re.sub(
            r'\+\+\[([^\]]+)\]\(([^)]+)\)\+\+',
            r'<a href="\2">\1</a>',
            line
        )
        line = re.sub(
            r'(?<!\+)\[([^\]]+)\]\(([^)]+)\)(?!\+)',
            r'<a href="\2">\1</a>',
            line
        )

        # Convert headers
        if line.startswith('# '):
            title = line[2:].strip()
            # Remove bold markers if present
            title = re.sub(r'\*{2,}(.+?)\*{2,}', r'\1', title)
            html_lines.append(
                f'<div><b><span style="font-size: 24px">{title}</span></b></div>'
            )
            continue

        # Convert bold **text** or __text__
        line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
        line = re.sub(r'__(.+?)__', r'<b>\1</b>', line)

        # Strip trailing whitespace markers
        line = line.rstrip(' ')

        html_lines.append(f'<div>{line}</div>')

    return '\n'.join(html_lines)


def create_note_applescript(html: str, folder: str) -> str:
    """Create a new note via AppleScript and return its ID."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.html', delete=False, encoding='utf-8'
    ) as f:
        f.write(html)
        tmppath = f.name

    try:
        applescript = f'''
set f to POSIX file "{tmppath}"
set fRef to open for access f
set newBody to read fRef as «class utf8»
close access fRef
tell application "Notes"
    set theNote to make new note at folder "{folder}" with properties {{body:newBody}}
    return id of theNote
end tell
'''
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Error creating note: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        return result.stdout.strip()
    finally:
        os.unlink(tmppath)


def update_note_applescript(html: str, note_id: str) -> None:
    """Update an existing note's body via AppleScript."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.html', delete=False, encoding='utf-8'
    ) as f:
        f.write(html)
        tmppath = f.name

    try:
        applescript = f'''
set f to POSIX file "{tmppath}"
set fRef to open for access f
set newBody to read fRef as «class utf8»
close access fRef
tell application "Notes"
    set body of note id "{note_id}" to newBody
end tell
'''
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Error updating note: {result.stderr}", file=sys.stderr)
            sys.exit(1)
    finally:
        os.unlink(tmppath)


def main():
    parser = argparse.ArgumentParser(description='Import markdown into Apple Notes')
    parser.add_argument('md_file', help='Path to markdown file')
    parser.add_argument('--folder', default='Notes', help='Folder for new note (default: Notes)')
    parser.add_argument('--note-id', help='Update existing note by ID instead of creating new')
    args = parser.parse_args()

    with open(args.md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    html = md_to_html(md_content)

    if args.note_id:
        update_note_applescript(html, args.note_id)
        print(f"Updated note: {args.note_id}")
    else:
        note_id = create_note_applescript(html, args.folder)
        print(f"Created note: {note_id}")


if __name__ == '__main__':
    main()
