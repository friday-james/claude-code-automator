#!/usr/bin/env python3
"""
Claude Automator - Automatically improve your codebase with Claude Code.

Zero dependencies beyond Python 3.10+ stdlib. Just download and run.

Usage:
    cook --once -m improve_code    # Improve code quality
    cook --once --northstar        # Iterate towards NORTHSTAR.md goals
    cook --yolo                    # YOLO mode: loop + create PR + auto-merge
    cook --list-modes              # Show available modes
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import random
import re
import string
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import IO

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

def get_goal_prompt(goal: str) -> str:
    """Generate a prompt for Claude to work towards a user-specified goal.

    Args:
        goal: The goal description provided by the user.

    Returns:
        A formatted prompt instructing Claude to analyze the codebase and make
        incremental progress towards the specified goal.
    """
    return f"""You are working towards a specific goal. Read the goal below and make progress towards it.

## Goal

{goal}

---

## Your Task

1. **Analyze the current state**: Review the codebase to understand what has already been implemented and what's needed to achieve the goal.

2. **Identify the next steps**: Determine the most impactful improvements you can make RIGHT NOW to move closer to the goal. Focus on:
   - Features or changes needed to achieve the goal
   - Quality improvements that align with the goal
   - Technical debt that blocks progress
   - Missing functionality

3. **Make concrete progress**: Implement changes that move the project forward. This could include:
   - Adding new features
   - Improving existing code
   - Fixing issues
   - Refactoring to enable the goal

4. **Commit your changes**: For each improvement, commit with a descriptive message:
   - "feat: [description]" for new features
   - "fix: [description]" for fixes
   - "refactor: [description]" for refactoring
   - "docs: [description]" for documentation

## Guidelines

- **Be incremental**: Make meaningful but atomic changes. Don't try to do everything at once.
- **Prioritize impact**: Focus on changes that provide the most value towards the goal.
- **Stay aligned**: Every change should clearly connect to the goal.
- **Don't break things**: Ensure existing functionality continues to work.

## Limits

- Focus on at most 3-5 related improvements per run
- If the goal is too large, break it into smaller steps and complete one step

If the goal is already fully achieved, say "Goal achieved!" and summarize what was done.
"""


def get_northstar_prompt(northstar_content: str) -> str:
    """Generate a prompt for Claude to work towards North Star goals.

    Args:
        northstar_content: The contents of the NORTHSTAR.md file defining project vision and goals.

    Returns:
        A formatted prompt instructing Claude to analyze the codebase and make
        incremental progress towards the defined goals.
    """
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
    """Generate a prompt for Claude to review a pull request.

    Args:
        pr_number: The PR number to review (e.g., "123").

    Returns:
        A formatted prompt instructing Claude to fetch PR details, review changes,
        and provide either APPROVED or CHANGES_REQUESTED decision.
    """
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
    """Generate a prompt for Claude to fix issues identified in PR review.

    Args:
        pr_number: The PR number that needs fixes (e.g., "123").
        feedback: The reviewer's feedback describing what needs to be fixed.

    Returns:
        A formatted prompt instructing Claude to checkout the PR branch,
        address each issue, commit fixes, and push changes.
    """
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
    """Generate a combined prompt for multiple improvement modes.

    Args:
        mode_keys: List of mode keys from IMPROVEMENT_MODES (e.g., ['fix_bugs', 'security']).

    Returns:
        For a single mode, returns that mode's prompt directly.
        For multiple modes, returns a combined prompt with all mode instructions
        separated by dividers and guidance for systematic execution.
    """
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
# INPUT VALIDATION
# ============================================================================

def validate_path(path_str: str, must_exist: bool = True, must_be_dir: bool = False) -> Path:
    """Validate and resolve a path, preventing path traversal attacks.

    Args:
        path_str: The path string to validate
        must_exist: If True, raise error if path doesn't exist
        must_be_dir: If True, raise error if path is not a directory

    Returns:
        Resolved absolute Path object

    Raises:
        ValueError: If path is invalid or doesn't meet requirements
    """
    try:
        path = Path(path_str).resolve()
    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid path '{path_str}': {e}")

    if must_exist and not path.exists():
        raise ValueError(f"Path does not exist: {path}")

    if must_be_dir and path.exists() and not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    return path


def validate_branch_name(branch: str) -> str:
    """Validate a git branch name for safety.

    Prevents shell injection and ensures valid git ref names.

    Args:
        branch: The branch name to validate

    Returns:
        The validated branch name

    Raises:
        ValueError: If branch name is invalid or potentially dangerous
    """
    if not branch or not branch.strip():
        raise ValueError("Branch name cannot be empty")

    branch = branch.strip()

    # Prevent shell metacharacters
    dangerous_chars = ['$', '`', '|', ';', '&', '>', '<', '\n', '\r', '\0']
    for char in dangerous_chars:
        if char in branch:
            raise ValueError(f"Branch name contains invalid character: {repr(char)}")

    # Git ref name rules (simplified)
    if branch.startswith('-') or branch.startswith('.'):
        raise ValueError("Branch name cannot start with '-' or '.'")

    if '..' in branch or branch.endswith('.lock') or branch.endswith('/'):
        raise ValueError("Invalid git branch name format")

    if len(branch) > 250:
        raise ValueError("Branch name too long (max 250 characters)")

    return branch


def validate_cron_expression(expr: str) -> str:
    """Validate a cron expression for basic safety.

    Args:
        expr: The cron expression to validate

    Returns:
        The validated cron expression

    Raises:
        ValueError: If expression is invalid or potentially dangerous
    """
    if not expr or not expr.strip():
        raise ValueError("Cron expression cannot be empty")

    expr = expr.strip()

    # Prevent shell metacharacters
    dangerous_chars = ['$', '`', '|', ';', '&', '>', '<', '\n', '\r', '\0']
    for char in dangerous_chars:
        if char in expr:
            raise ValueError(f"Cron expression contains invalid character: {repr(char)}")

    # Basic format check: should have 5 space-separated fields
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError("Cron expression must have exactly 5 fields")

    return expr


def validate_positive_int(value: int, name: str, max_value: int | None = None) -> int:
    """Validate that a value is a positive integer.

    Args:
        value: The value to validate
        name: The parameter name for error messages
        max_value: Optional maximum allowed value

    Returns:
        The validated value

    Raises:
        ValueError: If value is not positive or exceeds max_value
    """
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"{name} cannot exceed {max_value}, got {value}")
    return value


def check_claude_permissions(project_dir: Path) -> tuple[bool, str]:
    """Check if Claude Code permissions are properly configured.

    Args:
        project_dir: The project directory

    Returns:
        Tuple of (is_configured, message)
    """
    import json

    # Check project-level settings
    project_settings = project_dir / ".claude" / "settings.json"
    user_settings = Path.home() / ".claude" / "settings.json"

    for settings_path in [project_settings, user_settings]:
        if settings_path.exists():
            try:
                with open(settings_path) as f:
                    settings = json.load(f)
                    permissions = settings.get("permissions", {})
                    if permissions.get("defaultMode") == "bypassPermissions":
                        return True, f"Permissions configured in {settings_path}"
            except (json.JSONDecodeError, OSError):
                pass

    return False, """
