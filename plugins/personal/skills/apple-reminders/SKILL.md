---
name: apple-reminders
description: Use when the user wants to add, view, complete, or organize items in Apple Reminders, or says "remind me", "add to my list", "todo".
---

# Apple Reminders

Add items to any Apple Reminders list, view existing reminders, mark items complete, and create new lists. Pure AppleScript via `osascript` — no external deps.

Adapted from [densign01/reminders-skill](https://github.com/densign01/reminders-skill).

## Determine the action

Parse the request:

1. **Add items** — "add X to my list", "remind me to X", "todo: X"
2. **View items** — "what's on my list", "show reminders", "what do I need to do"
3. **Complete items** — "mark X done", "complete X", "I did X"
4. **List all lists** — "what lists do I have", "show my reminder lists"

## List all available lists

```bash
osascript -e 'tell application "Reminders"
    set listNames to {}
    repeat with l in lists
        set end of listNames to name of l
    end repeat
    return listNames
end tell'
```

## View items on a list

```bash
osascript -e 'tell application "Reminders"
    set targetList to list "LIST_NAME"
    set reminderInfo to {}
    repeat with r in (reminders in targetList whose completed is false)
        set reminderName to name of r
        set dueDate to due date of r
        if dueDate is not missing value then
            set reminderName to reminderName & " (due: " & (dueDate as string) & ")"
        end if
        set end of reminderInfo to reminderName
    end repeat
    return reminderInfo
end tell'
```

## Add items to a list

**Step 1 — Pick the list.** If unspecified, ask the user, showing available lists from the query above.

**Step 2 — Check existing items to avoid duplicates** (case-insensitive partial match):

```bash
osascript -e 'tell application "Reminders"
    set targetList to list "LIST_NAME"
    set reminderNames to {}
    repeat with r in (reminders in targetList whose completed is false)
        set end of reminderNames to name of r
    end repeat
    return reminderNames
end tell'
```

**Step 3 — Parse items.** Extract bullet/comma items, due dates ("tomorrow", "in 3 days", "Jan 15"), and notes (after a dash or in parens).

**Step 4 — Present the plan and confirm:**

```
## Adding to [List Name] (X new items)

**Will add:**
- Item 1
- Item 2 (due: tomorrow)

**Already on list (skipping):**
- ~~Item 3~~
```

**Step 5 — Add via AppleScript.** Without due date:

```bash
osascript -e 'tell application "Reminders"
    set targetList to list "LIST_NAME"
    make new reminder in targetList with properties {name:"ITEM_NAME"}
end tell'
```

With due date:

```bash
osascript <<'EOF'
tell application "Reminders"
    set targetList to list "LIST_NAME"
    set dueDate to (current date) + (1 * days)  -- tomorrow
    make new reminder in targetList with properties {name:"ITEM_NAME", due date:dueDate}
end tell
EOF
```

Batch insert (more efficient for multiple items):

```bash
osascript <<'EOF'
tell application "Reminders"
    set targetList to list "LIST_NAME"
    make new reminder in targetList with properties {name:"Item 1"}
    make new reminder in targetList with properties {name:"Item 2"}
    make new reminder in targetList with properties {name:"Item 3", due date:(current date) + (1 * days)}
end tell
EOF
```

## Mark an item complete

```bash
osascript -e 'tell application "Reminders"
    set targetList to list "LIST_NAME"
    repeat with r in (reminders in targetList whose completed is false)
        if name of r contains "SEARCH_TERM" then
            set completed of r to true
            return "Completed: " & name of r
        end if
    end repeat
    return "Not found"
end tell'
```

## Create a new list

```bash
osascript -e 'tell application "Reminders"
    make new list with properties {name:"LIST_NAME"}
end tell'
```

## Date parsing

| Input | AppleScript |
|-------|-------------|
| today | `(current date)` |
| tomorrow | `(current date) + (1 * days)` |
| next week | `(current date) + (7 * days)` |
| in X days | `(current date) + (X * days)` |
| Monday, Tuesday, … | calculate days until that weekday |
| Jan 15, March 3, … | parse and construct date object |

For specific times:

```applescript
set dueDate to (current date) + (1 * days)
set hours of dueDate to 14  -- 2 PM
set minutes of dueDate to 0
```

## Workflow rules

- Always confirm the plan before mutating (showing what will be added/skipped).
- Duplicate detection is case-insensitive, partial match.
- Due dates are optional.
- If the user references a list that doesn't exist, offer to create it rather than silently failing.

## Requirements

- macOS, Apple Reminders app
- No external dependencies (`osascript` only)
