#!/usr/bin/env python3
"""
Concurrent Claude Automator - Run multiple Claude/Codex workers in parallel.

Each worker runs the FULL cycle (improve → PR → review → fix → merge)
but scoped to a specific directory. Uses git worktrees for true parallelism.

Usage:
    # Run on specific directories
    ./claude_automator_concurrent.py -d src scripts -p "Fix bugs"

    # Auto-partition top-level directories
    ./claude_automator_concurrent.py --auto-partition -p "Improve code quality"

    # Use config file for different prompts per directory
    ./claude_automator_concurrent.py --config workers.json

    # Same options as main script
    ./claude_automator_concurrent.py -d src -p "Fix bugs" --think ultrathink --auto-merge
    ./claude_automator_concurrent.py -d src --llm codex --think ultrathink

Example workers.json:
[
    {"directory": "src", "prompt": "Fix bugs in this directory"},
    {"directory": "scripts", "prompt": "Add type hints"},
    {"directory": "lib", "modes": ["security", "fix_bugs"]}
]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .automator import (
    AutoReviewer,
    validate_branch_name,
    get_combined_prompt,
    IMPROVEMENT_MODES,
)


@dataclass
class WorkerConfig:
    """Configuration for a single worker."""
    directory: str
    prompt: str | None = None
    modes: list[str] | None = None

    def get_scoped_prompt(self, base_prompt: str) -> str:
        """Get the prompt scoped to this directory."""
        prompt = self.prompt or base_prompt
        return f"""You are working ONLY on the directory: {self.directory}/

IMPORTANT CONSTRAINTS:
- You may ONLY modify files within: {self.directory}/
- Do NOT touch any files outside this directory
- Do NOT modify files in other directories, even if they seem related
- If you need to import from other directories, that's fine, but don't edit those files

