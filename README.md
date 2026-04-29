# dotfiles

Personal dotfiles + a [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces) for my custom skills. `SKILL.md` files follow the [open Agent Skills standard](https://agentskills.io/specification), so the skill bodies are portable across Claude Code, Codex, Gemini CLI, etc. — only the marketplace wrapper (`.claude-plugin/`) is Claude-Code-specific.

## Install in Claude Code

From inside Claude Code, add the marketplace and install the `personal` plugin:

```text
/plugin marketplace add k4black/dotfiles
/plugin install personal@kchernyshev-dotfiles
```

(Substitute `~/.dotfiles` for `k4black/dotfiles` if you cloned locally.)

Skills are then auto-discovered, namespaced as `personal:<skill-name>` (e.g. `/personal:anki-connect`).

To pull updates after I push new skills:

```text
/plugin marketplace update kchernyshev-dotfiles
```

## Install in Codex CLI

Codex reads skills directly from `~/.codex/skills/<skill-name>/SKILL.md`. Run the included installer to symlink every skill in `plugins/personal/skills/` into that directory:

```bash
~/.dotfiles/plugins/personal/install-codex.sh
```

Idempotent — re-run it after adding new skills. Override the destination with `CODEX_SKILLS_DIR=...` if needed.

## Use with other agents (Gemini CLI, Copilot CLI, etc.)

Point them at the skill directories directly: `~/.dotfiles/plugins/personal/skills/<skill-name>/`.

## Layout

```
.
├── .claude-plugin/
│   └── marketplace.json          # marketplace manifest (CC discovers plugins from here)
├── plugins/
│   └── personal/                 # one plugin, holds all my custom skills
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── install-codex.sh      # symlinks every skill into ~/.codex/skills
│       └── skills/
│           ├── anki-connect/     # Anki flashcard creator
│           ├── apple-notes/      # Apple Notes — safe edit/rename/reorganize
│           └── apple-reminders/  # Apple Reminders — add/view/complete
└── ...                           # zsh, git, macOS dotfiles
```

## Skills included

| Skill | Description |
|-------|-------------|
| `anki-connect` | Create and browse Anki flashcards via the [Anki-Connect](https://git.sr.ht/~foosoft/anki-connect) add-on (AnkiWeb code [2055492159](https://ankiweb.net/shared/info/2055492159)). Adapted from [doasfrancisco/anki-skill](https://github.com/doasfrancisco/anki-skill). |
| `apple-notes` | Read, rename, move, and reorganize Apple Notes safely — encodes the gotchas around link-URL stripping, the styled-`<div>` title, and `move-note` ID changes. Bundles export-to-markdown and import-from-markdown scripts. |
| `apple-reminders` | Add, view, complete, and organize items in Apple Reminders via AppleScript. Adapted from [densign01/reminders-skill](https://github.com/densign01/reminders-skill). |

## Adding a new skill

1. Create `plugins/personal/skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`).
2. Add any helper scripts under `plugins/personal/skills/<skill-name>/scripts/`.
3. Bump `version` in `plugins/personal/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, commit, push.
4. **Claude Code** (other machines): `/plugin marketplace update kchernyshev-dotfiles`.
5. **Codex** (any machine after `git pull`): re-run `plugins/personal/install-codex.sh` to symlink the new skill.
