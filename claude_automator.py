#!/usr/bin/env python3
"""
Claude Automator - Automatically improve your codebase with Claude Code.

Zero dependencies beyond Python 3.10+ stdlib. Just download and run.

Usage:
    ./claude_automator.py --once -m improve_code    # Improve code quality
    ./claude_automator.py --once --northstar        # Iterate towards NORTHSTAR.md goals
    ./claude_automator.py --list-modes              # Show available modes
"""

import subprocess
import argparse
import time
import re
import os
import sys
import fcntl
import random
import string
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

try:
    from croniter import croniter
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False

# ============================================================================
# IMPROVEMENT MODES - Predefined prompts for each mode
# ============================================================================

IMPROVEMENT_MODES = {
    "fix_bugs": {
        "name": "Fix Bugs",
        "description": "Find and fix actual bugs in the code",
        "prompt": """Review the code in this repository for bugs.

Focus on finding ACTUAL BUGS only:
- Wrong method names (e.g., calling .load_node() when method is .get_node())
- Type mismatches that would cause runtime errors
- Undefined variables or attributes
- Logic errors that produce wrong results
- Race conditions and concurrency issues
- Memory leaks or resource handling issues

For each bug found:
1. Read the file to confirm the bug
2. Fix it with minimal changes
3. Commit with message: "fix: [description]"

If no bugs found, say "No bugs found" and do not make any changes.

Limit: Check at most 10 files, prioritize recently modified ones."""
    },

    "improve_code": {
        "name": "Improve Code Quality",
        "description": "Refactor and improve code readability, structure, and maintainability",
        "prompt": """Review the code in this repository for code quality improvements.

Focus on:
- Simplifying complex or convoluted logic
- Reducing code duplication (DRY principle)
- Improving variable and function naming
- Breaking down large functions into smaller, focused ones
- Applying appropriate design patterns
- Improving error handling and edge case coverage
- Making code more idiomatic for the language

DO NOT:
- Change working functionality
- Add features that don't exist
- Over-engineer simple solutions

For each improvement:
1. Read the file and understand the context
2. Make the improvement with clear, focused changes
3. Commit with message: "refactor: [description]"

Limit: Focus on the most impactful improvements. Check at most 5 files."""
    },

    "enhance_ux": {
        "name": "Enhance User Experience",
        "description": "Improve UI/UX, error messages, user feedback, and usability",
        "prompt": """Review the code in this repository for UX/UI improvements.

Focus on:
- Improving error messages to be more helpful and actionable
- Adding better user feedback (loading states, confirmations, progress)
- Improving CLI help text and documentation
- Making interfaces more intuitive
- Adding input validation with clear feedback
- Adding better logging for debugging
- Improving output formatting and readability

For each improvement:
1. Read the file and understand the user-facing context
2. Make the improvement
3. Commit with message: "ux: [description]"

Limit: Focus on the most impactful UX improvements. Check at most 5 files."""
    },

    "add_tests": {
        "name": "Add Tests",
        "description": "Add missing unit tests, integration tests, and improve test coverage",
        "prompt": """Review the code in this repository and add tests.

Focus on:
- Functions and classes that lack test coverage
- Critical business logic that should be tested
- Edge cases that aren't covered
- Error handling paths
- Integration between components

For each test added:
1. Identify untested or under-tested code
2. Write comprehensive tests following the project's testing patterns
3. Ensure tests are meaningful (not just for coverage)
4. Commit with message: "test: add tests for [component/function]"

Guidelines:
- Follow existing test patterns and frameworks in the project
- Use descriptive test names
- Include both positive and negative test cases
- Mock external dependencies appropriately

Limit: Add tests for at most 3 components/modules."""
    },

    "add_docs": {
        "name": "Add Documentation",
        "description": "Add or improve code documentation, comments, and docstrings",
        "prompt": """Review the code in this repository and improve documentation.

Focus on:
- Adding docstrings to public functions and classes
- Adding inline comments for complex logic
- Documenting function parameters and return values
- Adding type hints where missing
- Documenting edge cases and gotchas
- Adding module-level documentation

DO NOT:
- Add obvious comments (e.g., "# increment i" for i += 1)
- Over-document simple code
- Change any functionality

For each improvement:
1. Read the file and understand the code
2. Add clear, helpful documentation
3. Commit with message: "docs: add documentation for [component]"

Limit: Focus on the most important undocumented code. Check at most 5 files."""
    },

    "security": {
        "name": "Security Review",
        "description": "Find and fix security vulnerabilities",
        "prompt": """Review the code in this repository for security vulnerabilities.

Focus on OWASP Top 10 and common security issues:
- SQL injection vulnerabilities
- Cross-site scripting (XSS)
- Command injection
- Path traversal
- Insecure deserialization
- Hardcoded secrets or credentials
- Weak cryptographic practices
- Improper input validation
- Sensitive data exposure
- Missing authentication/authorization checks

For each vulnerability found:
1. Confirm the vulnerability exists
2. Fix it with minimal changes
3. Commit with message: "security: fix [vulnerability type]"

IMPORTANT: Do not introduce new dependencies unless absolutely necessary.

Limit: Check at most 10 files, prioritize user input handling and authentication."""
    },

    "performance": {
        "name": "Optimize Performance",
        "description": "Find and fix performance issues and bottlenecks",
        "prompt": """Review the code in this repository for performance improvements.

Focus on:
- Inefficient algorithms (O(n²) where O(n) is possible)
- Unnecessary database queries or API calls
- Missing caching opportunities
- Memory inefficiencies
- Blocking operations that could be async
- Unnecessary object creation in loops
- Inefficient string concatenation
- Missing indexes (if applicable)

DO NOT:
- Premature optimization of non-critical paths
- Micro-optimizations that hurt readability
- Changes without clear performance benefit

For each improvement:
1. Identify the performance issue
2. Fix it with clear, measurable improvement
3. Commit with message: "perf: [description]"

Limit: Focus on the most impactful optimizations. Check at most 5 files."""
    },

    "cleanup": {
        "name": "Code Cleanup",
        "description": "Remove dead code, unused imports, and clean up the codebase",
        "prompt": """Review the code in this repository for cleanup opportunities.

Focus on:
- Removing dead/unreachable code
- Removing unused imports and variables
- Removing commented-out code
- Fixing inconsistent formatting
- Removing duplicate code
- Cleaning up TODO/FIXME comments (fix or remove)
- Removing deprecated code paths

DO NOT:
- Change working functionality
- Remove code that might be used dynamically
- Remove comments that provide valuable context

For each cleanup:
1. Confirm the code is truly unused/dead
2. Remove or clean it up
3. Commit with message: "cleanup: [description]"

Limit: Focus on obvious cleanup opportunities. Check at most 10 files."""
    },

    "modernize": {
        "name": "Modernize Code",
        "description": "Update to modern language features and best practices",
        "prompt": """Review the code in this repository and modernize it.

Focus on:
- Using modern language features (async/await, destructuring, etc.)
- Replacing deprecated APIs with modern alternatives
- Using modern standard library functions
- Applying current best practices
- Updating to recommended patterns

DO NOT:
- Change working functionality
- Add new dependencies
- Make changes that require runtime/language version upgrades

For each modernization:
1. Identify outdated patterns
2. Update to modern equivalent
3. Commit with message: "modernize: [description]"

Limit: Focus on the most impactful modernizations. Check at most 5 files."""
    },

    "accessibility": {
        "name": "Improve Accessibility",
        "description": "Improve accessibility (a11y) for web/UI components",
        "prompt": """Review the code in this repository for accessibility improvements.

Focus on:
- Adding ARIA labels and roles
- Ensuring keyboard navigation
- Adding alt text for images
- Ensuring sufficient color contrast
- Adding screen reader support
- Semantic HTML usage
- Focus management
- Form accessibility

For each improvement:
1. Identify accessibility issues
2. Fix them following WCAG guidelines
3. Commit with message: "a11y: [description]"

Limit: Focus on the most impactful accessibility issues. Check at most 5 files."""
    },
}

