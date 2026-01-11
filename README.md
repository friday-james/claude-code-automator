# Let Claude Code

### Set it. Forget it. Wake up to a better codebase.

```
You: cook --once -m fix_bugs
Claude: *improves your code*
Claude: *commits directly to your branch*
You: *reviews the changes*
```

## The Fundamental Flaw (And How We Fix It)

**Claude Code's Problem**: It's interactive. It stops and asks you questions. It waits for permission. It can't run unattended.

**Our Solution**: Full autonomy.

- **🤖 AI Consultation Loop**: GPT-5.2 or Gemini reviews Claude's work and sets the next goal. True multi-AI collaboration.
- **💬 AI Auto-Answer**: Claude asks a question? AI answers it instantly. Choose from cost-effective to premium models.
- **⚡ Permission Bypass**: Configured once, runs forever without prompts.
- **🔄 Loop & Schedule**: Run continuously or on cron. Walk away. Come back to improvements.
- **🚀 PR Automation**: Creates branches, opens PRs, reviews them, merges approved ones.

**The result?** Claude Code becomes a true autonomous agent that improves your codebase 24/7 without human intervention—at a cost you control.

---

## Install

```bash
pip install let-claude-code
```

Or from source:

```bash
pip install git+https://github.com/friday-james/let-claude-code.git

# Or with wget
wget -qO- https://raw.githubusercontent.com/friday-james/let-claude-code/main/install.sh | bash
```

Update:

```bash
pip install --upgrade let-claude-code
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

**Option 3: Specify a goal directly**

```bash
cook --once --goal "Add user authentication with JWT"
cook --loop -g "Refactor the API to use async/await"
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

# YOLO mode: loop + create PR + auto-merge + skip prompts
cook --yolo -m improve_code

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

## AI Consultation Loop

Let AI consultants (GPT-5.2, Gemini) guide Claude's work autonomously. The AI consultant reviews what Claude does and sets the next goal, creating a true multi-AI collaboration loop.

**Setup:**

```bash
# Option 1: OpenAI (GPT models)
export OPENAI_API_KEY=sk-...

# Option 2: Google (Gemini models)
export GEMINI_API_KEY=...

# Or add to .env file
echo "OPENAI_API_KEY=sk-..." >> .env
echo "GEMINI_API_KEY=..." >> .env
```

**Usage:**

```bash
# AI-driven loop (AI consultant determines when complete)
cook --auto-answer -g "Improve code quality across the project"

# Choose specific AI model
cook --auto-answer --ai-model gpt-4o-mini      # Cheapest OpenAI (default)
cook --auto-answer --ai-model gpt-4o           # Balanced
cook --auto-answer --ai-model gpt-5.2          # Premium reasoning
cook --auto-answer --ai-model gemini-1.5-flash # Cheapest Gemini
cook --auto-answer --ai-model gemini-1.5-pro   # Balanced Gemini

# Still works with explicit loop flags
cook --loop --auto-answer -m fix_bugs          # Loop forever
cook --once --auto-answer -g "Fix bug"         # Run once only

# YOLO mode (includes auto-answer)
cook --yolo -m improve_code
```

**How the AI Consultation Loop works:**

1. **Iteration 1**: Claude works on your initial goal (e.g., "Improve code quality")
2. **AI Review**: GPT-5.2/Gemini reviews Claude's commits and sets next goal (e.g., "Add docstrings to math_utils.py")
3. **Iteration 2**: Claude works on AI's goal → AI reviews → AI sets new goal (e.g., "Add type hints")
4. **Iteration 3**: Claude adds type hints → AI reviews → "GOAL_ACHIEVED: YES" → Loop exits ✓

**Example output:**

```
[Run #1]
🔮 Asking gpt-5.2 to review Claude's work and set next goal...
✨ gpt-5.2's Review:
GOAL_ACHIEVED: NO
CONTINUE: YES
NEXT_GOAL:
Add comprehensive docstrings to all functions in math_utils.py.
Use Google-style format with descriptions, args, and returns sections.

📋 Next goal set by AI:
Add comprehensive docstrings to all functions in math_utils.py...

[Run #2]
Claude adds docstrings → gpt-5.2 reviews → sets new goal...

[Run #3]
✅ Goal Achieved!
gpt-5.2 confirmed the task is complete.
```

