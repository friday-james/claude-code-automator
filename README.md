# Claude Automator

### Your codebase improves itself while you sleep.

```
You: *goes to bed*
Claude Automator: *fixes 47 bugs, adds tests, removes dead code*
You: *wakes up to mass approved PRs*
```

---

## What is this?

A single Python script that lets **Claude continuously improve your codebase**.

- Pick a goal (fix bugs, add tests, improve security...)
- Claude makes changes, creates a PR
- A *second* Claude reviews the PR
- If changes needed, a *third* Claude fixes them
- Loop until approved
- You wake up to better code

**Zero dependencies. Just download and run.**

---

## Quick Start

```bash
# Download it
curl -O https://raw.githubusercontent.com/friday-james/claude-code-automator/main/claude_automator.py
chmod +x claude_automator.py

# Let Claude improve your code
./claude_automator.py --once -m improve_code
```

That's it. Go grab coffee.

---

## The Modes

Pick what you want Claude to focus on:

| Mode | What it does |
|:-----|:-------------|
| `fix_bugs` | Hunts down actual bugs and fixes them |
| `improve_code` | Refactors messy code into clean code |
| `enhance_ux` | Better error messages, better feedback |
| `add_tests` | Adds tests for untested code |
| `add_docs` | Documents the undocumented |
| `security` | Finds and fixes vulnerabilities |
| `performance` | Makes slow things fast |
| `cleanup` | Removes dead code and cruft |
| `modernize` | Updates old patterns to new ones |
| `accessibility` | Makes UI accessible to everyone |

```bash
# Run one mode
./claude_automator.py --once -m security

# Run multiple modes
./claude_automator.py --once -m fix_bugs -m add_tests

# Run ALL the modes
./claude_automator.py --once -m all

# Can't decide? Interactive picker
./claude_automator.py --once -m interactive
```

---

## North Star Mode

**The real power move.**

Instead of predefined modes, define your own vision. Create a `NORTHSTAR.md` file that describes what your perfect codebase looks like. Claude will iterate towards it, run after run.

```bash
# Generate the template
./claude_automator.py --init-northstar

# Edit NORTHSTAR.md with your goals, then:
./claude_automator.py --once --northstar
```

### Example NORTHSTAR.md

```markdown
# Project North Star

## Vision
A bulletproof API that developers love.

## Goals

### Security (do these first)
- [ ] All user input is validated
- [ ] No SQL injection possible
- [ ] Auth on every protected route
- [ ] No secrets in code

### Reliability
- [ ] 100% of business logic has tests
- [ ] All errors have helpful messages
- [ ] No unhandled edge cases

### Developer Experience
- [ ] Every public function is documented
- [ ] Consistent code style everywhere
- [ ] No dead code or unused imports
```

Claude reads this, figures out what's not done yet, and makes progress. Every run gets you closer.

<details>
<summary><b>Full default template (click to expand)</b></summary>

```markdown
# Project North Star

> This file defines the vision and goals for this project. The auto-improvement daemon
> will iterate towards these goals, making incremental progress with each run.

## Vision

A high-quality, well-maintained codebase that is secure, performant, and easy to work with.

---

## Goals

### Code Quality
- [ ] Clean, readable code with consistent style
- [ ] No code duplication (DRY principle)
- [ ] Functions and classes have single responsibilities
- [ ] Meaningful variable and function names

### Bug-Free
- [ ] No runtime errors or crashes
- [ ] All edge cases handled properly
- [ ] No logic errors in business logic

### Security
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] No command injection risks
- [ ] No hardcoded secrets or credentials
- [ ] Proper input validation on all user inputs

### Performance
- [ ] No obvious performance bottlenecks
- [ ] Efficient algorithms (no unnecessary O(n²) where O(n) works)
- [ ] Appropriate caching where beneficial

### Testing
- [ ] Unit tests for critical business logic
- [ ] Integration tests for key workflows
- [ ] Edge cases covered in tests

### Documentation
- [ ] Public APIs and functions are documented
- [ ] Complex logic has explanatory comments
- [ ] README is up to date

### User Experience
- [ ] Clear, helpful error messages
- [ ] Good feedback for user actions
- [ ] Intuitive interfaces

### Code Health
- [ ] No dead or unused code
- [ ] No unused imports or variables
- [ ] No commented-out code blocks

---

## Priority Order

1. **Security** - Fix vulnerabilities first
2. **Bugs** - Fix broken functionality
3. **Tests** - Prevent regressions
4. **Code Quality** - Improve maintainability
5. **Performance** - Optimize where it matters
6. **Documentation** - Help future developers
7. **UX** - Improve the experience
8. **Cleanup** - Remove cruft

---

## Notes

- Focus on incremental improvements
- Don't over-engineer; keep it simple
- Prioritize impact over perfection
- Mark items as [x] when complete
```

