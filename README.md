# Let Claude Code

### Set it. Forget it. Wake up to a better codebase.

```
You: cook --once -m fix_bugs
Claude: *improves your code*
Claude: *commits directly to your branch*
You: *reviews the changes*
```

---

## Install

```bash
# One-liner
pip install git+https://github.com/friday-james/let-claude-code.git

# Or with wget
wget -qO- https://raw.githubusercontent.com/friday-james/let-claude-code/main/install.sh | bash

# For cron support
pip install "let-claude-code[cron] @ git+https://github.com/friday-james/let-claude-code.git"
```

This installs the `cook` command.

---

## Quick Start

```bash
# Run once and improve code (commits to current branch)
cook --once -m improve_code

# With PR workflow (creates branch, PR, review cycle)
cook --once -m fix_bugs --create-pr

# Skip confirmation prompt
cook --once -m fix_bugs -y
```

By default, commits are made directly to your current branch. Use `--create-pr` to enable the full PR workflow with review cycles.

---

## What Happens

**Default mode (direct commits):**
```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│   YOU RUN:  cook --once -m fix_bugs                      │
│                                                          │
│   CLAUDE (Improver)                                     │
│   └── Reads your code, makes it better, commits         │
│                                                          │
│   DONE                                                  │
│   └── Changes committed to your current branch          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**With `--create-pr` (full PR workflow):**
```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│   YOU RUN:  cook --loop --create-pr                      │
│                                                          │
│   CLAUDE 1 (Improver)                                   │
│   └── Reads your code, makes it better, commits         │
│                                                          │
│   AUTO-CREATE PR                                        │
│   └── Pushes branch, opens pull request                 │
│                                                          │
│   CLAUDE 2 (Reviewer)                                   │
│   └── Reviews the PR critically                         │
│       ├── APPROVED → Merge                              │
│       └── CHANGES REQUESTED ↓                           │
│                                                          │
│   CLAUDE 3 (Fixer)                                      │
│   └── Addresses feedback, pushes fixes                  │
│                                                          │
│   LOOP FOREVER                                          │
│   └── Back to Claude 1, next improvement                │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Pick Your Mode

**Option 1: Define your vision (recommended)**

Create a `NORTHSTAR.md` file describing your ideal codebase:

```bash
cook --init-northstar   # Creates template
vim NORTHSTAR.md        # Customize your goals
cook --once              # Claude iterates towards it
```

**Option 2: Use preset modes**

```bash
cook --once -m fix_bugs      # Hunt and fix bugs
cook --once -m security      # Find vulnerabilities
cook --once -m add_tests     # Add missing tests
cook --once -m improve_code  # Refactor messy code
cook --once -m all           # Do everything
```

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

---

## NORTHSTAR.md

Your vision. Claude's mission.

```markdown
# Project North Star

## Vision
A bulletproof API that developers love.

## Goals

### Security (do these first)
- [ ] All user input is validated
- [ ] No SQL injection possible
- [ ] Auth on every protected route

### Reliability
- [ ] 100% of business logic has tests
- [ ] All errors have helpful messages

### Developer Experience
- [ ] Every public function is documented
- [ ] No dead code or unused imports
```

Claude reads this. Figures out what's not done. Makes progress. Every. Single. Run.

<details>
<summary><b>Full default template</b></summary>

```markdown
# Project North Star

## Vision
A high-quality, well-maintained codebase that is secure, performant, and easy to work with.

## Goals

### Code Quality
- [ ] Clean, readable code with consistent style
- [ ] No code duplication (DRY principle)
- [ ] Functions and classes have single responsibilities

### Bug-Free
- [ ] No runtime errors or crashes
- [ ] All edge cases handled properly

### Security
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] No hardcoded secrets or credentials
- [ ] Proper input validation

### Performance
- [ ] No obvious performance bottlenecks
- [ ] Efficient algorithms

### Testing
- [ ] Unit tests for critical business logic
- [ ] Edge cases covered in tests

### Documentation
- [ ] Public APIs documented
- [ ] Complex logic has comments

### Code Health
- [ ] No dead or unused code
- [ ] No commented-out code blocks

## Priority Order
1. Security
2. Bugs
3. Tests
4. Code Quality
5. Performance
6. Documentation
7. Cleanup
```

</details>

---

## All The Ways

```bash
# Run once (default: commits to current branch)
cook --once -m improve_code

# Run once with PR workflow (merge to main)
cook --once -m improve_code --create-pr

# Run once with PR to specific branch
cook --once -m improve_code --create-pr develop

# Skip confirmation prompt
cook --once -m fix_bugs -y

# Loop forever (with PR workflow)
cook --loop --create-pr

# Run every hour
cook --interval 3600 --create-pr

# Run on cron (requires: pip install let-claude-code[cron])
cook --cron "0 */4 * * *" --create-pr

# Auto-merge when approved
cook --loop --create-pr --auto-merge

# Get Telegram notifications
export TG_BOT_TOKEN="your_token"
export TG_CHAT_ID="your_chat_id"
cook --loop --create-pr
```

---

