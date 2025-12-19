#!/usr/bin/env python3
"""Unit tests for claude_automator.py.

Tests focus on critical functionality: input validation, security boundaries,
and core logic. Run with: python -m pytest test_claude_automator.py -v
or simply: python test_claude_automator.py
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from claude_automator import (
    validate_path,
    validate_branch_name,
    validate_cron_expression,
    validate_positive_int,
    get_combined_prompt,
    get_northstar_prompt,
    get_pr_review_prompt,
    get_fix_feedback_prompt,
    load_northstar_prompt,
    create_default_northstar,
    IMPROVEMENT_MODES,
    NORTHSTAR_TEMPLATE,
    LockFile,
    TelegramNotifier,
    AutoReviewer,
)


class TestValidatePath(unittest.TestCase):
    """Tests for validate_path function."""

    def test_valid_existing_path(self):
        """Should return resolved Path for existing paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_path(tmpdir, must_exist=True, must_be_dir=True)
            self.assertIsInstance(result, Path)
            self.assertTrue(result.exists())
            self.assertTrue(result.is_dir())

    def test_valid_existing_file(self):
        """Should return resolved Path for existing files."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        try:
            result = validate_path(path, must_exist=True, must_be_dir=False)
            self.assertIsInstance(result, Path)
            self.assertTrue(result.exists())
        finally:
            Path(path).unlink()

    def test_nonexistent_path_raises(self):
        """Should raise ValueError for nonexistent paths when must_exist=True."""
        with self.assertRaises(ValueError) as ctx:
            validate_path("/nonexistent/path/that/does/not/exist", must_exist=True)
        self.assertIn("does not exist", str(ctx.exception))

    def test_file_when_must_be_dir_raises(self):
        """Should raise ValueError when path is file but must_be_dir=True."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                validate_path(path, must_exist=True, must_be_dir=True)
            self.assertIn("not a directory", str(ctx.exception))
        finally:
            Path(path).unlink()

    def test_nonexistent_allowed(self):
        """Should succeed for nonexistent paths when must_exist=False."""
        result = validate_path("/some/nonexistent/path", must_exist=False)
        self.assertIsInstance(result, Path)


class TestValidateBranchName(unittest.TestCase):
    """Tests for validate_branch_name function."""

    def test_valid_branch_names(self):
        """Should accept valid branch names."""
        valid_names = [
            "main",
            "feature/new-feature",
            "fix/bug-123",
            "auto-review/20231218-123456-abcd",
            "release-v1.0.0",
            "user_branch",
        ]
        for name in valid_names:
            result = validate_branch_name(name)
            self.assertEqual(result, name)

    def test_empty_branch_name_raises(self):
        """Should raise ValueError for empty branch names."""
        with self.assertRaises(ValueError) as ctx:
            validate_branch_name("")
        self.assertIn("cannot be empty", str(ctx.exception))

    def test_whitespace_only_raises(self):
        """Should raise ValueError for whitespace-only branch names."""
        with self.assertRaises(ValueError) as ctx:
            validate_branch_name("   ")
        self.assertIn("cannot be empty", str(ctx.exception))

    def test_shell_injection_blocked(self):
        """Should block shell metacharacters to prevent injection."""
        dangerous_inputs = [
            "branch; rm -rf /",
            "branch$(whoami)",
            "branch`id`",
            "branch|cat /etc/passwd",
            "branch&& malicious",
            "branch > /tmp/evil",
            "branch < /etc/shadow",
            "branch\nmalicious",
            "branch\rmalicious",
            "branch\0malicious",
        ]
        for name in dangerous_inputs:
            with self.assertRaises(ValueError) as ctx:
                validate_branch_name(name)
            self.assertIn("invalid character", str(ctx.exception))

    def test_invalid_git_ref_names(self):
        """Should reject invalid git ref name patterns."""
        invalid_names = [
            "-starts-with-dash",
            ".starts-with-dot",
            "contains..double-dots",
            "ends-with.lock",
            "ends-with-slash/",
        ]
        for name in invalid_names:
            with self.assertRaises(ValueError):
                validate_branch_name(name)

    def test_too_long_branch_name_raises(self):
        """Should reject branch names over 250 characters."""
        long_name = "x" * 251
        with self.assertRaises(ValueError) as ctx:
            validate_branch_name(long_name)
        self.assertIn("too long", str(ctx.exception))