⚠️  WARNING: Claude Code permissions not configured!

For seamless automation, you need to configure Claude Code to bypass permissions.

Without this, Claude will prompt for permissions during execution, which will
interrupt the automation. See: https://github.com/friday-james/let-claude-code#requirements
"""


def configure_claude_permissions(project_dir: Path, user_level: bool = False) -> tuple[bool, str]:
    """Configure Claude Code permissions to bypassPermissions mode.

    Args:
        project_dir: The project directory
        user_level: If True, configure at user level (~/.claude/settings.json),
                   otherwise at project level (.claude/settings.json)

    Returns:
        Tuple of (success, message)
    """
    import json

    if user_level:
        settings_path = Path.home() / ".claude" / "settings.json"
    else:
        settings_path = project_dir / ".claude" / "settings.json"

    try:
        # Create directory if it doesn't exist
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing settings or create new
        settings = {}
        if settings_path.exists():
            try:
                with open(settings_path) as f:
                    settings = json.load(f)
            except json.JSONDecodeError:
                # Invalid JSON, start fresh
                pass

        # Update permissions
        if "permissions" not in settings:
            settings["permissions"] = {}
        settings["permissions"]["defaultMode"] = "bypassPermissions"

        # Write back
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
            f.write('\n')  # Add trailing newline

        return True, f"✓ Configured permissions in {settings_path}"
    except (OSError, PermissionError) as e:
        return False, f"✗ Failed to write {settings_path}: {e}"


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

    print("\n  [ 0] All modes")
    print("  [ q] Quit")
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
    """File-based lock to prevent concurrent execution of the automator.

    Uses fcntl.flock for advisory locking. The lock file contains the PID
    and timestamp of the process that acquired the lock.

    Can be used as a context manager for automatic cleanup:
        with LockFile(path) as lock:
            if lock.acquired:
                # do work while holding the lock
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.fd: IO[str] | None = None
        self.acquired: bool = False

    def __enter__(self) -> "LockFile":
        """Context manager entry - attempts to acquire the lock."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - releases the lock."""
        self.release()

    def acquire(self) -> bool:
        """Attempt to acquire the lock. Returns True if successful."""
        try:
            self.fd = open(self.path, 'w')
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.fd.write(f"{os.getpid()}\n{datetime.now().isoformat()}\n")
            self.fd.flush()
            self.acquired = True
            return True
        except (IOError, OSError):
            if self.fd:
                self.fd.close()
                self.fd = None
            self.acquired = False
            return False

    def release(self) -> None:
        """Release the lock and remove the lock file."""
        if self.fd:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                self.fd.close()
            except OSError:
                pass
            finally:
                self.fd = None
                self.acquired = False
        try:
            self.path.unlink()
        except (FileNotFoundError, PermissionError):
            pass


class TelegramNotifier:
    """Sends notifications to Telegram when review cycles complete or fail."""

    def __init__(self, bot_token: str | None, chat_id: str | None) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)

    def send(self, message: str) -> bool:
        """Send a message to the configured Telegram chat. Returns True on success."""
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
        except (urllib.error.URLError, OSError) as e:
            print(f"Failed to send Telegram message: {e}")
            return False


