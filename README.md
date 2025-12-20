# Let Claude Code

### Set it. Forget it. Wake up to a better codebase.

```
You: ./claude_automator.py --loop
Claude: *improves your code while you sleep*
Claude: *creates PR*
Claude: *reviews its own PR*
Claude: *fixes review feedback*
Claude: *repeats forever*
You: *wakes up to mass merged PRs*
```

---

## One Command

```bash
curl -O https://raw.githubusercontent.com/friday-james/let-claude-code/main/claude_automator.py
chmod +x claude_automator.py
./claude_automator.py --loop
```

That's it. Claude improves your code forever.

---

## What Happens

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│   YOU RUN:  ./claude_automator.py --loop                │
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

Three Claudes. Arguing with each other. Making your code better. Forever.

---

## Pick Your Mode

**Option 1: Define your vision (recommended)**

Create a `NORTHSTAR.md` file describing your ideal codebase:

```bash
./claude_automator.py --init-northstar   # Creates template
vim NORTHSTAR.md                          # Customize your goals
./claude_automator.py --loop              # Claude iterates towards it
```

**Option 2: Use preset modes**

```bash
./claude_automator.py --loop -m fix_bugs      # Hunt and fix bugs
./claude_automator.py --loop -m security      # Find vulnerabilities
./claude_automator.py --loop -m add_tests     # Add missing tests
./claude_automator.py --loop -m improve_code  # Refactor messy code
./claude_automator.py --loop -m all           # Do everything
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
# The main event - loop forever
./claude_automator.py --loop

# Run once (for testing)
./claude_automator.py --once -m improve_code

# Run every hour
./claude_automator.py --interval 3600

# Run on cron (requires: pip install croniter)
./claude_automator.py --cron "0 */4 * * *"

# Auto-merge when approved (living dangerously)
./claude_automator.py --loop --auto-merge

# Get Telegram notifications
export TG_BOT_TOKEN="your_token"
export TG_CHAT_ID="your_chat_id"
./claude_automator.py --loop
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
| `--loop` | **Run forever** (start next immediately) |
| `--once` | Run once and exit |
| `--interval N` | Run every N seconds |
| `--cron "expr"` | Run on cron schedule |
| `-m, --mode MODE` | Improvement mode (repeatable) |
| `-n, --northstar` | Force NORTHSTAR.md mode |
| `--init-northstar` | Create NORTHSTAR.md template |
| `--list-modes` | Show all available modes |
| `--project-dir PATH` | Project directory (default: `.`) |
| `--base-branch NAME` | Base branch for PRs (default: `main`) |
| `--auto-merge` | Auto-merge approved PRs |
| `--max-iterations N` | Max review-fix rounds (default: `3`) |
| `--think LEVEL` | Thinking budget: `normal`, `think`, `megathink`, `ultrathink` |

---

## Extended Thinking

Use `--think` to give Claude more thinking time for complex tasks:

```bash
./claude_automator.py --loop --think ultrathink    # Maximum thinking budget
./claude_automator.py --loop --think megathink     # 10,000 token budget
./claude_automator.py --loop --think think         # 4,000 token budget
./claude_automator.py --loop                       # Normal (default)
```

| Level | Budget | Best For |
|:------|:-------|:---------|
| `normal` | Default | Routine improvements |
| `think` | 4,000 tokens | Moderate complexity |
| `megathink` | 10,000 tokens | Complex refactoring |
| `ultrathink` | Maximum | Architectural decisions, deep analysis |

**When to use `--think ultrathink`:**
- Complex architectural decisions
- Performance optimization challenges
- Security vulnerability analysis
- Large-scale refactoring

The thinking keywords are Claude Code magic words that trigger extended reasoning. Reserve higher levels for tasks where thorough analysis justifies the additional compute cost.

---

## Requirements

- **Python 3.10+** (zero dependencies)
- **[Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)** installed
- **[GitHub CLI](https://cli.github.com/)** (`gh`) installed
- **Git repo** with remote

---

## Philosophy

Your codebase decays. Every day. Tech debt accumulates. Tests don't get written. Docs go stale.

You're too busy shipping features to fix it.

What if your codebase could improve itself?

That's this. One command. Claude works while you don't. PRs appear. Code gets better.

```bash
./claude_automator.py --loop
```

**Let Claude code.**

---

<p align="center">
  <b>Stop maintaining. Start automating.</b>
  <br><br>
  <i>Let Claude Code.</i>
</p>