class TestValidateCronExpression(unittest.TestCase):
    """Tests for validate_cron_expression function."""

    def test_valid_cron_expressions(self):
        """Should accept valid cron expressions."""
        valid_exprs = [
            "* * * * *",
            "0 * * * *",
            "0 0 * * *",
            "0 0 1 * *",
            "0 0 * * 0",
            "*/15 * * * *",
            "0 9-17 * * 1-5",
        ]
        for expr in valid_exprs:
            result = validate_cron_expression(expr)
            self.assertEqual(result, expr)

    def test_empty_expression_raises(self):
        """Should raise ValueError for empty expressions."""
        with self.assertRaises(ValueError) as ctx:
            validate_cron_expression("")
        self.assertIn("cannot be empty", str(ctx.exception))

    def test_wrong_field_count_raises(self):
        """Should raise ValueError for wrong number of fields."""
        invalid_exprs = [
            "* * * *",      # 4 fields
            "* * * * * *",  # 6 fields
            "0 0",          # 2 fields
        ]
        for expr in invalid_exprs:
            with self.assertRaises(ValueError) as ctx:
                validate_cron_expression(expr)
            self.assertIn("5 fields", str(ctx.exception))

    def test_shell_injection_blocked(self):
        """Should block shell metacharacters."""
        dangerous_inputs = [
            "* * * * *; rm -rf /",
            "* * * * * && cat /etc/passwd",
            "$(whoami) * * * *",
        ]
        for expr in dangerous_inputs:
            with self.assertRaises(ValueError) as ctx:
                validate_cron_expression(expr)
            self.assertIn("invalid character", str(ctx.exception))


class TestValidatePositiveInt(unittest.TestCase):
    """Tests for validate_positive_int function."""

    def test_valid_positive_integers(self):
        """Should accept positive integers."""
        self.assertEqual(validate_positive_int(1, "test"), 1)
        self.assertEqual(validate_positive_int(100, "test"), 100)
        self.assertEqual(validate_positive_int(1000000, "test"), 1000000)

    def test_zero_raises(self):
        """Should raise ValueError for zero."""
        with self.assertRaises(ValueError) as ctx:
            validate_positive_int(0, "count")
        self.assertIn("positive integer", str(ctx.exception))

    def test_negative_raises(self):
        """Should raise ValueError for negative integers."""
        with self.assertRaises(ValueError) as ctx:
            validate_positive_int(-5, "iterations")
        self.assertIn("positive integer", str(ctx.exception))

    def test_max_value_enforced(self):
        """Should raise ValueError when value exceeds max_value."""
        with self.assertRaises(ValueError) as ctx:
            validate_positive_int(100, "interval", max_value=60)
        self.assertIn("cannot exceed", str(ctx.exception))

    def test_at_max_value_allowed(self):
        """Should accept value equal to max_value."""
        result = validate_positive_int(60, "interval", max_value=60)
        self.assertEqual(result, 60)


class TestGetCombinedPrompt(unittest.TestCase):
    """Tests for get_combined_prompt function."""

    def test_single_mode(self):
        """Should return the mode's prompt for single mode."""
        result = get_combined_prompt(["fix_bugs"])
        self.assertEqual(result, IMPROVEMENT_MODES["fix_bugs"]["prompt"])

    def test_multiple_modes(self):
        """Should combine prompts for multiple modes."""
        result = get_combined_prompt(["fix_bugs", "security"])
        self.assertIn("Fix Bugs", result)
        self.assertIn("Security Review", result)
        self.assertIn("multiple types of code improvements", result)

    def test_all_modes_have_required_fields(self):
        """Should verify all modes have required fields."""
        for key, mode in IMPROVEMENT_MODES.items():
            self.assertIn("name", mode, f"Mode {key} missing 'name'")
            self.assertIn("description", mode, f"Mode {key} missing 'description'")
            self.assertIn("prompt", mode, f"Mode {key} missing 'prompt'")


class TestPromptGenerators(unittest.TestCase):
    """Tests for prompt generator functions."""

    def test_get_northstar_prompt_includes_content(self):
        """Should include the provided content in the prompt."""
        content = "# My Vision\n\n## Goals\n- Goal 1"
        result = get_northstar_prompt(content)
        self.assertIn("My Vision", result)
        self.assertIn("Goal 1", result)

    def test_get_northstar_prompt_includes_instructions(self):
        """Should include instructions for making progress."""
        result = get_northstar_prompt("test content")
        self.assertIn("Analyze the current state", result)
        self.assertIn("Make concrete progress", result)
        self.assertIn("Commit your changes", result)

    def test_get_pr_review_prompt_includes_pr_number(self):
        """Should include the PR number in the prompt."""
        result = get_pr_review_prompt("123")
        self.assertIn("PR #123", result)
        self.assertIn("gh pr view 123", result)
        self.assertIn("gh pr diff 123", result)

    def test_get_pr_review_prompt_includes_decision_instructions(self):
        """Should include APPROVED/CHANGES_REQUESTED instructions."""
        result = get_pr_review_prompt("456")
        self.assertIn("APPROVED", result)
        self.assertIn("CHANGES_REQUESTED", result)

    def test_get_fix_feedback_prompt_includes_pr_and_feedback(self):
        """Should include PR number and feedback in the prompt."""
        result = get_fix_feedback_prompt("789", "Fix the typo in line 42")
        self.assertIn("PR #789", result)
        self.assertIn("Fix the typo in line 42", result)
        self.assertIn("gh pr checkout 789", result)

    def test_get_fix_feedback_prompt_includes_commit_instructions(self):
        """Should include instructions to commit and push."""
        result = get_fix_feedback_prompt("100", "Some feedback")
        self.assertIn("Commit", result)
        self.assertIn("git push", result)