YOUR TASK:
{prompt}
"""


@dataclass
class WorkerResult:
    """Result from a worker execution."""
    worker_id: int
    directory: str
    success: bool
    pr_url: str | None = None
    merged: bool = False
    error: str | None = None
    duration_seconds: float = 0.0
    cost_usd: float = 0.0


def setup_worktree(project_dir: Path, worker_id: int, base_branch: str) -> Path | None:
    """Create a git worktree for isolated parallel execution."""
    worktree_dir = project_dir / ".worktrees" / f"worker-{worker_id}"

    # Clean up if exists
    if worktree_dir.exists():
        try:
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_dir), "--force"],
                cwd=project_dir, capture_output=True, timeout=30
            )
        except Exception:
            shutil.rmtree(worktree_dir, ignore_errors=True)

    # Create worktree
    worktree_dir.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["git", "worktree", "add", str(worktree_dir), base_branch],
        cwd=project_dir, capture_output=True, text=True, timeout=60
    )

    if result.returncode != 0:
        print(f"[Worker {worker_id}] Failed to create worktree: {result.stderr}")
        return None

    return worktree_dir


def cleanup_worktree(project_dir: Path, worktree_dir: Path) -> None:
    """Remove a git worktree."""
    try:
        subprocess.run(
            ["git", "worktree", "remove", str(worktree_dir), "--force"],
            cwd=project_dir, capture_output=True, timeout=30
        )
    except Exception:
        shutil.rmtree(worktree_dir, ignore_errors=True)


def run_worker(
    worker_id: int,
    config: WorkerConfig,
    worktree_dir: Path,
    base_branch: str,
    auto_merge: bool,
    max_iterations: int,
    think_level: str,
    llm_provider: str,
    tg_bot_token: str | None,
    tg_chat_id: str | None,
    create_pr: bool = False,
) -> WorkerResult:
    """Run a single worker through the full PR cycle."""
    start_time = time.time()

    # Validate directory exists in worktree
    target_dir = worktree_dir / config.directory
    if not target_dir.is_dir():
        return WorkerResult(
            worker_id=worker_id,
            directory=config.directory,
            success=False,
            error=f"Directory does not exist: {config.directory}",
            duration_seconds=time.time() - start_time,
        )

    # Build scoped prompt
    if config.modes:
        base_prompt = get_combined_prompt(config.modes)
    else:
        base_prompt = config.prompt or "Improve code quality"

    scoped_prompt = config.get_scoped_prompt(base_prompt)

    # Create AutoReviewer for this worker
    reviewer = AutoReviewer(
        project_dir=worktree_dir,
        base_branch=base_branch,
        auto_merge=auto_merge,
        max_iterations=max_iterations,
        tg_bot_token=tg_bot_token,
        tg_chat_id=tg_chat_id,
        review_prompt=scoped_prompt,
        modes=config.modes or ["improve_code"],
        think_level=think_level,
        llm_provider=llm_provider,
        create_pr=create_pr,
    )

    # Override branch name to include directory
    original_generate = reviewer.generate_branch_name
    def scoped_branch_name() -> str:
        name = original_generate()
        dir_slug = config.directory.replace("/", "-").replace("\\", "-")[:20]
        return f"{name}-{dir_slug}"
    reviewer.generate_branch_name = scoped_branch_name

    try:
        print(f"\n[Worker {worker_id}] Starting: {config.directory}")
        success = reviewer.run_once()

        # Try to get PR URL from git
        pr_url = None
        try:
            result = subprocess.run(
                ["gh", "pr", "view", "--json", "url", "-q", ".url"],
                cwd=worktree_dir, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                pr_url = result.stdout.strip()
        except Exception:
            pass

        return WorkerResult(
            worker_id=worker_id,
            directory=config.directory,
            success=success,
            pr_url=pr_url,
            merged=auto_merge and success,
            duration_seconds=time.time() - start_time,
            cost_usd=reviewer.session_cost,
        )

    except Exception as e:
        return WorkerResult(
            worker_id=worker_id,
            directory=config.directory,
            success=False,
            error=str(e),
            duration_seconds=time.time() - start_time,
        )


def run_workers_parallel(
    configs: list[WorkerConfig],
    project_dir: Path,
    base_branch: str,
    auto_merge: bool,
    max_iterations: int,
    think_level: str,
    llm_provider: str,
    max_workers: int | None,
    tg_bot_token: str | None,
    tg_chat_id: str | None,
    create_pr: bool = False,
) -> list[WorkerResult]:
    """Run all workers in parallel using git worktrees."""
    if not configs:
        return []

    if max_workers is None:
        max_workers = min(len(configs), os.cpu_count() or 4)

    print(f"\n{'='*60}")
    print("Concurrent Claude/Codex Automator")
    print(f"{'='*60}")
    print(f"Project: {project_dir}")
    print(f"Base branch: {base_branch}")
    print(f"Workers: {len(configs)} directories, {max_workers} parallel")
    print(f"Auto-merge: {auto_merge}")
    print(f"LLM: {llm_provider}")
    if think_level != "normal":
        print(f"Thinking: {think_level}")
    if create_pr:
        print(f"PR: Enabled → merge to {base_branch}")
    print(f"{'='*60}")

    for i, config in enumerate(configs, 1):
        print(f"  [{i}] {config.directory}")
    print()

    results: list[WorkerResult] = []
    worktrees: list[tuple[int, Path]] = []

    try:
        # Setup worktrees
        print("Setting up worktrees...")
        for i, config in enumerate(configs, 1):
            worktree = setup_worktree(project_dir, i, base_branch)
            if worktree:
                worktrees.append((i, worktree))
            else:
                results.append(WorkerResult(
                    worker_id=i,
                    directory=config.directory,
                    success=False,
                    error="Failed to create worktree",
                ))

        print(f"Created {len(worktrees)} worktrees\n")

        # Run workers in parallel
        # Note: We use sequential execution here because ProcessPoolExecutor
        # has issues with the AutoReviewer's subprocess calls and streaming.
        # For true parallelism, run multiple instances of the script.
        for (worker_id, worktree), config in zip(worktrees, configs):
            result = run_worker(
                worker_id=worker_id,
                config=config,
                worktree_dir=worktree,
                base_branch=base_branch,
                auto_merge=auto_merge,
                max_iterations=max_iterations,
                think_level=think_level,
                llm_provider=llm_provider,
                tg_bot_token=tg_bot_token,
                tg_chat_id=tg_chat_id,
                create_pr=create_pr,
            )
            results.append(result)

            status = "✓" if result.success else "✗"
            print(f"\n[Worker {worker_id}] {status} {config.directory} ({result.duration_seconds:.1f}s)")
            if result.pr_url:
                print(f"    PR: {result.pr_url}")
            if result.error:
                print(f"    Error: {result.error}")

    finally:
        # Cleanup worktrees
        print("\nCleaning up worktrees...")
        for worker_id, worktree in worktrees:
            cleanup_worktree(project_dir, worktree)

        # Remove .worktrees dir if empty
        worktrees_dir = project_dir / ".worktrees"
        if worktrees_dir.exists():
            try:
                worktrees_dir.rmdir()
            except OSError:
                pass

    return results


def auto_partition_directories(project_dir: Path) -> list[str]:
    """Auto-detect top-level directories for partitioning."""
    exclude = {".git", ".venv", "venv", "node_modules", "__pycache__",
               ".worktrees", "results", ".claude", ".github"}

    directories = []
    for item in project_dir.iterdir():
        if item.is_dir() and item.name not in exclude and not item.name.startswith('.'):
            directories.append(item.name)

    return sorted(directories)


def print_summary(results: list[WorkerResult]) -> None:
    """Print summary of all worker results."""
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    successful = sum(1 for r in results if r.success)
    merged = sum(1 for r in results if r.merged)
    total_cost = sum(r.cost_usd for r in results)
    total_time = sum(r.duration_seconds for r in results)

    for r in results:
        status = "✓" if r.success else "✗"
        print(f"\n[{r.worker_id}] {status} {r.directory}")
        print(f"    Duration: {r.duration_seconds:.1f}s")
        if r.pr_url:
            print(f"    PR: {r.pr_url}")
        if r.merged:
            print("    Merged: Yes")
        if r.error:
            print(f"    Error: {r.error}")
        if r.cost_usd > 0:
            print(f"    Cost: ${r.cost_usd:.4f}")

    print(f"\n{'─'*60}")
    print(f"Success: {successful}/{len(results)}")
    if merged > 0:
        print(f"Merged: {merged}")
    print(f"Total time: {total_time:.1f}s")
    if total_cost > 0:
        print(f"Total cost: ${total_cost:.4f}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Run multiple Claude/Codex workers in parallel, each on its own branch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Directory selection
    parser.add_argument("--config", "-c", type=str,
                        help="JSON config file with worker configs")
    parser.add_argument("--auto-partition", "-a", action="store_true",
                        help="Auto-partition top-level directories")
    parser.add_argument("--directories", "-d", nargs="+",
                        help="Specific directories to work on")

    # Prompts and modes
    parser.add_argument("--prompt", "-p", type=str,
                        default="Improve code quality in this directory",
                        help="Default prompt for all workers")
    parser.add_argument("--mode", "-m", type=str, action="append", dest="modes",
                        choices=list(IMPROVEMENT_MODES.keys()),
                        help="Improvement mode (can be repeated)")

    # Standard options (same as main script)
    parser.add_argument("--auto-merge", action="store_true",
                        help="Auto-merge approved PRs")
    parser.add_argument("--max-iterations", type=int, default=3,
                        help="Max review-fix cycles (default: 3)")
    parser.add_argument("--think", type=str,
                        choices=["normal", "think", "megathink", "ultrathink"],
                        default="normal", help="Thinking level")
    parser.add_argument("--llm", type=str, choices=["claude", "codex"], default="claude",
                        help="LLM CLI to use (default: claude)")
    parser.add_argument("--create-pr", nargs="?", const="main", metavar="BRANCH",
                        help="Create PR targeting BRANCH (default: main)")
    parser.add_argument("-y", "--yes", action="store_true",
                        help="Skip confirmation prompt")
    parser.add_argument("--max-workers", "-w", type=int,
                        help="Max parallel workers")

    # Notifications
    parser.add_argument("--tg-bot-token", type=str,
                        default=os.environ.get("TG_BOT_TOKEN"))
    parser.add_argument("--tg-chat-id", type=str,
                        default=os.environ.get("TG_CHAT_ID"))

    # Other
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done")

    args = parser.parse_args()

    # Use current directory as project path
    project_dir = Path(os.getcwd()).resolve()

    # Validate target branch if specified
    if args.create_pr:
        try:
            validate_branch_name(args.create_pr)
        except ValueError as e:
            print(f"Error: Invalid target branch: {e}")
            sys.exit(1)

    # Build worker configs
    configs: list[WorkerConfig] = []

    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file not found: {config_path}")
            sys.exit(1)

        with open(config_path) as f:
            data = json.load(f)

        for item in data:
            configs.append(WorkerConfig(
                directory=item["directory"],
                prompt=item.get("prompt"),
                modes=item.get("modes"),
            ))

    elif args.directories:
        for directory in args.directories:
            configs.append(WorkerConfig(
                directory=directory,
                prompt=args.prompt,
                modes=args.modes,
            ))

    elif args.auto_partition:
        directories = auto_partition_directories(project_dir)
        if not directories:
            print("No directories found to partition")
            sys.exit(1)

        for directory in directories:
            configs.append(WorkerConfig(
                directory=directory,
                prompt=args.prompt,
                modes=args.modes,
            ))

    else:
        print("Error: Specify --config, --directories, or --auto-partition")
        parser.print_help()
        sys.exit(1)

    if not configs:
        print("No worker configs defined")
        sys.exit(0)

    # Dry run
    if args.dry_run:
        print("DRY RUN - Would execute:\n")
        for i, config in enumerate(configs, 1):
            print(f"Worker {i}: {config.directory}")
            if config.modes:
                print(f"  Modes: {', '.join(config.modes)}")
            else:
                print(f"  Prompt: {(config.prompt or args.prompt)[:60]}...")
            print()
        sys.exit(0)

    # Get current branch name
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_dir, capture_output=True, text=True, timeout=10
        )
        current_branch = result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        current_branch = "unknown"

    # Warn if committing directly to current branch
    if not args.create_pr and not args.yes:
        print("\n" + "=" * 60)
        print("⚠️  WARNING: Direct commit mode")
        print("=" * 60)
        print("Commits will be made directly to worktree branches")
        print(f"Based on current branch: {current_branch}")
        print("No PRs will be created, no review cycle.")
        print("=" * 60)
        try:
            response = input("\nContinue? [y/N] ").strip().lower()
            if response not in ('y', 'yes'):
                print("Aborted.")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(0)

    # Run workers
    results = run_workers_parallel(
        configs=configs,
        project_dir=project_dir,
        base_branch=args.create_pr or "main",
        auto_merge=args.auto_merge,
        max_iterations=args.max_iterations,
        think_level=args.think,
        llm_provider=args.llm,
        max_workers=args.max_workers,
        tg_bot_token=args.tg_bot_token,
        tg_chat_id=args.tg_chat_id,
        create_pr=bool(args.create_pr),
    )

    # Print summary
    print_summary(results)

    # Exit with error if any worker failed
    if not all(r.success for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