# ============================================================================
# NORTHSTAR TEMPLATE - Default template for NORTHSTAR.md
# ============================================================================

NORTHSTAR_TEMPLATE = """# Project North Star

> This file defines the vision and goals for this project. The auto-improvement daemon
> will iterate towards these goals, making incremental progress with each run.
>
> Customize this file to match your project's specific needs and priorities.

## Vision

A high-quality, well-maintained codebase that is secure, performant, and easy to work with.

---

## Goals

### Code Quality
- [ ] Clean, readable code with consistent style
- [ ] No code duplication (DRY principle)
- [ ] Functions and classes have single responsibilities
- [ ] Meaningful variable and function names
- [ ] Appropriate use of design patterns

### Bug-Free
- [ ] No runtime errors or crashes
- [ ] All edge cases handled properly
- [ ] No logic errors in business logic
- [ ] No race conditions or concurrency issues

### Security
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] No command injection risks
- [ ] No hardcoded secrets or credentials
- [ ] Proper input validation on all user inputs
- [ ] Secure authentication and authorization

### Performance
- [ ] No obvious performance bottlenecks
- [ ] Efficient algorithms (no unnecessary O(n²) where O(n) works)
- [ ] Appropriate caching where beneficial
- [ ] No memory leaks

### Testing
- [ ] Unit tests for critical business logic
- [ ] Integration tests for key workflows
- [ ] Edge cases covered in tests
- [ ] Tests are meaningful, not just for coverage

### Documentation
- [ ] Public APIs and functions are documented
- [ ] Complex logic has explanatory comments
- [ ] README is up to date
- [ ] Type hints where applicable

### User Experience
- [ ] Clear, helpful error messages
- [ ] Good feedback for user actions
- [ ] Intuitive interfaces
- [ ] Accessible to all users (a11y)

### Code Health
- [ ] No dead or unused code
- [ ] No unused imports or variables
- [ ] No commented-out code blocks
- [ ] Modern language features used appropriately

---

## Priority Order

1. **Security** - Fix any security vulnerabilities first
2. **Bugs** - Fix any bugs that affect functionality
3. **Tests** - Add tests to prevent regressions
4. **Code Quality** - Improve maintainability
5. **Performance** - Optimize where it matters
6. **Documentation** - Help future developers
7. **UX** - Improve the user experience
8. **Cleanup** - Remove cruft and modernize

---

## Notes

- Focus on incremental improvements
- Don't over-engineer; keep it simple
- Prioritize impact over perfection
- Mark items as [x] when complete
"""