## Usage Tracking

After each run, you see:

```
────────────────────────────────────────────────────────────
📊 Tokens: 15,234 (in: 12,500, out: 2,734)
💾 Cache: read 14,640, created 3,461
💰 This run: $0.0314 | Session total: $0.1542
⏱️  Time: 6.1s
💡 Check quota: run 'claude' then type '/usage'
────────────────────────────────────────────────────────────
```

Sessions are continued automatically - subsequent runs reuse cached context and burn fewer tokens.

---

## All Options

| Option | What it does |
|:-------|:-------------|
| `--once` | Run once and exit |
| `--loop` | Run forever (start next immediately) |
| `--interval N` | Run every N seconds |
| `--cron "expr"` | Run on cron schedule |
| `-m, --mode MODE` | Improvement mode (repeatable) |
| `-n, --northstar` | Force NORTHSTAR.md mode |
| `--init-northstar` | Create NORTHSTAR.md template |
| `--list-modes` | Show all available modes |
| `--create-pr [BRANCH]` | Create PR targeting BRANCH (default: `main`) |
| `--auto-merge` | Auto-merge approved PRs |
| `--max-iterations N` | Max review-fix rounds (default: `3`) |
| `-y, --yes` | Skip confirmation prompt |
| `--think LEVEL` | Thinking budget: `normal`, `think`, `megathink`, `ultrathink` |
| `--llm PROVIDER` | LLM CLI to use: `claude` or `codex` |
| `--codex` | Use Codex CLI (same as `--llm codex`) |

---

## Extended Thinking

Use `--think` to give Claude more thinking time for complex tasks:

```bash
cook --once --think ultrathink    # Maximum thinking budget
cook --once --think megathink     # 10,000 token budget
cook --once --think think         # 4,000 token budget
cook --once                       # Normal (default)
```

| Level | Budget | Best For |
|:------|:-------|:---------|
| `normal` | Default | Routine improvements |
| `think` | 4,000 tokens | Moderate complexity |
| `megathink` | 10,000 tokens | Complex refactoring |
| `ultrathink` | Maximum | Architectural decisions, deep analysis |

---

## Concurrent Workers

Run multiple Claudes in parallel, each on its own worktree.

```bash
# Run on specific directories
cook-concurrent -d src lib scripts -p "Fix bugs"

# With PR workflow
cook-concurrent -d src lib --create-pr --auto-merge

# With extended thinking
cook-concurrent -d src -m security --think ultrathink

# Use Codex CLI
cook-concurrent -d src --codex
```

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│   YOU RUN:  cook-concurrent -d src lib --create-pr       │
│                                                          │
│   Worker 1 (src/)              Worker 2 (lib/)           │
│   ┌────────────────┐           ┌────────────────┐        │
│   │ Branch         │           │ Branch         │        │
│   │ Improve        │           │ Improve        │        │
│   │ Create PR      │           │ Create PR      │        │
│   │ Review         │           │ Review         │        │
│   │ Fix feedback   │           │ Fix feedback   │        │
│   │ Merge          │           │ Merge          │        │
│   └────────────────┘           └────────────────┘        │
│          ↓                            ↓                  │
│   ┌─────────────────────────────────────────────────┐   │
│   │     2 PRs created, reviewed, and merged         │   │
│   │        Each scoped to its own directory         │   │
│   └─────────────────────────────────────────────────┘   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Config file for different tasks per directory:**

```json
[
    {"directory": "src", "prompt": "Fix bugs in the core modules"},
    {"directory": "lib", "modes": ["security", "fix_bugs"]},
    {"directory": "scripts", "prompt": "Add type hints"}
]
```

```bash
cook-concurrent -c workers.json --create-pr --auto-merge
```

| Option | What it does |
|:-------|:-------------|
| `-d, --directories` | Directories to work on |
| `-p, --prompt` | Prompt for all workers |
| `-m, --mode` | Improvement mode (repeatable) |
| `-c, --config` | JSON config file |
| `--create-pr [BRANCH]` | Create PR targeting BRANCH (default: `main`) |
| `--auto-merge` | Auto-merge approved PRs |
| `-y, --yes` | Skip confirmation prompt |
| `--think LEVEL` | Thinking budget |
| `--dry-run` | Preview without executing |

---

## Requirements

- **Python 3.10+**
- **[Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)** or **Codex CLI** installed
- **[GitHub CLI](https://cli.github.com/)** (`gh`) installed (for `--create-pr`)
- **Git repo** with remote

**Recommended:** Enable auto-delete branches in your GitHub repo:
**Settings → General → Pull Requests → ✓ Automatically delete head branches**

---

## Philosophy

Your codebase decays. Every day. Tech debt accumulates. Tests don't get written. Docs go stale.

You're too busy shipping features to fix it.

What if your codebase could improve itself?

That's this. One command. Claude works while you don't. Code gets better.

```bash
cook --once -m improve_code
```

**Let Claude code.**

---

<p align="center">
  <b>Stop maintaining. Start automating.</b>
  <br><br>
  <i>Let Claude Code.</i>
</p>
