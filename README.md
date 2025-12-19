# Claude Automator

Automatically improve your codebase with Claude Code. Choose from predefined improvement modes or define your own goals with a `NORTHSTAR.md` file.

## Installation

No installation required. Just download the script:

```bash
# Download to your project
curl -O https://raw.githubusercontent.com/friday-james/claude-code-automator/main/claude_automator.py
chmod +x claude_automator.py

# Or clone the repo
git clone https://github.com/friday-james/claude-code-automator.git
```

## Quick Start

```bash
# Navigate to your project
cd /path/to/your/project

# Run an improvement mode
./claude_automator.py --once -m improve_code

# Or create a NORTHSTAR.md and iterate towards your goals
./claude_automator.py --init-northstar
./claude_automator.py --once --northstar
```

---

## Features

- **Multiple improvement modes** - Bug fixes, code quality, UX, tests, security, and more
- **North Star mode** - Define your own goals in `NORTHSTAR.md` and iterate towards them
- **Two-Claude review** - A separate Claude instance reviews PRs before merging
- **Review-fix loop** - If reviewer requests changes, fixer Claude addresses them
- **Telegram notifications** - Get notified when reviews complete
- **Flexible scheduling** - Run once, at intervals, or via cron

---

## Improvement Modes

| Mode | Description |
|------|-------------|
| `fix_bugs` | Find and fix actual bugs in the code |
| `improve_code` | Refactor and improve code readability, structure, and maintainability |
| `enhance_ux` | Improve UI/UX, error messages, user feedback, and usability |
| `add_tests` | Add missing unit tests, integration tests, and improve test coverage |
| `add_docs` | Add or improve code documentation, comments, and docstrings |
| `security` | Find and fix security vulnerabilities |
| `performance` | Find and fix performance issues and bottlenecks |
| `cleanup` | Remove dead code, unused imports, and clean up the codebase |
| `modernize` | Update to modern language features and best practices |
| `accessibility` | Improve accessibility (a11y) for web/UI components |

### Special Modes

| Mode | Description |
|------|-------------|
| `all` | Run all improvement modes sequentially |
| `interactive` | Interactively select which modes to run |
| `northstar` | Iterate towards goals defined in NORTHSTAR.md |

---

## NORTHSTAR.md - Define Your Goals

The **North Star** mode lets you define your own project vision and goals. Claude will automatically iterate towards them with each run.

```bash
# Create a template
claude-automator --init-northstar

# Edit NORTHSTAR.md to customize your goals, then run:
claude-automator --once --northstar
```

### Example NORTHSTAR.md

```markdown
# Project North Star

## Vision
Build a fast, secure, and user-friendly API.

## Goals

### Must Have
- [ ] All endpoints have input validation
- [ ] Authentication on protected routes
- [ ] Unit tests for business logic

### Should Have
- [ ] Response time < 100ms for all endpoints
- [ ] API documentation with examples

### Nice to Have
- [ ] Rate limiting on public endpoints
```

---

## Usage Examples

```bash
# Single mode
./claude_automator.py --once -m fix_bugs

# Multiple modes
./claude_automator.py --once -m fix_bugs -m add_tests -m security

# All modes
./claude_automator.py --once -m all

# Interactive selection
./claude_automator.py --once -m interactive

# North Star mode
./claude_automator.py --once --northstar

# List available modes
./claude_automator.py --list-modes

# Run every hour
./claude_automator.py --interval 3600 -m improve_code

# Run on cron schedule (requires: pip install croniter)
./claude_automator.py --cron "0 */4 * * *" --northstar

# Auto-merge approved PRs
./claude_automator.py --once --northstar --auto-merge

# With Telegram notifications
export TG_BOT_TOKEN="your_bot_token"
export TG_CHAT_ID="your_chat_id"
./claude_automator.py --once --northstar
```

---

## All Options

| Option | Description |
|--------|-------------|
| `--once` | Run once and exit |
| `--interval N` | Run every N seconds |
| `--cron "expr"` | Run on cron schedule |
| `-m, --mode MODE` | Improvement mode (can specify multiple) |
| `-n, --northstar` | Iterate towards NORTHSTAR.md goals |
| `--init-northstar` | Create a default NORTHSTAR.md template |
| `--list-modes` | List all available modes |
| `--project-dir PATH` | Project directory (default: current dir) |
| `--base-branch NAME` | Base branch for PRs (default: main) |
| `--auto-merge` | Automatically merge approved PRs |
| `--max-iterations N` | Max review-fix rounds (default: 3) |
| `--prompt-file PATH` | Custom prompt file (overrides modes) |
| `--tg-bot-token TOKEN` | Telegram bot token |
| `--tg-chat-id ID` | Telegram chat ID |

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                       CLAUDE AUTOMATOR                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. SELECT MODE                                             │
│     ├── Predefined modes (fix_bugs, add_tests, etc.)       │
│     ├── North Star (reads NORTHSTAR.md goals)              │
│     └── Custom prompt file                                  │
│                                                             │
│  2. CREATE BRANCH                                           │
│     └── auto-{mode}/YYYYMMDD-HHMMSS-xxxx                   │
│                                                             │
│  3. IMPROVEMENT CLAUDE                                      │
│     └── Makes changes based on selected mode/goals         │
│                                                             │
│  4. CREATE PR                                               │
│     └── If changes were made                               │
│                                                             │
│  5. REVIEWER CLAUDE                                         │
│     ├── Separate Claude instance reviews the PR            │
│     ├── APPROVED → Merge (if --auto-merge)                 │
│     └── CHANGES REQUESTED → Fixer Claude addresses         │
│                                                             │
│  6. LOOP (up to --max-iterations)                          │
│     └── Repeat review-fix cycle until approved             │
│                                                             │
│  7. NOTIFY                                                  │
│     └── Send Telegram notification with results            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Requirements

- Python 3.10+ (no external dependencies)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- [GitHub CLI](https://cli.github.com/) (`gh`) installed and authenticated
- Git repository with remote configured

Optional: `pip install croniter` for cron scheduling support

---

## License

MIT