</details>

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   1. YOU                                                        │
│      └── Pick a mode (or define NORTHSTAR.md)                  │
│                                                                 │
│   2. IMPROVER CLAUDE                                           │
│      └── Makes changes, commits them                           │
│                                                                 │
│   3. AUTO-CREATE PR                                            │
│      └── Pushes branch, opens pull request                     │
│                                                                 │
│   4. REVIEWER CLAUDE                                           │
│      ├── Reviews the PR critically                             │
│      ├── APPROVED → Done (or auto-merge)                       │
│      └── CHANGES REQUESTED → Go to step 5                      │
│                                                                 │
│   5. FIXER CLAUDE                                              │
│      └── Addresses feedback, pushes fixes                      │
│                                                                 │
│   6. LOOP                                                       │
│      └── Back to step 4 (up to 3 iterations)                   │
│                                                                 │
│   7. NOTIFY                                                     │
│      └── Telegram notification with results                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Three Claudes. Arguing with each other. Making your code better.

---

## Run It Your Way

```bash
# Once (great for testing)
./claude_automator.py --once -m improve_code

# Every hour
./claude_automator.py --interval 3600 -m fix_bugs

# On a cron schedule (requires: pip install croniter)
./claude_automator.py --cron "0 */4 * * *" --northstar

# Auto-merge when approved (living dangerously)
./claude_automator.py --once --northstar --auto-merge

# Get Telegram notifications
export TG_BOT_TOKEN="your_bot_token"
export TG_CHAT_ID="your_chat_id"
./claude_automator.py --once --northstar
```

---

## All Options

| Option | What it does |
|:-------|:-------------|
| `--once` | Run once and exit |
| `--interval N` | Run every N seconds |
| `--cron "expr"` | Run on cron schedule |
| `-m, --mode MODE` | Improvement mode (repeatable) |
| `-n, --northstar` | Use NORTHSTAR.md goals |
| `--init-northstar` | Create NORTHSTAR.md template |
| `--list-modes` | Show all available modes |
| `--project-dir PATH` | Project directory (default: `.`) |
| `--base-branch NAME` | Base branch for PRs (default: `main`) |
| `--auto-merge` | Auto-merge approved PRs |
| `--max-iterations N` | Max review-fix rounds (default: `3`) |
| `--prompt-file PATH` | Custom prompt file |
| `--tg-bot-token` | Telegram bot token |
| `--tg-chat-id` | Telegram chat ID |

---

## Requirements

- **Python 3.10+** (no pip install needed)
- **[Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)** installed and authenticated
- **[GitHub CLI](https://cli.github.com/)** (`gh`) installed and authenticated
- **Git repo** with remote configured

Optional: `pip install croniter` for cron scheduling

---

## Philosophy

Your codebase should get better over time, not worse.

But you're busy. You have features to ship. Tech debt accumulates. Tests don't get written. Docs go stale.

What if your codebase could improve itself?

That's Claude Automator. Define where you want to go. Let Claude do the work. Wake up to PRs that make your code better.

**Set it. Forget it. Ship it.**

---

## License

MIT

---

<p align="center">
  <i>Stop maintaining. Start automating.</i>
</p>