# ============================================================================
# PROMPT GENERATORS
# ============================================================================

def get_northstar_prompt(northstar_content: str) -> str:
    return f"""You are working towards the project's North Star vision. Read the goals below and make progress towards them.

## NORTHSTAR.md - Project Vision & Goals

{northstar_content}

---

## Your Task

1. **Analyze the current state**: Review the codebase to understand what has already been implemented and what's missing relative to the North Star goals.

2. **Identify the next steps**: Determine the most impactful improvements you can make RIGHT NOW to move closer to the vision. Focus on:
   - Unfinished features mentioned in the North Star
   - Quality improvements that align with the stated goals
   - Technical debt that blocks progress towards the vision
   - Missing functionality that's explicitly called out

3. **Make concrete progress**: Implement changes that move the project forward. This could include:
   - Adding new features
   - Improving existing code
   - Fixing issues that conflict with the vision
   - Refactoring to enable future goals

4. **Commit your changes**: For each improvement, commit with a descriptive message:
   - "feat: [description]" for new features
   - "fix: [description]" for fixes
   - "refactor: [description]" for refactoring
   - "docs: [description]" for documentation

## Guidelines

- **Be incremental**: Make meaningful but atomic changes. Don't try to do everything at once.
- **Prioritize impact**: Focus on changes that provide the most value towards the North Star.
- **Stay aligned**: Every change should clearly connect to a goal in NORTHSTAR.md.
- **Don't break things**: Ensure existing functionality continues to work.
- **Update progress**: If you complete a goal or milestone, you may update NORTHSTAR.md to reflect progress (mark items as done, add notes).

## Limits

- Focus on at most 3-5 related improvements per run
- Prioritize the most important/urgent goals first
- If a goal is too large, break it into smaller steps and complete one step

If the North Star goals are already fully achieved, say "North Star achieved! All goals complete." and suggest new goals if appropriate.
"""


