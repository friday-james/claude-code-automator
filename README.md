# Auto-Improvement Daemon

A tool that spawns Claude Code to automatically improve your codebase. Choose from predefined improvement modes or define your own goals with a `NORTHSTAR.md` file.

## Quick Start

```bash
# Create a NORTHSTAR.md with default goals
python auto_review.py --init-northstar

# Run improvements towards your North Star
python auto_review.py --once --northstar

# Or pick specific improvement modes
python auto_review.py --once -m improve_code -m add_tests
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

### Create a NORTHSTAR.md

```bash
# Generate a default template
python auto_review.py --init-northstar

# Or create your own NORTHSTAR.md manually
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
- [ ] Error messages are helpful to developers

### Nice to Have
- [ ] Rate limiting on public endpoints
- [ ] Request/response logging
```

### Run North Star Mode

```bash
# Iterate towards your goals
python auto_review.py --once --northstar

# Or equivalently
python auto_review.py --once -m northstar
```

Claude will:
1. Read your `NORTHSTAR.md`
2. Analyze the current codebase
3. Make incremental progress towards uncompleted goals
4. Optionally update `NORTHSTAR.md` to mark completed items

---

## Usage Examples

### Single Improvement Mode

```bash
python auto_review.py --once -m fix_bugs
python auto_review.py --once -m add_tests
python auto_review.py --once -m security
```

### Multiple Modes

```bash
python auto_review.py --once -m fix_bugs -m improve_code -m add_tests
```

### All Modes

```bash
python auto_review.py --once -m all
```

### Interactive Selection

```bash
python auto_review.py --once -m interactive
# Or just omit the mode to get prompted:
python auto_review.py --once
```

### List Available Modes

```bash
python auto_review.py --list-modes
```

### Scheduled Runs

```bash
# Every hour
python auto_review.py --interval 3600 --northstar

# Every 4 hours via cron
pip install croniter
python auto_review.py --cron "0 */4 * * *" --northstar
```

### Auto-Merge Approved PRs

```bash
python auto_review.py --once --northstar --auto-merge
```

### With Telegram Notifications

```bash
export TG_BOT_TOKEN="your_bot_token"
export TG_CHAT_ID="your_chat_id"
python auto_review.py --once --northstar
```

---

## All Options

| Option | Description |
|--------|-------------|
| `--once` | Run once and exit |
| `--interval N` | Run every N seconds |
| `--cron "expr"` | Run on cron schedule |
| `-m, --mode MODE` | Improvement mode (can specify multiple) |
| `-n, --northstar` | Use North Star mode (shortcut for `-m northstar`) |
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
│                     AUTO-IMPROVEMENT FLOW                    │
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

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- [GitHub CLI](https://cli.github.com/) (`gh`) installed and authenticated
- Git repository with remote configured

### Optional

- `croniter` for cron scheduling: `pip install croniter`

---

## Telegram Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and get the token
2. Get your chat ID from [@userinfobot](https://t.me/userinfobot)
3. Start a chat with your bot (send `/start`)
4. Set environment variables or pass as arguments

---

## License

MIT