**AI Auto-Answer (for Claude's questions):**

When enabled, AI also auto-answers any questions Claude asks during execution:

1. Claude encounters a question (e.g., "Should I create a new file or edit existing?")
2. Automator sends question + recent conversation context to AI
3. AI reasons through the question and provides an answer
4. Answer is sent back to Claude automatically
5. Claude continues without human intervention

**Available Models:**

| Model | Provider | Cost | Speed | Best For |
|:------|:---------|:-----|:------|:---------|
| `gpt-4o-mini` | OpenAI | $ | Fast | Default - great balance of cost/quality |
| `gpt-4o` | OpenAI | $$ | Medium | More complex decisions |
| `gpt-5.2` | OpenAI | $$$ | Slow | Maximum reasoning for critical decisions |
| `gemini-1.5-flash` | Google | $ | Fast | Default - cost-effective fallback |
| `gemini-1.5-pro` | Google | $$ | Medium | More complex reasoning |
| `gemini-3-pro-preview` | Google | $$$ | Slow | Premium Google model |

**Cost Comparison:**

- **gpt-4o-mini**: ~$0.15 per 1M input tokens, $0.60 per 1M output (cheapest OpenAI)
- **gpt-4o**: ~$2.50 per 1M input tokens, $10 per 1M output
- **gpt-5.2**: ~$10 per 1M input tokens, $40 per 1M output (premium reasoning)
- **gemini-1.5-flash**: ~$0.075 per 1M input tokens, $0.30 per 1M output (cheapest)
- **gemini-1.5-pro**: ~$1.25 per 1M input tokens, $5 per 1M output

💡 **Tip:** Start with `auto` mode (default) for cost-effective operation. Upgrade to premium models only when needed.

**Get API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- Gemini: https://aistudio.google.com/app/apikey

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
| `--yolo` | YOLO mode: `--loop --create-pr --auto-merge -y` combined |
| `--interval N` | Run every N seconds |
| `--cron "expr"` | Run on cron schedule |
| `-m, --mode MODE` | Improvement mode (repeatable) |
| `-n, --northstar` | Force NORTHSTAR.md mode |
| `-g, --goal GOAL` | Work towards a specific goal |
| `--init-northstar` | Create NORTHSTAR.md template |
| `--list-modes` | Show all available modes |
| `--create-pr [BRANCH]` | Create PR targeting BRANCH (default: `main`) |
| `-b, --branch BRANCH` | Work on specified branch (checkout if needed) |
| `--auto-merge` | Auto-merge approved PRs (deletes branch after) |
| `--max-iterations N` | Max review-fix rounds (default: `3`) |
| `-y, --yes` | Skip confirmation prompt |
| `--think LEVEL` | Thinking budget: `normal`, `think`, `megathink`, `ultrathink` |
| `--auto-answer` | Enable AI consultation loop + auto-answer (requires API key). Auto-loops until AI determines task is complete. |
| `--ai-model MODEL` | AI consultant model: `auto`, `gpt-4o-mini`, `gpt-4o`, `gpt-5.2`, `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-3-pro-preview` |
| `--claude "FLAGS"` | Additional flags to pass to Claude CLI |
| `--resume` | Resume from a previous session |
| `--clear-sessions` | Clear all saved sessions |

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

# YOLO mode
cook-concurrent -d src lib --yolo

# With extended thinking
cook-concurrent -d src -m security --think ultrathink
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
| `--yolo` | YOLO mode: `--create-pr --auto-merge -y` combined |
| `-y, --yes` | Skip confirmation prompt |
| `--think LEVEL` | Thinking budget |
| `--dry-run` | Preview without executing |

---

## Requirements

- **Python 3.10+**
- **[Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)** installed
- **[GitHub CLI](https://cli.github.com/)** (`gh`) installed (for `--create-pr`)
- **Git repo** with remote

**Recommended:** Enable auto-delete branches in your GitHub repo:
**Settings → General → Pull Requests → ✓ Automatically delete head branches**

**Required:** Configure Claude Code to allow all permissions.

On first run, `cook` will offer to configure this automatically. You can also manually add this to `.claude/settings.json` (project-level) or `~/.claude/settings.json` (user-level):
```json
{
  "permissions": {
    "defaultMode": "bypassPermissions"
  }
}
```

This is required because `cook` invokes `claude` programmatically and cannot pass the `--dangerously-skip-permissions` flag.

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