def get_pr_review_prompt(pr_number: str) -> str:
    return f"""You are a code reviewer. Please review PR #{pr_number}.

1. First, get the PR details:
   - Run: gh pr view {pr_number}
   - Run: gh pr diff {pr_number}

2. Review the changes critically:
   - Are the changes correct and well-implemented?
   - Do they introduce any new bugs or issues?
   - Are the commit messages clear?
   - Is the code style consistent?

3. Make your decision and state it clearly:
   - If the changes look good, say "APPROVED" and explain why it's ready to merge
   - If changes are needed, say "CHANGES_REQUESTED" and list the specific issues

Do NOT use gh pr review command (it won't work for self-review).
Just output your decision clearly: either "APPROVED" or "CHANGES_REQUESTED" followed by your reasoning.

Be thorough but fair. Approve if the changes are net positive, even if not perfect.
When requesting changes, be SPECIFIC about what needs to be fixed."""


def get_fix_feedback_prompt(pr_number: str, feedback: str) -> str:
    return f"""A code reviewer has requested changes on PR #{pr_number}. Please address their feedback.

**Reviewer Feedback:**
{feedback}

**Your task:**
1. First, check out the PR branch and view the current code:
   - Run: gh pr checkout {pr_number}
   - Review the files mentioned in the feedback

2. Address EACH issue the reviewer mentioned:
   - Make the necessary code changes
   - Ensure you don't break existing functionality

3. Commit and push your fixes:
   - Commit with a clear message like "fix: address review feedback - [what you fixed]"
   - Push the changes: git push

4. Provide a summary of what you fixed.

IMPORTANT: Actually make the fixes, don't just describe them."""


def get_combined_prompt(mode_keys: list[str]) -> str:
    if len(mode_keys) == 1:
        return IMPROVEMENT_MODES[mode_keys[0]]["prompt"]

    prompts = []
    for key in mode_keys:
        if key in IMPROVEMENT_MODES:
            mode = IMPROVEMENT_MODES[key]
            prompts.append(f"## {mode['name']}\n\n{mode['prompt']}")

    return """You will perform multiple types of code improvements. Complete each section in order.

""" + "\n\n---\n\n".join(prompts) + """

---

IMPORTANT: Work through each section systematically. Make atomic commits for each improvement with appropriate prefixes (fix:, refactor:, ux:, test:, docs:, security:, perf:, cleanup:, modernize:, a11y:).
"""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_mode_list() -> str:
    lines = ["\nAvailable improvement modes:\n"]
    for key, mode in IMPROVEMENT_MODES.items():
        lines.append(f"  {key:20} - {mode['description']}")
    lines.append(f"\n  {'all':20} - Run all improvement modes sequentially")
    lines.append(f"  {'interactive':20} - Interactively select modes to run")
    lines.append(f"\n  {'northstar':20} - Iterate towards goals defined in NORTHSTAR.md")
    return "\n".join(lines)


def create_default_northstar(project_dir: Path) -> tuple[bool, str]:
    northstar_path = project_dir / "NORTHSTAR.md"
    if northstar_path.exists():
        return False, f"NORTHSTAR.md already exists at {northstar_path}"
    try:
        northstar_path.write_text(NORTHSTAR_TEMPLATE)
        return True, f"Created NORTHSTAR.md at {northstar_path}"
    except Exception as e:
        return False, f"Failed to create NORTHSTAR.md: {e}"


def load_northstar_prompt(project_dir: Path) -> tuple[str | None, str | None]:
    northstar_path = project_dir / "NORTHSTAR.md"
    if not northstar_path.exists():
        return None, f"NORTHSTAR.md not found in {project_dir}"
    try:
        content = northstar_path.read_text()
    except Exception as e:
        return None, f"Failed to read NORTHSTAR.md: {e}"
    if not content.strip():
        return None, "NORTHSTAR.md is empty"
    return get_northstar_prompt(content), None