class TestNorthstarFunctions(unittest.TestCase):
    """Tests for NORTHSTAR.md related functions."""

    def test_create_default_northstar_success(self):
        """Should create NORTHSTAR.md successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            success, msg = create_default_northstar(project_dir)
            self.assertTrue(success)
            self.assertTrue((project_dir / "NORTHSTAR.md").exists())

    def test_create_default_northstar_already_exists(self):
        """Should fail if NORTHSTAR.md already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "NORTHSTAR.md").write_text("existing content")
            success, msg = create_default_northstar(project_dir)
            self.assertFalse(success)
            self.assertIn("already exists", msg)

    def test_load_northstar_prompt_success(self):
        """Should load and format NORTHSTAR.md content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "NORTHSTAR.md").write_text("# Test North Star\n\nVision here")
            prompt, error = load_northstar_prompt(project_dir)
            self.assertIsNotNone(prompt)
            self.assertIsNone(error)
            self.assertIn("Test North Star", prompt)

    def test_load_northstar_prompt_not_found(self):
        """Should return error if NORTHSTAR.md not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            prompt, error = load_northstar_prompt(project_dir)
            self.assertIsNone(prompt)
            self.assertIn("not found", error)

    def test_load_northstar_prompt_empty_file(self):
        """Should return error if NORTHSTAR.md is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "NORTHSTAR.md").write_text("")
            prompt, error = load_northstar_prompt(project_dir)
            self.assertIsNone(prompt)
            self.assertIn("empty", error)


class TestLockFile(unittest.TestCase):
    """Tests for LockFile class."""

    def test_acquire_and_release(self):
        """Should acquire and release lock successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / ".test.lock"
            lock = LockFile(lock_path)

            # Should acquire successfully
            self.assertTrue(lock.acquire())
            self.assertTrue(lock_path.exists())

            # Lock file should contain PID
            content = lock_path.read_text()
            self.assertIn(str(os.getpid()), content)

            # Release should clean up
            lock.release()
            self.assertFalse(lock_path.exists())

    def test_cannot_acquire_twice(self):
        """Should not allow acquiring the same lock twice."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / ".test.lock"
            lock1 = LockFile(lock_path)
            lock2 = LockFile(lock_path)

            self.assertTrue(lock1.acquire())
            self.assertFalse(lock2.acquire())

            lock1.release()

    def test_release_nonexistent_lock(self):
        """Should handle releasing a lock that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / ".nonexistent.lock"
            lock = LockFile(lock_path)
            # Should not raise
            lock.release()


class TestTelegramNotifier(unittest.TestCase):
    """Tests for TelegramNotifier class."""

    def test_disabled_when_no_credentials(self):
        """Should be disabled when credentials are missing."""
        notifier = TelegramNotifier(None, None)
        self.assertFalse(notifier.enabled)

        notifier = TelegramNotifier("token", None)
        self.assertFalse(notifier.enabled)

        notifier = TelegramNotifier(None, "chat_id")
        self.assertFalse(notifier.enabled)

    def test_enabled_with_credentials(self):
        """Should be enabled when both credentials provided."""
        notifier = TelegramNotifier("token", "chat_id")
        self.assertTrue(notifier.enabled)

    def test_send_returns_false_when_disabled(self):
        """Should return False without sending when disabled."""
        notifier = TelegramNotifier(None, None)
        result = notifier.send("test message")
        self.assertFalse(result)

    @patch('urllib.request.urlopen')
    def test_send_success(self, mock_urlopen):
        """Should send message and return True on success."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        notifier = TelegramNotifier("bot_token", "chat_id")
        result = notifier.send("test message")

        self.assertTrue(result)
        mock_urlopen.assert_called_once()

    @patch('urllib.request.urlopen')
    def test_send_failure(self, mock_urlopen):
        """Should return False on network error."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Network error")

        notifier = TelegramNotifier("bot_token", "chat_id")
        result = notifier.send("test message")

        self.assertFalse(result)