class AutoReviewer:
    """Orchestrates automated code review cycles using Claude.

    Workflow:
    1. Creates a feature branch from base_branch
    2. Runs Claude with the configured improvement prompt
    3. Creates a PR if changes were made
    4. Has a reviewer Claude review the PR
    5. If changes requested, has a fixer Claude address them
    6. Loops until approved or max_iterations reached
    7. Optionally auto-merges approved PRs
    """

    def __init__(
        self,
        project_dir: str,
        base_branch: str = "main",
        auto_merge: bool = False,
        max_iterations: int = 3,
        tg_bot_token: str | None = None,
        tg_chat_id: str | None = None,
        review_prompt: str | None = None,
        modes: list[str] | None = None,
        think_level: str = "normal",
        create_pr: bool = False,
        work_branch: str | None = None,
        claude_flags: str | None = None,
        auto_yes: bool = False,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.auto_merge = auto_merge
        self.base_branch = base_branch
        self.log_file = self.project_dir / "auto_review.log"
        self.lock_file = LockFile(self.project_dir / ".auto_review.lock")
        self.current_branch: str | None = None
        self.telegram = TelegramNotifier(tg_bot_token, tg_chat_id)
        self.max_iterations = max_iterations
        self.modes = modes or ["fix_bugs"]
        self.review_prompt = review_prompt or get_combined_prompt(self.modes)
        self.session_cost = 0.0  # Cumulative cost across all runs
        self.session_id: str | None = None  # For continuing sessions
        self.think_level = think_level  # Thinking budget: normal, think, megathink, ultrathink
        self.create_pr = create_pr  # If True, create PR with review cycle
        self.work_branch = work_branch  # If set, checkout to this branch before working
        self.claude_flags = claude_flags  # Additional flags to pass to Claude CLI
        self.sessions_file = self.project_dir / ".cook_sessions.json"
        self.use_ai = False  # Enable auto-answering Claude questions via AI
        self.ai_model = "auto"  # Which AI model to use: auto, gpt-4o-mini, gemini-1.5-flash, etc.
        self.auto_yes = auto_yes  # Skip confirmation prompts

    def get_mode_names(self) -> str:
        """Get human-readable names for the configured modes."""
        names = [IMPROVEMENT_MODES[m]["name"] for m in self.modes if m in IMPROVEMENT_MODES]
        return ", ".join(names) if names else "Unknown"

    # ============================================================================
    # SESSION MANAGEMENT
    # ============================================================================

    def load_sessions(self) -> list[dict]:
        """Load saved sessions from file."""
        if not self.sessions_file.exists():
            return []
        try:
            with open(self.sessions_file) as f:
                data = json.load(f)
                return data.get("sessions", [])
        except (json.JSONDecodeError, OSError):
            return []

    def save_session(self, session_id: str, prompt: str, cost: float = 0.0) -> None:
        """Save a session to the sessions file."""
        sessions = self.load_sessions()

        # Remove if already exists
        sessions = [s for s in sessions if s.get("id") != session_id]

        # Create new session record
        session = {
            "id": session_id,
            "prompt_preview": prompt[:200].replace("\n", " ") + ("..." if len(prompt) > 200 else ""),
            "created_at": datetime.now().isoformat(),
            "cost": cost,
        }
        sessions.insert(0, session)  # Most recent first

        # Keep only last 10 sessions
        sessions = sessions[:10]

        try:
            with open(self.sessions_file, 'w') as f:
                json.dump({"sessions": sessions, "last_updated": datetime.now().isoformat()}, f, indent=2)
        except OSError as e:
            self.log(f"Warning: Failed to save session: {e}")

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from the sessions file."""
        sessions = self.load_sessions()
        original_count = len(sessions)
        sessions = [s for s in sessions if s.get("id") != session_id]

        if len(sessions) < original_count:
            try:
                with open(self.sessions_file, 'w') as f:
                    json.dump({"sessions": sessions, "last_updated": datetime.now().isoformat()}, f, indent=2)
                return True
            except OSError as e:
                self.log(f"Warning: Failed to delete session: {e}")
        return False

    def clear_all_sessions(self) -> bool:
        """Clear all saved sessions."""
        try:
            if self.sessions_file.exists():
                self.sessions_file.unlink()
            return True
        except OSError as e:
            self.log(f"Warning: Failed to clear sessions: {e}")
            return False

    def select_session(self) -> str | None:
        """Show session selection menu and return selected session ID."""
        sessions = self.load_sessions()

        if not sessions:
            print("\nNo saved sessions found.")
            return None

        print("\n" + "=" * 60)
        print("Select a session to resume")
        print("=" * 60)

        for i, session in enumerate(sessions, 1):
            created = session.get("created_at", "")[:19].replace("T", " ")
            prompt = session.get("prompt_preview", "Unknown")
            session_id = session.get("id", "")[:12]
            print(f"  [{i}] {created} | {session_id}... | {prompt[:40]}...")

        print("\n  [n] New session (start fresh)")
        print("  [c] Clear all sessions")
        print("  [q] Quit")
        print("\nEnter number to resume, or 'n'/'c'/'q':")

        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None

        if choice == 'q' or choice == '':
            return None
        elif choice == 'n':
            return None
        elif choice == 'c':
            if self.clear_all_sessions():
                print("All sessions cleared.")
            return None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(sessions):
                return sessions[idx].get("id")
        except ValueError:
            pass

        print("Invalid choice.")
        return None

    # ============================================================================
    # AI INTEGRATION - Auto-answer Claude questions with Gemini or GPT-5
    # ============================================================================

    def ask_ai(self, question: str, context: str = "") -> str | None:
        """Send a question to AI and get an answer."""
        # Determine which model to use
        model = self.ai_model

        # Auto mode: use cost-effective defaults
        if model == "auto":
            if os.environ.get("OPENAI_API_KEY"):
                model = "gpt-4o-mini"  # Cost-effective default
            elif os.environ.get("GEMINI_API_KEY"):
                model = "gemini-1.5-flash"  # Cost-effective default
            else:
                self.log("No AI API keys found (OPENAI_API_KEY or GEMINI_API_KEY)")
                return None

        # Route to appropriate provider
        if model.startswith("gpt-") or model.startswith("o1"):
            if not os.environ.get("OPENAI_API_KEY"):
                self.log(f"{model} requested but no OPENAI_API_KEY found")
                return None
            return self.ask_openai(question, context, model)
        elif model.startswith("gemini-"):
            if not os.environ.get("GEMINI_API_KEY"):
                self.log(f"{model} requested but no GEMINI_API_KEY found")
                return None
            return self.ask_gemini(question, context, model)
        else:
            self.log(f"Unknown AI model: {model}")
            return None

    def ask_openai(self, question: str, context: str = "", model: str = "gpt-4o-mini") -> str | None:
        """Send a question to OpenAI and get an answer."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None

        try:
            import urllib.request
            import urllib.error
            import json

            prompt = f"""You are helping an AI coding assistant (Claude) answer a question.

Context about the project/codebase:
{context if context else "General question - use your knowledge"}

Question from Claude:
{question}

Provide a clear, direct answer that Claude can use. Be concise but thorough."""

            # Use GPT-5.2 Responses API for GPT-5.2
            if model == "gpt-5.2":
                url = "https://api.openai.com/v1/responses"
                data = {
                    "model": model,
                    "input": prompt,
                    "reasoning": {
                        "effort": "xhigh"  # Maximum reasoning effort
                    },
                    "text": {
                        "verbosity": "medium"
                    },
                    "max_output_tokens": 65536
                }
            # Use Chat Completions API for other models
            else:
                url = "https://api.openai.com/v1/chat/completions"
                data = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 4096 if model == "gpt-4o-mini" else 16384
                }

            data_str = json.dumps(data).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=data_str,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))

                # Extract text based on API type
                if model == "gpt-5.2":
                    if result.get("output"):
                        answer = result["output"]
                        self.log(f"{model} answered: {answer[:100]}...")
                        return answer
                else:
                    if result.get("choices") and len(result["choices"]) > 0:
                        answer = result["choices"][0]["message"]["content"]
                        self.log(f"{model} answered: {answer[:100]}...")
                        return answer

                self.log(f"{model} response had no output: {result}")
                return None

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ""
            self.log(f"{model} HTTP {e.code} error: {error_body[:200]}")
            return None
        except urllib.error.URLError as e:
            self.log(f"{model} URL error: {e.reason}")
            return None
        except Exception as e:
            self.log(f"{model} API error: {type(e).__name__}: {e}")
            return None

    def ask_gemini(self, question: str, context: str = "", model: str = "gemini-1.5-flash") -> str | None:
        """Send a question to Gemini and get an answer."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None

        try:
            import urllib.request
            import urllib.error
            import json

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

            prompt = f"""You are helping an AI coding assistant (Claude) answer a question.