def select_modes_interactive() -> list[str]:
    print("\n" + "=" * 60)
    print("Select improvement modes to run")
    print("=" * 60 + "\n")

    modes = list(IMPROVEMENT_MODES.keys())
    for i, key in enumerate(modes, 1):
        mode = IMPROVEMENT_MODES[key]
        print(f"  [{i:2}] {mode['name']:25} - {mode['description']}")

    print(f"\n  [ 0] All modes")
    print(f"  [ q] Quit")
    print("\nEnter mode numbers separated by space (e.g., '1 3 5'), or '0' for all:")

    try:
        choice = input("> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return []

    if choice == 'q' or choice == '':
        return []
    if choice == '0':
        return modes

    selected = []
    for num in choice.split():
        try:
            idx = int(num) - 1
            if 0 <= idx < len(modes):
                selected.append(modes[idx])
        except ValueError:
            if num in modes:
                selected.append(num)
    return selected

# ============================================================================
# CORE CLASSES
# ============================================================================

class LockFile:
    def __init__(self, path: Path):
        self.path = path
        self.fd = None

    def acquire(self) -> bool:
        try:
            self.fd = open(self.path, 'w')
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.fd.write(f"{os.getpid()}\n{datetime.now().isoformat()}\n")
            self.fd.flush()
            return True
        except (IOError, OSError):
            if self.fd:
                self.fd.close()
                self.fd = None
            return False

    def release(self):
        if self.fd:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                self.fd.close()
            except:
                pass
            finally:
                self.fd = None
        try:
            self.path.unlink()
        except:
            pass


class TelegramNotifier:
    def __init__(self, bot_token: str | None, chat_id: str | None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)

    def send(self, message: str) -> bool:
        if not self.enabled:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": "true"
            }).encode('utf-8')
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
            return False