class TestAutoReviewer(unittest.TestCase):
    """Tests for AutoReviewer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmpdir = tempfile.mkdtemp()
        self.reviewer = AutoReviewer(
            project_dir=self.tmpdir,
            base_branch="main",
            auto_merge=False,
            max_iterations=3,
            modes=["fix_bugs"]
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_initialization(self):
        """Should initialize with correct default values."""
        self.assertEqual(self.reviewer.base_branch, "main")
        self.assertFalse(self.reviewer.auto_merge)
        self.assertEqual(self.reviewer.max_iterations, 3)
        self.assertEqual(self.reviewer.modes, ["fix_bugs"])
        self.assertTrue(self.reviewer.project_dir.is_absolute())

    def test_get_mode_names(self):
        """Should return human-readable mode names."""
        result = self.reviewer.get_mode_names()
        self.assertEqual(result, "Fix Bugs")

        multi_mode_reviewer = AutoReviewer(
            project_dir=self.tmpdir,
            modes=["fix_bugs", "security"]
        )
        result = multi_mode_reviewer.get_mode_names()
        self.assertEqual(result, "Fix Bugs, Security Review")

    def test_generate_branch_name(self):
        """Should generate valid branch names."""
        branch = self.reviewer.generate_branch_name()
        self.assertTrue(branch.startswith("auto-fix-bugs/"))
        self.assertLessEqual(len(branch), 250)
        # Should be unique
        branch2 = self.reviewer.generate_branch_name()
        self.assertNotEqual(branch, branch2)

    def test_log_writes_to_file(self):
        """Should write log messages to file."""
        self.reviewer.log("Test message")
        log_content = self.reviewer.log_file.read_text()
        self.assertIn("Test message", log_content)

    @patch('subprocess.run')
    def test_run_cmd_success(self, mock_run):
        """Should return success and output on successful command."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output",
            stderr=""
        )

        success, output = self.reviewer.run_cmd(["echo", "test"])

        self.assertTrue(success)
        self.assertEqual(output, "output")

    @patch('subprocess.run')
    def test_run_cmd_failure(self, mock_run):
        """Should return failure and output on failed command."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error message"
        )

        success, output = self.reviewer.run_cmd(["false"])

        self.assertFalse(success)
        self.assertIn("error message", output)

    @patch('subprocess.run')
    def test_run_cmd_timeout(self, mock_run):
        """Should handle command timeout gracefully."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 60)

        success, output = self.reviewer.run_cmd(["sleep", "999"])

        self.assertFalse(success)
        self.assertIn("timed out", output)

    @patch('subprocess.run')
    def test_run_cmd_command_not_found(self, mock_run):
        """Should handle command not found gracefully."""
        mock_run.side_effect = FileNotFoundError()

        success, output = self.reviewer.run_cmd(["nonexistent_cmd"])

        self.assertFalse(success)
        self.assertIn("not found", output)

    @patch('subprocess.Popen')
    def test_run_claude_command_not_found(self, mock_popen):
        """Should return helpful error when Claude CLI not found."""
        mock_popen.side_effect = FileNotFoundError()

        success, output = self.reviewer.run_claude("test prompt")

        self.assertFalse(success)
        self.assertIn("Claude CLI not found", output)

    @patch('time.time')
    @patch('subprocess.Popen')
    def test_run_claude_timeout(self, mock_popen, mock_time):
        """Should handle Claude timeout gracefully."""
        # Simulate time passing beyond timeout
        mock_time.side_effect = [0, 0, 10]  # start_time, first check, timeout check

        mock_process = MagicMock()
        mock_process.stdout.readline.return_value = ""
        mock_process.poll.return_value = None
        mock_process.kill = MagicMock()
        mock_popen.return_value = mock_process

        success, output = self.reviewer.run_claude("test prompt", timeout=5)

        self.assertFalse(success)
        self.assertIn("timed out", output)
        mock_process.kill.assert_called_once()

    @patch.object(AutoReviewer, 'run_cmd')
    def test_has_commits_ahead_true(self, mock_run_cmd):
        """Should detect commits ahead of base branch."""
        mock_run_cmd.return_value = (True, "5")

        result = self.reviewer.has_commits_ahead()

        self.assertTrue(result)

    @patch.object(AutoReviewer, 'run_cmd')
    def test_has_commits_ahead_false(self, mock_run_cmd):
        """Should detect no commits ahead of base branch."""
        mock_run_cmd.return_value = (True, "0")

        result = self.reviewer.has_commits_ahead()

        self.assertFalse(result)

    @patch.object(AutoReviewer, 'run_cmd')
    def test_has_commits_ahead_invalid_output(self, mock_run_cmd):
        """Should handle invalid git output gracefully."""
        mock_run_cmd.return_value = (True, "not a number")

        result = self.reviewer.has_commits_ahead()

        self.assertFalse(result)

    @patch.object(AutoReviewer, 'run_cmd')
    def test_merge_pr(self, mock_run_cmd):
        """Should call gh with correct arguments."""
        mock_run_cmd.return_value = (True, "Merged")

        result = self.reviewer.merge_pr("https://github.com/owner/repo/pull/123")

        self.assertTrue(result)
        mock_run_cmd.assert_called_once()
        call_args = mock_run_cmd.call_args[0][0]
        self.assertIn("gh", call_args)
        self.assertIn("merge", call_args)
        self.assertIn("123", call_args)

    @patch.object(AutoReviewer, 'run_cmd')
    def test_cleanup_branch(self, mock_run_cmd):
        """Should checkout base branch on cleanup."""
        mock_run_cmd.return_value = (True, "")
        self.reviewer.current_branch = "test-branch"

        self.reviewer.cleanup_branch()

        mock_run_cmd.assert_called_once()
        call_args = mock_run_cmd.call_args[0][0]
        self.assertIn("checkout", call_args)
        self.assertIn("main", call_args)
        self.assertIsNone(self.reviewer.current_branch)

    @patch.object(AutoReviewer, 'run_cmd')
    def test_create_branch_success(self, mock_run_cmd):
        """Should create branch and set current_branch."""
        mock_run_cmd.return_value = (True, "")

        result = self.reviewer.create_branch("test-branch")

        self.assertTrue(result)
        self.assertEqual(self.reviewer.current_branch, "test-branch")
        # Should call: checkout base, pull --rebase, checkout -b new_branch
        self.assertEqual(mock_run_cmd.call_count, 3)

    @patch.object(AutoReviewer, 'run_cmd')
    def test_create_branch_failure(self, mock_run_cmd):
        """Should return False when branch creation fails."""
        # First two calls succeed, third fails
        mock_run_cmd.side_effect = [(True, ""), (True, ""), (False, "error")]

        result = self.reviewer.create_branch("test-branch")

        self.assertFalse(result)
        self.assertIsNone(self.reviewer.current_branch)

    @patch.object(AutoReviewer, 'run_cmd')
    @patch.object(AutoReviewer, 'has_commits_ahead')
    def test_create_pull_request_success(self, mock_has_commits, mock_run_cmd):
        """Should create PR and return URL on success."""
        mock_has_commits.return_value = True
        mock_run_cmd.side_effect = [
            (True, ""),  # git push
            (True, "https://github.com/owner/repo/pull/123\n"),  # gh pr create
        ]
        self.reviewer.current_branch = "test-branch"

        result = self.reviewer.create_pull_request("Test summary")

        self.assertEqual(result, "https://github.com/owner/repo/pull/123")

    @patch.object(AutoReviewer, 'has_commits_ahead')
    def test_create_pull_request_no_commits(self, mock_has_commits):
        """Should return None when no commits ahead."""
        mock_has_commits.return_value = False

        result = self.reviewer.create_pull_request("Test summary")

        self.assertIsNone(result)

    @patch.object(AutoReviewer, 'run_cmd')
    @patch.object(AutoReviewer, 'has_commits_ahead')
    def test_create_pull_request_push_fails(self, mock_has_commits, mock_run_cmd):
        """Should return None when git push fails."""
        mock_has_commits.return_value = True
        mock_run_cmd.return_value = (False, "push failed")
        self.reviewer.current_branch = "test-branch"

        result = self.reviewer.create_pull_request("Test summary")

        self.assertIsNone(result)

    @patch.object(AutoReviewer, 'run_claude')
    def test_review_pr_approved(self, mock_run_claude):
        """Should detect PR approval correctly."""
        mock_run_claude.return_value = (True, "APPROVED - looks good!")

        approved, output, feedback = self.reviewer.review_pr_with_claude(
            "https://github.com/owner/repo/pull/123"
        )

        self.assertTrue(approved)

    @patch.object(AutoReviewer, 'run_claude')
    def test_review_pr_changes_requested(self, mock_run_claude):
        """Should detect changes requested correctly."""
        mock_run_claude.return_value = (
            True,
            "CHANGES_REQUESTED: Please fix the formatting"
        )

        approved, output, feedback = self.reviewer.review_pr_with_claude(
            "https://github.com/owner/repo/pull/123"
        )

        self.assertFalse(approved)
        self.assertIn("formatting", feedback)