Context about the project/codebase:
{context if context else "General question - use your knowledge"}

Question from Claude:
{question}

Provide a clear, direct answer that Claude can use. Be concise but thorough."""

            # Set max tokens based on model
            if "flash" in model:
                max_tokens = 8192
            elif "1.5" in model:
                max_tokens = 8192
            else:  # gemini-3-pro
                max_tokens = 65536

            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": max_tokens,
                }
            }

            data_str = json.dumps(data).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=data_str,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))

                if result.get("candidates"):
                    answer = result["candidates"][0]["content"]["parts"][0]["text"]
                    self.log(f"{model} answered: {answer[:100]}...")
                    return answer
                else:
                    self.log(f"{model} response had no candidates: {result}")
                    return None

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ""
            self.log(f"{model} HTTP {e.code} error: {error_body[:200]}")
            return None
        except urllib.error.URLError as e:
            self.log(f"{model} URL error: {e.reason}")
            return None
        except Exception as e:
            self.log(f"{model} API error: {type(e).__name__}: {e}")
            return None

    def detect_question(self, text: str) -> bool:
        """Detect if text contains a question Claude is asking the user."""
        if not text:
            return False

        text = text.strip()

        # Claude asking for user input typically has these patterns:
        # 1. Ends with "?" (direct question)
        # 2. Contains question words with specific phrases
        # 3. Has patterns like "Would you like me to", "Should I", etc.

        if text.endswith("?"):
            return True

        # Check for common Claude input request patterns
        question_patterns = [
            r"what would you like me to",
            r"how should i proceed",
            r"would you like me to",
            r"should i continue",
            r"do you want me to",
            r"let me know what",
            r"please tell me",
            r"what would you like",
            r"should i make the changes",
            r"would you like to proceed",
            r"is this okay",
            r"is this correct",
            r"does this look right",
            r"are you happy with",
        ]

        for pattern in question_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def extract_question(self, text: str) -> str:
        """Extract the main question from Claude's output."""
        # Get the last line that seems like a question
        lines = text.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line and (line.endswith('?') or self.detect_question(line)):
                return line

        # If no clear question, return the last non-empty line
        for line in reversed(lines):
            line = line.strip()
            if line:
                return line

        return text[:200]

    def log(self, msg: str) -> None:
        """Log a message to stdout and the log file with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {msg}"
        print(log_line)
        try:
            with open(self.log_file, "a") as f:
                f.write(log_line + "\n")
        except PermissionError:
            print(f"Warning: Cannot write to log file {self.log_file} (permission denied)")
        except OSError as e:
            print(f"Warning: Cannot write to log file {self.log_file}: {e}")

    def run_cmd(self, cmd: list[str], timeout: int = 60) -> tuple[bool, str]:
        """Run a shell command and return (success, output)."""
        try:
            result = subprocess.run(
                cmd, cwd=self.project_dir, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout}s: {' '.join(cmd)}"
        except FileNotFoundError:
            return False, f"Command not found: {cmd[0]}"
        except PermissionError:
            return False, f"Permission denied: {cmd[0]}"
        except OSError as e:
            return False, f"Failed to run {cmd[0]}: {e}"

    def run_claude(self, prompt: str, timeout: int = 3600) -> tuple[bool, str]:
        """Run Claude CLI with the given prompt, streaming output in real-time with usage stats."""
        import atexit
        import tempfile
        import json


        # Append thinking keyword if not normal
        if self.think_level != "normal":
            prompt = f"{prompt}\n\n{self.think_level}"

        prompt_file = None

        def cleanup_temp_file() -> None:
            """Cleanup temp file on exit - registered with atexit for safety."""
            if prompt_file and os.path.exists(prompt_file):
                try:
                    os.unlink(prompt_file)
                except OSError:
                    pass

        try:
            # Write prompt to a temp file to avoid command line length limits
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name

            # Register cleanup with atexit in case of abnormal exit (SIGTERM, etc.)
            # Note: SIGKILL cannot be caught, but this handles most other cases
            atexit.register(cleanup_temp_file)

            try:
                # Build command
                cmd = ["claude", "--print", "--output-format", "stream-json", "--verbose"]
                if self.session_id:
                    cmd.extend(["--resume", self.session_id])

                # Add any additional claude flags specified by user
                if self.claude_flags:
                    # Expand ~ in arguments
                    expanded_flags = []
                    for flag in self.claude_flags.split():
                        expanded_flags.append(os.path.expanduser(flag))
                    cmd.extend(expanded_flags)


                # Run claude
                process = subprocess.Popen(
                    cmd,
                    cwd=self.project_dir,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )

                # For new sessions, send prompt via stdin
                # IMPORTANT: Do NOT close stdin here - Claude needs it open
                # to receive user input when asking questions (e.g., permission prompts)
                if not self.session_id:
                    try:
                        process.stdin.write(prompt)
                        process.stdin.flush()
                    except (BrokenPipeError, OSError) as e:
                        self.log(f"Failed to send prompt: {e}")
                        process.kill()
                        return False, f"Failed to start Claude: {e}"

                result_data = {}
                start_time = time.time()

                # Keep track of recent conversation for AI context
                conversation_history = []
                max_context_chars = 8000  # Limit context size

                while True:
                    if time.time() - start_time > timeout:
                        process.kill()
                        return False, "Claude timed out"

                    line = process.stdout.readline()
                    if not line:
                        if process.poll() is not None:
                            break
                        # Small sleep to avoid busy-waiting when no output available
                        time.sleep(0.01)
                        continue

                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        msg_type = data.get("type", "")

                        # Handle user input requests from Claude
                        # Note: This only works for resumed sessions where stdin is still open
                        if msg_type == "input_required":
                            question_text = data.get("message", {}).get("text", "") or data.get("description", "")
                            print(f"\n\033[93m🤖 Claude asking: {question_text[:100]}...\033[0m")

                            # Check if stdin is still open (only for resumed sessions)
                            if process.stdin.closed:
                                self.log("Warning: input_required received but stdin is closed (new session)")
                                print("\n\033[91m⚠️ Cannot answer - stdin closed\033[0m")
                                continue

                            if self.use_ai:
                                self.telegram.send(f"🤖 *Claude asking:*\n_{question_text[:200]}_")

                                # Build context from recent conversation
                                context_parts = [f"Project: {self.project_dir}"]
                                if conversation_history:
                                    context_parts.append("\nRecent conversation:")
                                    for msg in conversation_history[-5:]:  # Last 5 messages
                                        context_parts.append(f"- {msg[:200]}...")  # Truncate long messages
                                context = "\n".join(context_parts)

                                # Ask AI (GPT-5 or Gemini) with conversation context
                                answer = self.ask_ai(question_text, context)
                                if answer:
                                    print("\n\033[92m✨ AI answered\033[0m")
                                    self.telegram.send("✨ *AI auto-answered*")
                                    try:
                                        process.stdin.write(answer + "\n")
                                        process.stdin.flush()
                                    except (BrokenPipeError, OSError) as e:
                                        self.log(f"Failed to send answer: {e}")
                                else:
                                    # AI failed, use default "y" to proceed
                                    print("\n\033[91m⚠️ AI failed, proceeding with 'y'\033[0m")
                                    self.telegram.send("⚠️ *AI failed, proceeding with 'y'*")
                                    try:
                                        process.stdin.write("y\n")
                                        process.stdin.flush()
                                    except (BrokenPipeError, OSError) as e:
                                        self.log(f"Failed to send fallback answer: {e}")
                            else:
                                # Gemini not enabled, auto-proceed with 'y'
                                print("\n\033[90m→ Auto-answering 'y'\033[0m")
                                try:
                                    process.stdin.write("y\n")
                                    process.stdin.flush()
                                except (BrokenPipeError, OSError) as e:
                                    self.log(f"Failed to send answer: {e}")

                        # Print assistant messages in real-time and capture for context
                        if msg_type == "assistant" and "message" in data:
                            content = data["message"].get("content", [])
                            message_text = []
                            for block in content:
                                block_type = block.get("type")
                                if block_type == "text":
                                    text = block.get("text", "")
                                    message_text.append(text)
                                    print(text, end="", flush=True)
                                elif block_type == "thinking":
                                    # Print thinking content with visual distinction
                                    thinking_text = block.get("thinking", "")
                                    if thinking_text:
                                        print("\n\033[2m--- Thinking ---\033[0m", flush=True)
                                        for thought_line in thinking_text.split('\n'):
                                            print(f"\033[2m{thought_line}\033[0m", flush=True)
                                        print("\033[2m--- End Thinking ---\033[0m\n", flush=True)

                            # Add to conversation history for AI context
                            if message_text:
                                full_text = "".join(message_text)
                                conversation_history.append(full_text)
                                # Trim history if it gets too large
                                total_chars = sum(len(msg) for msg in conversation_history)
                                while total_chars > max_context_chars and len(conversation_history) > 1:
                                    removed = conversation_history.pop(0)
                                    total_chars -= len(removed)

                        # Capture final result with usage
                        if msg_type == "result":
                            result_data = data

                    except json.JSONDecodeError:
                        # Not JSON, print as-is
                        print(line, flush=True)

                success = process.returncode == 0

                # Print usage summary from result
                if result_data:
                    # Save session_id for continuing future runs
                    if "session_id" in result_data:
                        self.session_id = result_data["session_id"]
                        # Also save to sessions file for persistence across restarts
                        self.save_session(self.session_id, prompt, result_data.get("total_cost_usd", 0))

                    run_cost = result_data.get("total_cost_usd", 0)
                    self.session_cost += run_cost
                    usage = result_data.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    cache_read = usage.get("cache_read_input_tokens", 0)
                    cache_create = usage.get("cache_creation_input_tokens", 0)
                    duration = result_data.get("duration_ms", 0) / 1000

                    print(f"\n\n{'─'*60}")
                    print(f"📊 Tokens: {input_tokens + output_tokens:,} (in: {input_tokens:,}, out: {output_tokens:,})")
                    if cache_read or cache_create:
                        print(f"💾 Cache: read {cache_read:,}, created {cache_create:,}")
                    print(f"💰 This run: ${run_cost:.4f} | Session total: ${self.session_cost:.4f}")
                    print(f"⏱️  Time: {duration:.1f}s")
                    print("💡 Check quota: run 'claude' then type '/usage'")
                    print(f"{'─'*60}\n")

                # Close stdin if still open (after potential gemini answers)
                try:
                    if not process.stdin.closed:
                        process.stdin.close()
                except OSError:
                    pass

                # Get summary from git log
                if success:
                    _, log_output = self.run_cmd(["git", "log", "--oneline", f"{self.base_branch}..HEAD"])
                    summary = f"Changes made:\n{log_output}" if log_output.strip() else "Claude completed"
                else:
                    summary = "Claude failed"

                return success, summary
            finally:
                # Clean up temp file and unregister atexit handler
                if prompt_file and os.path.exists(prompt_file):
                    os.unlink(prompt_file)
                atexit.unregister(cleanup_temp_file)

        except FileNotFoundError:
            return False, "Claude CLI not found"
        except OSError as e:
            return False, f"Failed to run Claude: {e}"

    def generate_branch_name(self) -> str:
        """Generate a unique branch name based on mode and timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
        mode_prefix = self.modes[0].replace("_", "-") if self.modes else "review"
        return f"auto-{mode_prefix}/{timestamp}-{suffix}"

    def create_branch(self, branch_name: str) -> bool:
        """Create a new branch from base_branch and check it out."""
        self.run_cmd(["git", "checkout", self.base_branch])
        self.run_cmd(["git", "pull", "--rebase"])
        success, output = self.run_cmd(["git", "checkout", "-b", branch_name])
        if success:
            self.current_branch = branch_name
            self.log(f"Created branch: {branch_name}")
        return success

    def has_commits_ahead(self) -> bool:
        """Check if current branch has commits ahead of base branch."""
        success, output = self.run_cmd(["git", "rev-list", "--count", f"{self.base_branch}..HEAD"])
        try:
            return success and int(output.strip()) > 0
        except ValueError:
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
        branch_to_delete = self.current_branch
        success, _ = self.run_cmd(["gh", "pr", "merge", pr_number, "--squash", "--delete-branch"], timeout=60)
        if success and branch_to_delete:
            # Switch to base branch and delete local branch
            self.run_cmd(["git", "checkout", self.base_branch])
            self.run_cmd(["git", "branch", "-D", branch_to_delete])
            self.current_branch = None
            self.log(f"Deleted branch: {branch_to_delete}")
        return success

    def cleanup_branch(self):
        if self.current_branch:
            self.run_cmd(["git", "checkout", self.base_branch])
            self.current_branch = None

    def run_once(self) -> bool:
        # Check for stale lock file and prompt to remove
        if self.lock_file.path.exists():
            self.log(f"Found stale lock file: {self.lock_file.path}")
            print(f"\n⚠️  Found stale lock file: {self.lock_file.path}")

            if self.auto_yes:
                # Auto-remove with --yes flag
                try:
                    self.lock_file.path.unlink()
                    self.log("Lock file removed (auto-yes)")
                    print("Lock file removed (auto-yes)")
                except OSError as e:
                    self.log(f"Failed to remove lock file: {e}")
                    return False
            else:
                # Prompt user
                try:
                    response = input("Remove lock file and continue? [y/N]: ").strip().lower()
                    if response in ('y', 'yes'):
                        try:
                            self.lock_file.path.unlink()
                            self.log("Lock file removed")
                        except OSError as e:
                            self.log(f"Failed to remove lock file: {e}")
                            return False
                    else:
                        self.log("Skipping")
                        return False
                except (EOFError, KeyboardInterrupt):
                    print("\nAborted")
                    return False

        if not self.lock_file.acquire():
            self.log("Another review is already running, skipping")
            return False

        try:
            self.log("=" * 60)
            self.log("Starting review cycle")

            # Checkout to work branch if specified
            if self.work_branch:
                _, current = self.run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
                current = current.strip()
                if current != self.work_branch:
                    self.log(f"Checking out to {self.work_branch}...")
                    success, _ = self.run_cmd(["git", "checkout", self.work_branch])
                    if not success:
                        # Try to create the branch if it doesn't exist
                        success, _ = self.run_cmd(["git", "checkout", "-b", self.work_branch])
                        if not success:
                            self.log(f"Failed to checkout to {self.work_branch}")
                            self.telegram.send(f"⚠️ *Auto-Review Failed*\n\nCould not checkout to {self.work_branch}.")
                            return False
                else:
                    self.log(f"Already on {self.work_branch}")

            # Default: just run on the current branch without creating a new one
            if not self.create_pr:
                self.log("Running in no-PR mode (commits only)...")
                success, summary = self.run_claude(self.review_prompt, timeout=3600)
                if not success:
                    self.telegram.send("⚠️ *Auto-Review Failed*\n\nClaude failed.")
                    return False

                # Check what commits were made
                _, log_output = self.run_cmd(["git", "log", "--oneline", "-10"])
                if log_output.strip():
                    self.log(f"Recent commits:\n{log_output}")
                    self.telegram.send("✅ *Auto-Review Complete*\n\nCommits made on current branch.")
                else:
                    self.log("No changes made")
                    self.telegram.send("✅ *Auto-Review Complete*\n\nNo changes needed.")

                self.log("Review cycle complete")
                self.log("=" * 60)
                return True

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

                self.log("Changes requested, fixing...")
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