class AutoReviewer:
    def __init__(self, project_dir: str, base_branch: str = "main",
                 auto_merge: bool = False, max_iterations: int = 3,
                 tg_bot_token: str | None = None, tg_chat_id: str | None = None,
                 review_prompt: str | None = None, modes: list[str] | None = None):
        self.project_dir = Path(project_dir).resolve()
        self.auto_merge = auto_merge
        self.base_branch = base_branch
        self.log_file = self.project_dir / "auto_review.log"
        self.lock_file = LockFile(self.project_dir / ".auto_review.lock")
        self.current_branch = None
        self.telegram = TelegramNotifier(tg_bot_token, tg_chat_id)
        self.max_iterations = max_iterations
        self.modes = modes or ["fix_bugs"]
        self.review_prompt = review_prompt or get_combined_prompt(self.modes)

    def get_mode_names(self) -> str:
        names = [IMPROVEMENT_MODES[m]["name"] for m in self.modes if m in IMPROVEMENT_MODES]
        return ", ".join(names) if names else "Unknown"

    def log(self, msg: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {msg}"
        print(log_line)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")

    def run_cmd(self, cmd: list[str], timeout: int = 60) -> tuple[bool, str]:
        try:
            result = subprocess.run(cmd, cwd=self.project_dir, capture_output=True, text=True, timeout=timeout)
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def run_claude(self, prompt: str, timeout: int = 3600) -> tuple[bool, str]:
        try:
            result = subprocess.run(["claude", "--print", prompt], cwd=self.project_dir, capture_output=True, text=True, timeout=timeout)
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Claude timed out"
        except Exception as e:
            return False, str(e)

    def generate_branch_name(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
        mode_prefix = self.modes[0].replace("_", "-") if self.modes else "review"
        return f"auto-{mode_prefix}/{timestamp}-{suffix}"

    def create_branch(self, branch_name: str) -> bool:
        self.run_cmd(["git", "checkout", self.base_branch])
        self.run_cmd(["git", "pull", "--rebase"])
        success, output = self.run_cmd(["git", "checkout", "-b", branch_name])
        if success:
            self.current_branch = branch_name
            self.log(f"Created branch: {branch_name}")
        return success

    def has_commits_ahead(self) -> bool:
        success, output = self.run_cmd(["git", "rev-list", "--count", f"{self.base_branch}..HEAD"])
        try:
            return success and int(output.strip()) > 0
        except:
            return False

    def create_pull_request(self, summary: str) -> str | None:
        if not self.has_commits_ahead():
            return None
        success, _ = self.run_cmd(["git", "push", "-u", "origin", self.current_branch], timeout=120)
        if not success:
            return None

        mode_names = self.get_mode_names()
        pr_title = f"Auto-improvement: {mode_names} ({datetime.now().strftime('%Y-%m-%d')})"
        pr_body = f"## Automated Code Improvement\n\n### Modes: {mode_names}\n\n### Summary\n{summary[:3000]}"

        success, output = self.run_cmd(["gh", "pr", "create", "--title", pr_title, "--body", pr_body, "--base", self.base_branch], timeout=60)
        if not success:
            return None

        for line in output.strip().split('\n'):
            if 'github.com' in line and '/pull/' in line:
                self.log(f"Created PR: {line.strip()}")
                return line.strip()
        return None

    def review_pr_with_claude(self, pr_url: str) -> tuple[bool, str, str]:
        pr_number = pr_url.rstrip('/').split('/')[-1]
        success, output = self.run_claude(get_pr_review_prompt(pr_number), timeout=600)
        output_lower = output.lower()
        approved = ("approved" in output_lower or "lgtm" in output_lower) and "changes_requested" not in output_lower
        match = re.search(r'CHANGES_REQUESTED[:\s]*(.+)', output, re.DOTALL | re.IGNORECASE)
        feedback = match.group(1).strip()[:1000] if match else '\n'.join(output.strip().split('\n')[-20:])
        return approved, output, feedback

    def fix_pr_feedback(self, pr_url: str, feedback: str, iteration: int) -> tuple[bool, str]:
        pr_number = pr_url.rstrip('/').split('/')[-1]
        return self.run_claude(get_fix_feedback_prompt(pr_number, feedback), timeout=1200)

    def merge_pr(self, pr_url: str) -> bool:
        pr_number = pr_url.rstrip('/').split('/')[-1]
        success, _ = self.run_cmd(["gh", "pr", "merge", pr_number, "--squash", "--delete-branch"], timeout=60)
        return success

    def cleanup_branch(self):
        if self.current_branch:
            self.run_cmd(["git", "checkout", self.base_branch])
            self.current_branch = None

    def run_once(self) -> bool:
        if not self.lock_file.acquire():
            self.log("Another review is already running, skipping")
            return False

        try:
            self.log("=" * 60)
            self.log("Starting review cycle")

            branch_name = self.generate_branch_name()
            if not self.create_branch(branch_name):
                self.telegram.send("⚠️ *Auto-Review Failed*\n\nCould not create branch.")
                return False

            self.log("Running Claude...")
            success, summary = self.run_claude(self.review_prompt, timeout=3600)
            if not success:
                self.cleanup_branch()
                self.telegram.send("⚠️ *Auto-Review Failed*\n\nClaude failed.")
                return False

            if not self.has_commits_ahead():
                self.log("No changes made")
                self.cleanup_branch()
                self.telegram.send("✅ *Auto-Review Complete*\n\nNo changes needed.")
                return True

            pr_url = self.create_pull_request(summary)
            if not pr_url:
                self.cleanup_branch()
                self.telegram.send("⚠️ *Auto-Review Failed*\n\nCould not create PR.")
                return False

            # Review-fix loop
            for iteration in range(1, self.max_iterations + 1):
                self.log(f"Review iteration {iteration}/{self.max_iterations}")
                approved, _, feedback = self.review_pr_with_claude(pr_url)

                if approved:
                    self.log(f"PR approved on iteration {iteration}")
                    if self.auto_merge:
                        self.merge_pr(pr_url)
                        self.telegram.send(f"✅ *Auto-Review Merged*\n🔗 {pr_url}")
                    else:
                        self.telegram.send(f"✅ *Auto-Review: PR Ready*\n🔗 {pr_url}")
                    break

                self.log(f"Changes requested, fixing...")
                self.telegram.send(f"🔄 Fixing feedback (iteration {iteration})")
                fix_success, _ = self.fix_pr_feedback(pr_url, feedback, iteration)
                if not fix_success:
                    self.telegram.send(f"⚠️ *Fixer Failed*\n🔗 {pr_url}")
                    break
            else:
                self.telegram.send(f"⚠️ *Max iterations reached*\n🔗 {pr_url}")

            self.cleanup_branch()
            self.log("Review cycle complete")
            self.log("=" * 60)
            return True

        finally:
            self.lock_file.release()

# ============================================================================
# SCHEDULING
# ============================================================================

def run_with_interval(reviewer: AutoReviewer, interval: int):
    print(f"Running every {interval}s. Press Ctrl+C to stop.")
    while True:
        start = time.time()
        reviewer.run_once()
        sleep_time = max(0, interval - (time.time() - start))
        if sleep_time > 0:
            time.sleep(sleep_time)


def run_with_cron(reviewer: AutoReviewer, cron_expr: str):
    if not HAS_CRONITER:
        print("Error: pip install croniter")
        sys.exit(1)
    print(f"Running on cron: {cron_expr}")
    cron = croniter(cron_expr, datetime.now())
    while True:
        next_run = cron.get_next(datetime)
        wait = (next_run - datetime.now()).total_seconds()
        if wait > 0:
            print(f"Next run at {next_run}")
            time.sleep(wait)
        reviewer.run_once()

# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Claude Automator - Automatically improve your codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=get_mode_list()
    )
    parser.add_argument("--interval", type=int, help="Run every N seconds")
    parser.add_argument("--cron", type=str, help="Cron expression")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--mode", "-m", type=str, action="append", dest="modes", help="Improvement mode")
    parser.add_argument("--northstar", "-n", action="store_true", help="Use NORTHSTAR.md")
    parser.add_argument("--init-northstar", action="store_true", help="Create NORTHSTAR.md template")
    parser.add_argument("--list-modes", action="store_true", help="List modes")
    parser.add_argument("--project-dir", type=str, default=os.getcwd(), help="Project directory")
    parser.add_argument("--auto-merge", action="store_true", help="Auto-merge approved PRs")
    parser.add_argument("--base-branch", type=str, default="main", help="Base branch")
    parser.add_argument("--max-iterations", type=int, default=3, help="Max review-fix iterations")
    parser.add_argument("--tg-bot-token", type=str, default=os.environ.get("TG_BOT_TOKEN"))
    parser.add_argument("--tg-chat-id", type=str, default=os.environ.get("TG_CHAT_ID"))
    parser.add_argument("--prompt-file", type=str, help="Custom prompt file")

    args = parser.parse_args()

    if args.list_modes:
        print(get_mode_list())
        sys.exit(0)

    if args.init_northstar:
        success, msg = create_default_northstar(Path(args.project_dir).resolve())
        print(msg)
        if success:
            print("\nNext: Edit NORTHSTAR.md, then run with --northstar")
        sys.exit(0 if success else 1)

    project_path = Path(args.project_dir).resolve()
    selected_modes = []
    review_prompt = None

    if args.northstar:
        args.modes = ["northstar"]

    if args.prompt_file:
        review_prompt = Path(args.prompt_file).read_text()
        selected_modes = ["custom"]
    elif args.modes:
        for mode in args.modes:
            if mode == "all":
                selected_modes = list(IMPROVEMENT_MODES.keys())
                break
            elif mode == "interactive":
                selected_modes = select_modes_interactive()
                if not selected_modes:
                    sys.exit(0)
                break
            elif mode == "northstar":
                prompt, error = load_northstar_prompt(project_path)
                if error:
                    print(f"Error: {error}\nRun: ./claude_automator.py --init-northstar")
                    sys.exit(1)
                review_prompt = prompt
                selected_modes = ["northstar"]
                break
            elif mode in IMPROVEMENT_MODES:
                selected_modes.append(mode)
            else:
                print(f"Unknown mode: {mode}")
                print(get_mode_list())
                sys.exit(1)
    else:
        selected_modes = select_modes_interactive()
        if not selected_modes:
            sys.exit(0)

    print("\n" + "=" * 60)
    print("Claude Automator")
    print("=" * 60)
    print(f"Project: {args.project_dir}")
    print(f"Branch: {args.base_branch}")
    if "northstar" in selected_modes:
        print("Mode: North Star")
    else:
        print(f"Modes: {', '.join(IMPROVEMENT_MODES[m]['name'] for m in selected_modes if m in IMPROVEMENT_MODES)}")
    print("=" * 60 + "\n")

    reviewer = AutoReviewer(
        project_dir=args.project_dir,
        auto_merge=args.auto_merge,
        base_branch=args.base_branch,
        tg_bot_token=args.tg_bot_token,
        tg_chat_id=args.tg_chat_id,
        max_iterations=args.max_iterations,
        review_prompt=review_prompt,
        modes=selected_modes
    )

    if args.once:
        sys.exit(0 if reviewer.run_once() else 1)
    elif args.interval:
        run_with_interval(reviewer, args.interval)
    elif args.cron:
        run_with_cron(reviewer, args.cron)
    else:
        print("Error: Specify --once, --interval, or --cron")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
