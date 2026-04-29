# dotfiles

Personal dotfiles + a Claude Code plugin marketplace for my custom skills.

## Claude Code skills

This repo doubles as a [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces).

### Install

From inside Claude Code (clone this repo first or point to its GitHub URL):

```text
/plugin marketplace add ~/.dotfiles
/plugin install personal@kchernyshev-dotfiles
```

Or directly from GitHub:

```text
/plugin marketplace add kchernyshev/dotfiles
/plugin install personal@kchernyshev-dotfiles
```

After installing, skills are auto-discovered. They're namespaced as `personal:<skill-name>` (e.g. `/personal:anki`).

### Update

```text
/plugin marketplace update kchernyshev-dotfiles
```

### Use with other agents (Codex, Gemini CLI, Copilot CLI)

`SKILL.md` files follow the [open Agent Skills standard](https://agentskills.io/specification), so the skill bodies are portable. The Claude Code plugin wrapper (`.claude-plugin/`) is CC-specific. To use a skill with another agent, point it at:

```
~/.dotfiles/plugins/personal/skills/<skill-name>/
```

## Layout

```
.
├── .claude-plugin/
│   └── marketplace.json          # marketplace manifest (CC discovers plugins from here)
├── plugins/
│   └── personal/                 # one plugin, holds all my custom skills
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── skills/
│           └── anki-connect/     # first skill — Anki flashcard creator
│               ├── SKILL.md
│               └── scripts/
└── ...                           # zsh, git, macOS dotfiles
```

## Skills included

| Skill | Description |
|-------|-------------|
| `anki-connect` | Create and browse Anki flashcards via the [Anki-Connect](https://git.sr.ht/~foosoft/anki-connect) add-on (AnkiWeb code [2055492159](https://ankiweb.net/shared/info/2055492159)). Adapted from [doasfrancisco/anki-skill](https://github.com/doasfrancisco/anki-skill). |

## Adding a new skill

1. Create `plugins/personal/skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`).
2. Add any helper scripts under `plugins/personal/skills/<skill-name>/scripts/`.
3. Bump `version` in `plugins/personal/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
4. Run `/plugin marketplace update kchernyshev-dotfiles` in any session that already has the marketplace installed.