def run_loop(reviewer: AutoReviewer):
    print("Running continuously. Press Ctrl+C to stop.")
    run_count = 0
    while True:
        run_count += 1
        print(f"\n{'='*60}")
        print(f"Starting run #{run_count}")
        print(f"{'='*60}\n")

        start_time = time.time()
        reviewer.run_once()
        duration = time.time() - start_time

        # If run completed very quickly (< 30s), it likely failed or exited early
        # Add a delay to avoid rapid re-runs
        if duration < 30:
            delay = 10  # 10 second delay
            print(f"\n⚠️  Run completed quickly ({duration:.1f}s). Waiting {delay}s before next run...")
            time.sleep(delay)
        else:
            print(f"\nRun #{run_count} complete (took {duration:.1f}s). Starting next run immediately...")


def run_with_interval(reviewer: AutoReviewer, interval: int):
    print(f"Running every {interval}s. Press Ctrl+C to stop.")
    while True:
        start = time.time()
        reviewer.run_once()
        sleep_time = max(0, interval - (time.time() - start))
        if sleep_time > 0:
            print(f"\nWaiting {int(sleep_time)}s before next run...")
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
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"), override=False)

    parser = argparse.ArgumentParser(
        description="Claude Automator - Automatically improve your codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=get_mode_list()
    )
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--loop", action="store_true", help="Run continuously (start next immediately)")
    parser.add_argument("--interval", type=int, help="Run every N seconds")
    parser.add_argument("--cron", type=str, help="Cron expression")
    parser.add_argument("--mode", "-m", type=str, action="append", dest="modes", help="Improvement mode")
    parser.add_argument("--northstar", "-n", action="store_true", help="Use NORTHSTAR.md")
    parser.add_argument("--init-northstar", action="store_true", help="Create NORTHSTAR.md template")
    parser.add_argument("--goal", "-g", type=str, help="Work towards a specific goal")
    parser.add_argument("--list-modes", action="store_true", help="List modes")
    parser.add_argument("--auto-merge", action="store_true", help="Auto-merge approved PRs")
    parser.add_argument("--max-iterations", type=int, default=3, help="Max review-fix iterations")
    parser.add_argument("--tg-bot-token", type=str, default=os.environ.get("TG_BOT_TOKEN") or os.environ.get("TELEGRAM_API_ID") or os.environ.get("TELEGRAM_BOT_TOKEN"))
    parser.add_argument("--tg-chat-id", type=str, default=os.environ.get("TG_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID"))
    parser.add_argument("--prompt-file", type=str, help="Custom prompt file")
    parser.add_argument("--think", type=str, choices=["normal", "think", "megathink", "ultrathink"],
                        default="normal", help="Thinking budget level (default: normal)")
    parser.add_argument("--create-pr", nargs="?", const="main", metavar="BRANCH",
                        help="Create PR targeting BRANCH (default: main)")
    parser.add_argument("--branch", "-b", type=str,
                        help="Work on specified branch (checkout if needed)")
    parser.add_argument("-y", "--yes", action="store_true",
                        help="Skip confirmation prompt")
    parser.add_argument("--yolo", action="store_true",
                        help="YOLO mode: --loop --create-pr --auto-merge -y combined")
    parser.add_argument("--claude", type=str,
                        help="Additional flags to pass to Claude CLI (space-separated, ~ is expanded)")
    parser.add_argument("--resume", action="store_true",
                        help="Show session selection menu to resume a previous session")
    parser.add_argument("--clear-sessions", action="store_true",
                        help="Clear all saved sessions and exit")
    parser.add_argument("--auto-answer", action="store_true",
                        help="Auto-answer Claude's questions using AI. Requires OPENAI_API_KEY or GEMINI_API_KEY env var")
    parser.add_argument("--ai-model", type=str, default="auto",
                        help="AI model to use: auto (default: gpt-4o-mini or gemini-1.5-flash), gpt-4o-mini, gpt-4o, gpt-5.2, gemini-1.5-flash, gemini-1.5-pro, gemini-3-pro-preview")

    args = parser.parse_args()

    # YOLO mode sets all the aggressive flags
    if args.yolo:
        args.loop = True
        args.create_pr = args.create_pr or "main"
        args.auto_merge = True
        args.yes = True

    if args.list_modes:
        print(get_mode_list())
        sys.exit(0)

    # Use current directory as project path
    project_path = Path(os.getcwd()).resolve()

    # Validate inputs early to catch errors before doing any work
    try:
        if args.create_pr:
            validate_branch_name(args.create_pr)
        if args.branch:
            validate_branch_name(args.branch)
        if args.interval:
            validate_positive_int(args.interval, "interval", max_value=86400 * 7)  # Max 1 week
        if args.max_iterations:
            validate_positive_int(args.max_iterations, "max-iterations", max_value=10)
        if args.cron:
            validate_cron_expression(args.cron)
        if args.prompt_file:
            validate_path(args.prompt_file, must_exist=True)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if args.init_northstar:
        success, msg = create_default_northstar(project_path)
        print(msg)
        if success:
            print("\nNext: Edit NORTHSTAR.md, then run the automator (it will auto-detect)")
        sys.exit(0 if success else 1)
    selected_modes = []
    review_prompt = None

    if args.northstar:
        args.modes = ["northstar"]

    if args.goal:
        review_prompt = get_goal_prompt(args.goal)
        selected_modes = ["goal"]
    elif args.prompt_file:
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
        # Auto-detect NORTHSTAR.md if it exists
        northstar_path = project_path / "NORTHSTAR.md"
        if northstar_path.exists():
            prompt, error = load_northstar_prompt(project_path)
            if not error:
                print("Found NORTHSTAR.md, using North Star mode")
                review_prompt = prompt
                selected_modes = ["northstar"]
            else:
                selected_modes = select_modes_interactive()
                if not selected_modes:
                    sys.exit(0)
        else:
            selected_modes = select_modes_interactive()
            if not selected_modes:
                sys.exit(0)

    # Check Claude Code permissions configuration
    perms_configured, perms_msg = check_claude_permissions(project_path)
    if not perms_configured:
        print(perms_msg)
        if not args.yes:
            print("\nWould you like to configure this automatically?")
            print("  [p] Project-level (.claude/settings.json)")
            print("  [u] User-level (~/.claude/settings.json)")
            print("  [n] No, continue without configuring")
            try:
                response = input("\nChoice [p/u/N]: ").strip().lower()
                if response == 'p':
                    success, msg = configure_claude_permissions(project_path, user_level=False)
                    print(msg)
                    if not success:
                        print("Failed to configure. Continuing anyway...")
                elif response == 'u':
                    success, msg = configure_claude_permissions(project_path, user_level=True)
                    print(msg)
                    if not success:
                        print("Failed to configure. Continuing anyway...")
                elif response in ('n', ''):
                    print("Continuing without configuring...")
                    print("Note: Claude may prompt for permissions during execution.")
                else:
                    print("Invalid choice. Aborting.")
                    sys.exit(0)
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                sys.exit(0)
        else:
            print("\nProceeding anyway (--yes flag set)")
            print("Note: Claude may prompt for permissions during execution.\n")

    # Check for AI API keys if --auto-answer is requested
    use_ai = False
    if args.auto_answer:
        openai_key = os.environ.get("OPENAI_API_KEY")
        gemini_key = os.environ.get("GEMINI_API_KEY")

        if openai_key or gemini_key:
            use_ai = True
            model = args.ai_model
            if model == "auto":
                default_model = "gpt-4o-mini" if openai_key else "gemini-1.5-flash"
                print(f"✓ AI auto-answer enabled (using {default_model})")
                if openai_key and gemini_key:
                    print("  Both OpenAI and Gemini keys found - will fall back if primary fails")
            elif model.startswith("gpt-") or model.startswith("o1"):
                if openai_key:
                    print(f"✓ AI model: {model} (OpenAI)")
                else:
                    print(f"⚠️  {model} selected but OPENAI_API_KEY not found")
                    use_ai = False
            elif model.startswith("gemini-"):
                if gemini_key:
                    print(f"✓ AI model: {model} (Google)")
                else:
                    print(f"⚠️  {model} selected but GEMINI_API_KEY not found")
                    use_ai = False
        else:
            print("\n" + "=" * 60)
            print("🤖 AI Auto-Answer requested")
            print("=" * 60)
            print("To use --auto-answer, you need either:")
            print("  • OpenAI API key - https://platform.openai.com/api-keys")
            print("  • Gemini API key - https://aistudio.google.com/app/apikey")
            try:
                choice = input("\nEnter API key type [openai/gemini] (or press Enter to skip): ").strip().lower()
                if choice == "openai":
                    api_key = input("Enter your OpenAI API key: ").strip()
                    if api_key:
                        os.environ["OPENAI_API_KEY"] = api_key
                        use_ai = True
                        print("✓ OpenAI API key set")
                elif choice == "gemini":
                    api_key = input("Enter your Gemini API key: ").strip()
                    if api_key:
                        os.environ["GEMINI_API_KEY"] = api_key
                        use_ai = True
                        print("✓ Gemini API key set")
                else:
                    print("Skipping AI auto-answer.")
            except (EOFError, KeyboardInterrupt):
                print("\nSkipping AI auto-answer.")

    # Get current branch name
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path, capture_output=True, text=True, timeout=10
        )
        current_branch = result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        current_branch = "unknown"

    # Warn if committing directly to current branch
    if not args.create_pr and not args.yes:
        print("\n" + "=" * 60)
        print("⚠️  WARNING: Direct commit mode")
        print("=" * 60)
        print(f"Commits will be made directly to: {current_branch}")
        print("No PR will be created, no review cycle.")
        print("=" * 60)
        try:
            response = input("\nContinue? [y/N] ").strip().lower()
            if response not in ('y', 'yes'):
                print("Aborted.")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(0)

    print("\n" + "=" * 60)
    print("Claude Automator")
    print("=" * 60)
    print(f"Project: {project_path}")
    if args.branch:
        print(f"Work branch: {args.branch}" + (f" (current: {current_branch})" if current_branch != args.branch else " (current)"))
    else:
        print(f"Branch: {current_branch}")
    if "goal" in selected_modes:
        print(f"Mode: Goal - {args.goal[:50]}{'...' if len(args.goal) > 50 else ''}")
    elif "northstar" in selected_modes:
        print("Mode: North Star")
    else:
        print(f"Modes: {', '.join(IMPROVEMENT_MODES[m]['name'] for m in selected_modes if m in IMPROVEMENT_MODES)}")
    if args.think != "normal":
        print(f"Thinking: {args.think}")
    if args.create_pr:
        print(f"PR: Enabled → merge to {args.create_pr}")

    # Handle --clear-sessions first
    if args.clear_sessions:
        # Create temp reviewer just to access session methods
        temp_reviewer = AutoReviewer(project_dir=project_path)
        if temp_reviewer.clear_all_sessions():
            print("All sessions cleared.")
        else:
            print("Failed to clear sessions.")
        sys.exit(0)

    # Handle --resume: show session selection menu
    resume_session_id = None
    if args.resume:
        temp_reviewer = AutoReviewer(project_dir=project_path)
        resume_session_id = temp_reviewer.select_session()
        if resume_session_id is None:
            print("No session selected. Exiting.")
            sys.exit(0)
        print(f"\nResuming session: {resume_session_id[:12]}...")

    print("=" * 60 + "\n")

    reviewer = AutoReviewer(
        project_dir=project_path,
        auto_merge=args.auto_merge,
        base_branch=args.create_pr or "main",
        tg_bot_token=args.tg_bot_token,
        tg_chat_id=args.tg_chat_id,
        max_iterations=args.max_iterations,
        review_prompt=review_prompt,
        modes=selected_modes,
        think_level=args.think,
        create_pr=bool(args.create_pr),
        work_branch=args.branch,
        claude_flags=args.claude,
        auto_yes=args.yes,
    )

    # Enable AI auto-answer if requested
    if use_ai:
        reviewer.use_ai = True
        reviewer.ai_model = args.ai_model

    # If resuming a session, set the session_id
    if resume_session_id:
        reviewer.session_id = resume_session_id

    if args.once:
        sys.exit(0 if reviewer.run_once() else 1)
    elif args.loop:
        run_loop(reviewer)
    elif args.interval:
        run_with_interval(reviewer, args.interval)
    elif args.cron:
        run_with_cron(reviewer, args.cron)
    else:
        print("Error: Specify --once, --loop, --interval, or --cron")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