class TestSchedulingFunctions(unittest.TestCase):
    """Tests for scheduling functions (run_loop, run_with_interval)."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmpdir = tempfile.mkdtemp()
        self.reviewer = AutoReviewer(
            project_dir=self.tmpdir,
            base_branch="main",
            modes=["fix_bugs"]
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch.object(AutoReviewer, 'run_once')
    @patch('builtins.print')
    def test_run_loop_calls_run_once(self, mock_print, mock_run_once):
        """Should call run_once repeatedly in a loop."""
        # Import run_loop
        from claude_automator import run_loop

        # Set up mock to raise after 3 calls to break the infinite loop
        call_count = 0
        def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise KeyboardInterrupt()
            return True

        mock_run_once.side_effect = side_effect

        # run_loop will loop until KeyboardInterrupt
        try:
            run_loop(self.reviewer)
        except KeyboardInterrupt:
            pass

        # Should have called run_once 3 times
        self.assertEqual(mock_run_once.call_count, 3)

    @patch('time.sleep')
    @patch('time.time')
    @patch.object(AutoReviewer, 'run_once')
    @patch('builtins.print')
    def test_run_with_interval_respects_interval(self, mock_print, mock_run_once, mock_time, mock_sleep):
        """Should wait for remaining interval time after each run."""
        from claude_automator import run_with_interval

        # Simulate run_once taking 2 seconds when interval is 10
        call_count = 0
        def time_side_effect():
            nonlocal call_count
            call_count += 1
            # First call is start time (0), second is after run (2s elapsed)
            if call_count % 2 == 1:
                return 0
            else:
                return 2

        mock_time.side_effect = time_side_effect

        run_count = 0
        def run_once_side_effect():
            nonlocal run_count
            run_count += 1
            if run_count >= 2:
                raise KeyboardInterrupt()
            return True

        mock_run_once.side_effect = run_once_side_effect

        try:
            run_with_interval(self.reviewer, 10)
        except KeyboardInterrupt:
            pass

        # Should have called sleep with 8 seconds (10 - 2 = 8)
        mock_sleep.assert_called_with(8)

    @patch('time.sleep')
    @patch('time.time')
    @patch.object(AutoReviewer, 'run_once')
    @patch('builtins.print')
    def test_run_with_interval_no_sleep_if_run_exceeds_interval(self, mock_print, mock_run_once, mock_time, mock_sleep):
        """Should not sleep if run_once takes longer than interval."""
        from claude_automator import run_with_interval

        # Simulate run_once taking 15 seconds when interval is 10
        call_count = 0
        def time_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:
                return 0
            else:
                return 15

        mock_time.side_effect = time_side_effect

        run_count = 0
        def run_once_side_effect():
            nonlocal run_count
            run_count += 1
            if run_count >= 2:
                raise KeyboardInterrupt()
            return True

        mock_run_once.side_effect = run_once_side_effect

        try:
            run_with_interval(self.reviewer, 10)
        except KeyboardInterrupt:
            pass

        # Should not have called sleep since max(0, 10-15) = 0
        mock_sleep.assert_not_called()


class TestRunOnceWorkflow(unittest.TestCase):
    """Tests for the run_once() orchestration workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmpdir = tempfile.mkdtemp()
        self.reviewer = AutoReviewer(
            project_dir=self.tmpdir,
            base_branch="main",
            auto_merge=False,
            max_iterations=3,
            modes=["fix_bugs"]
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch.object(AutoReviewer, 'run_claude')
    @patch.object(AutoReviewer, 'create_branch')
    @patch.object(LockFile, 'acquire')
    @patch.object(LockFile, 'release')
    def test_run_once_lock_already_held(self, mock_release, mock_acquire, mock_create, mock_claude):
        """Should return False immediately if lock cannot be acquired."""
        mock_acquire.return_value = False

        result = self.reviewer.run_once()

        self.assertFalse(result)
        mock_create.assert_not_called()
        mock_claude.assert_not_called()

    @patch.object(TelegramNotifier, 'send')
    @patch.object(AutoReviewer, 'run_claude')
    @patch.object(AutoReviewer, 'create_branch')
    @patch.object(LockFile, 'acquire')
    @patch.object(LockFile, 'release')
    def test_run_once_branch_creation_fails(self, mock_release, mock_acquire, mock_create, mock_claude, mock_tg):
        """Should return False and notify if branch creation fails."""
        mock_acquire.return_value = True
        mock_create.return_value = False

        result = self.reviewer.run_once()

        self.assertFalse(result)
        mock_claude.assert_not_called()
        mock_tg.assert_called()  # Should send failure notification

    @patch.object(TelegramNotifier, 'send')
    @patch.object(AutoReviewer, 'cleanup_branch')
    @patch.object(AutoReviewer, 'run_claude')
    @patch.object(AutoReviewer, 'create_branch')
    @patch.object(LockFile, 'acquire')
    @patch.object(LockFile, 'release')
    def test_run_once_claude_fails(self, mock_release, mock_acquire, mock_create, mock_claude, mock_cleanup, mock_tg):
        """Should cleanup and return False if Claude fails."""
        mock_acquire.return_value = True
        mock_create.return_value = True
        mock_claude.return_value = (False, "Claude failed")

        result = self.reviewer.run_once()

        self.assertFalse(result)
        mock_cleanup.assert_called()
        mock_tg.assert_called()

    @patch.object(TelegramNotifier, 'send')
    @patch.object(AutoReviewer, 'cleanup_branch')
    @patch.object(AutoReviewer, 'has_commits_ahead')
    @patch.object(AutoReviewer, 'run_claude')
    @patch.object(AutoReviewer, 'create_branch')
    @patch.object(LockFile, 'acquire')
    @patch.object(LockFile, 'release')
    def test_run_once_no_changes_made(self, mock_release, mock_acquire, mock_create, mock_claude, mock_commits, mock_cleanup, mock_tg):
        """Should succeed and cleanup when Claude makes no changes."""
        mock_acquire.return_value = True
        mock_create.return_value = True
        mock_claude.return_value = (True, "No changes needed")
        mock_commits.return_value = False

        result = self.reviewer.run_once()

        self.assertTrue(result)
        mock_cleanup.assert_called()

    @patch.object(TelegramNotifier, 'send')
    @patch.object(AutoReviewer, 'cleanup_branch')
    @patch.object(AutoReviewer, 'create_pull_request')
    @patch.object(AutoReviewer, 'has_commits_ahead')
    @patch.object(AutoReviewer, 'run_claude')
    @patch.object(AutoReviewer, 'create_branch')
    @patch.object(LockFile, 'acquire')
    @patch.object(LockFile, 'release')
    def test_run_once_pr_creation_fails(self, mock_release, mock_acquire, mock_create, mock_claude, mock_commits, mock_pr, mock_cleanup, mock_tg):
        """Should cleanup and return False if PR creation fails."""
        mock_acquire.return_value = True
        mock_create.return_value = True
        mock_claude.return_value = (True, "Made changes")
        mock_commits.return_value = True
        mock_pr.return_value = None

        result = self.reviewer.run_once()

        self.assertFalse(result)
        mock_cleanup.assert_called()

    @patch.object(TelegramNotifier, 'send')
    @patch.object(AutoReviewer, 'cleanup_branch')
    @patch.object(AutoReviewer, 'review_pr_with_claude')
    @patch.object(AutoReviewer, 'create_pull_request')
    @patch.object(AutoReviewer, 'has_commits_ahead')
    @patch.object(AutoReviewer, 'run_claude')
    @patch.object(AutoReviewer, 'create_branch')
    @patch.object(LockFile, 'acquire')
    @patch.object(LockFile, 'release')
    def test_run_once_pr_approved_first_try(self, mock_release, mock_acquire, mock_create, mock_claude, mock_commits, mock_pr, mock_review, mock_cleanup, mock_tg):
        """Should succeed when PR is approved on first review."""
        mock_acquire.return_value = True
        mock_create.return_value = True
        mock_claude.return_value = (True, "Made changes")
        mock_commits.return_value = True
        mock_pr.return_value = "https://github.com/owner/repo/pull/123"
        mock_review.return_value = (True, "APPROVED", "Looks good")

        result = self.reviewer.run_once()

        self.assertTrue(result)
        mock_review.assert_called_once()

    @patch.object(TelegramNotifier, 'send')
    @patch.object(AutoReviewer, 'cleanup_branch')
    @patch.object(AutoReviewer, 'merge_pr')
    @patch.object(AutoReviewer, 'review_pr_with_claude')
    @patch.object(AutoReviewer, 'create_pull_request')
    @patch.object(AutoReviewer, 'has_commits_ahead')
    @patch.object(AutoReviewer, 'run_claude')
    @patch.object(AutoReviewer, 'create_branch')
    @patch.object(LockFile, 'acquire')
    @patch.object(LockFile, 'release')
    def test_run_once_auto_merge_on_approval(self, mock_release, mock_acquire, mock_create, mock_claude, mock_commits, mock_pr, mock_review, mock_merge, mock_cleanup, mock_tg):
        """Should auto-merge PR when approved and auto_merge is enabled."""
        self.reviewer.auto_merge = True
        mock_acquire.return_value = True
        mock_create.return_value = True
        mock_claude.return_value = (True, "Made changes")
        mock_commits.return_value = True
        mock_pr.return_value = "https://github.com/owner/repo/pull/123"
        mock_review.return_value = (True, "APPROVED", "Looks good")
        mock_merge.return_value = True

        result = self.reviewer.run_once()

        self.assertTrue(result)
        mock_merge.assert_called_once_with("https://github.com/owner/repo/pull/123")

    @patch.object(TelegramNotifier, 'send')
    @patch.object(AutoReviewer, 'cleanup_branch')
    @patch.object(AutoReviewer, 'fix_pr_feedback')
    @patch.object(AutoReviewer, 'review_pr_with_claude')
    @patch.object(AutoReviewer, 'create_pull_request')
    @patch.object(AutoReviewer, 'has_commits_ahead')
    @patch.object(AutoReviewer, 'run_claude')
    @patch.object(AutoReviewer, 'create_branch')
    @patch.object(LockFile, 'acquire')
    @patch.object(LockFile, 'release')
    def test_run_once_fix_cycle_then_approved(self, mock_release, mock_acquire, mock_create, mock_claude, mock_commits, mock_pr, mock_review, mock_fix, mock_cleanup, mock_tg):
        """Should iterate fix cycle until approved."""
        mock_acquire.return_value = True
        mock_create.return_value = True
        mock_claude.return_value = (True, "Made changes")
        mock_commits.return_value = True
        mock_pr.return_value = "https://github.com/owner/repo/pull/123"
        # First review requests changes, second approves
        mock_review.side_effect = [
            (False, "CHANGES_REQUESTED: Fix formatting", "Fix formatting"),
            (True, "APPROVED", "Looks good now"),
        ]
        mock_fix.return_value = (True, "Fixed formatting")

        result = self.reviewer.run_once()

        self.assertTrue(result)
        self.assertEqual(mock_review.call_count, 2)
        mock_fix.assert_called_once()

    @patch.object(TelegramNotifier, 'send')
    @patch.object(AutoReviewer, 'cleanup_branch')
    @patch.object(AutoReviewer, 'fix_pr_feedback')
    @patch.object(AutoReviewer, 'review_pr_with_claude')
    @patch.object(AutoReviewer, 'create_pull_request')
    @patch.object(AutoReviewer, 'has_commits_ahead')
    @patch.object(AutoReviewer, 'run_claude')
    @patch.object(AutoReviewer, 'create_branch')
    @patch.object(LockFile, 'acquire')
    @patch.object(LockFile, 'release')
    def test_run_once_max_iterations_reached(self, mock_release, mock_acquire, mock_create, mock_claude, mock_commits, mock_pr, mock_review, mock_fix, mock_cleanup, mock_tg):
        """Should stop after max_iterations even if not approved."""
        self.reviewer.max_iterations = 2
        mock_acquire.return_value = True
        mock_create.return_value = True
        mock_claude.return_value = (True, "Made changes")
        mock_commits.return_value = True
        mock_pr.return_value = "https://github.com/owner/repo/pull/123"
        # Always request changes
        mock_review.return_value = (False, "CHANGES_REQUESTED: Still not right", "Fix it")
        mock_fix.return_value = (True, "Tried to fix")

        result = self.reviewer.run_once()

        self.assertTrue(result)  # Still returns True (cycle completed)
        self.assertEqual(mock_review.call_count, 2)
        self.assertEqual(mock_fix.call_count, 2)

    @patch.object(TelegramNotifier, 'send')
    @patch.object(AutoReviewer, 'cleanup_branch')
    @patch.object(AutoReviewer, 'fix_pr_feedback')
    @patch.object(AutoReviewer, 'review_pr_with_claude')
    @patch.object(AutoReviewer, 'create_pull_request')
    @patch.object(AutoReviewer, 'has_commits_ahead')
    @patch.object(AutoReviewer, 'run_claude')
    @patch.object(AutoReviewer, 'create_branch')
    @patch.object(LockFile, 'acquire')
    @patch.object(LockFile, 'release')
    def test_run_once_fix_fails(self, mock_release, mock_acquire, mock_create, mock_claude, mock_commits, mock_pr, mock_review, mock_fix, mock_cleanup, mock_tg):
        """Should break loop if fix fails."""
        mock_acquire.return_value = True
        mock_create.return_value = True
        mock_claude.return_value = (True, "Made changes")
        mock_commits.return_value = True
        mock_pr.return_value = "https://github.com/owner/repo/pull/123"
        mock_review.return_value = (False, "CHANGES_REQUESTED", "Fix it")
        mock_fix.return_value = (False, "Fix failed")

        result = self.reviewer.run_once()

        self.assertTrue(result)  # Cycle completed even though fix failed
        mock_fix.assert_called_once()
        # Should notify about fixer failure
        self.assertTrue(any("Fixer Failed" in str(call) for call in mock_tg.call_args_list))


if __name__ == "__main__":
    unittest.main()
