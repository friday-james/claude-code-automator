#!/usr/bin/env python3
"""
Concurrent Claude Automator - Run multiple Claude workers in parallel.

Each worker is assigned ONE directory to work on, preventing race conditions.
No locks needed - isolation by directory partitioning.

Usage:
    # Run with default directory assignments
    ./claude_automator_concurrent.py --workers 3

    # Custom directory/prompt assignments via config
    ./claude_automator_concurrent.py --config workers.json

    # Quick mode: auto-partition top-level directories
    ./claude_automator_concurrent.py --auto-partition --prompt "Fix bugs in this directory"

Example workers.json:
[
    {"directory": "src", "prompt": "Fix bugs in this directory"},
    {"directory": "scripts", "prompt": "Add type hints to all functions"},
    {"directory": "strategies", "prompt": "Optimize performance"}
]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import string
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class WorkerTask:
    """A task for a single worker."""
    directory: str  # Relative path from project root
    prompt: str
    worker_id: int = 0
    branch_name: str = ""


@dataclass
class WorkerResult:
    """Result from a worker execution."""
    worker_id: int
    directory: str
    branch_name: str
    success: bool
    output: str
    duration_seconds: float
    commits: list[str] = field(default_factory=list)
    cost_usd: float = 0.0


def generate_branch_name(worker_id: int, directory: str) -> str:
    """Generate unique branch name for a worker."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
    dir_slug = directory.replace("/", "-").replace("\\", "-")[:20]
    return f"auto-worker{worker_id}-{dir_slug}/{timestamp}-{suffix}"


def run_worker(task: WorkerTask, project_dir: Path, base_branch: str) -> WorkerResult:
    """
    Execute a single worker task.

    Each worker:
    1. Creates its own branch
    2. Runs Claude scoped to its directory
    3. Returns results (does NOT create PR - coordinator handles that)
    """
    start_time = time.time()

    # Generate branch name
    branch_name = generate_branch_name(task.worker_id, task.directory)
    target_dir = project_dir / task.directory

    # Validate directory exists
    if not target_dir.is_dir():
        return WorkerResult(
            worker_id=task.worker_id,
            directory=task.directory,
            branch_name=branch_name,
            success=False,
            output=f"Directory does not exist: {target_dir}",
            duration_seconds=time.time() - start_time,
        )

    # Create branch
    try:
        subprocess.run(
            ["git", "checkout", base_branch],
            cwd=project_dir, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "pull", "--rebase"],
            cwd=project_dir, capture_output=True, timeout=60
        )
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=project_dir, capture_output=True, check=True
        )
    except subprocess.CalledProcessError as e:
        return WorkerResult(
            worker_id=task.worker_id,
            directory=task.directory,
            branch_name=branch_name,
            success=False,
            output=f"Git error: {e.stderr.decode() if e.stderr else str(e)}",
            duration_seconds=time.time() - start_time,
        )

    # Build scoped prompt
    scoped_prompt = f"""You are working ONLY on the directory: {task.directory}

IMPORTANT CONSTRAINTS:
- You may ONLY modify files within: {task.directory}/
- Do NOT touch any files outside this directory
- Do NOT modify files in other directories, even if they seem related
- If you need to import from other directories, that's fine, but don't edit those files

YOUR TASK:
{task.prompt}

After making changes:
- Commit each logical change separately
- Use conventional commit messages (feat:, fix:, refactor:, etc.)
- Include the directory name in the commit message for clarity
"""

    # Run Claude
    try:
        result = subprocess.run(
            ["claude", "--print", "--output-format", "json"],
            input=scoped_prompt,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 min timeout per worker
        )
        output = result.stdout
        success = result.returncode == 0

        # Parse cost if available
        cost_usd = 0.0
        try:
            data = json.loads(output)
            cost_usd = data.get("total_cost_usd", 0.0)
        except (json.JSONDecodeError, TypeError):
            pass

    except subprocess.TimeoutExpired:
        output = "Claude timed out after 30 minutes"
        success = False
        cost_usd = 0.0
    except FileNotFoundError:
        output = "Claude CLI not found"
        success = False
        cost_usd = 0.0

    # Get commits made
    commits = []
    try:
        log_result = subprocess.run(
            ["git", "log", "--oneline", f"{base_branch}..HEAD"],
            cwd=project_dir, capture_output=True, text=True
        )
        if log_result.returncode == 0:
            commits = [line.strip() for line in log_result.stdout.strip().split('\n') if line.strip()]
    except Exception:
        pass

    return WorkerResult(
        worker_id=task.worker_id,
        directory=task.directory,
        branch_name=branch_name,
        success=success,
        output=output[:5000],  # Truncate long outputs
        duration_seconds=time.time() - start_time,
        commits=commits,
        cost_usd=cost_usd,
    )


def run_concurrent_workers(
    tasks: list[WorkerTask],
    project_dir: Path,
    base_branch: str = "main",
    max_workers: int | None = None,
) -> list[WorkerResult]:
    """
    Run multiple workers concurrently.

    Each worker gets its own branch and directory scope.
    Results are collected after all complete.
    """
    if not tasks:
        return []

    # Assign worker IDs
    for i, task in enumerate(tasks):
        task.worker_id = i + 1

    # Default to number of tasks (each runs in parallel)
    if max_workers is None:
        max_workers = len(tasks)

    print(f"\n{'='*60}")
    print(f"Concurrent Claude Automator")
    print(f"{'='*60}")
    print(f"Project: {project_dir}")
    print(f"Base branch: {base_branch}")
    print(f"Workers: {len(tasks)} tasks, {max_workers} parallel")
    print(f"{'='*60}\n")

    for task in tasks:
        print(f"  Worker {task.worker_id}: {task.directory}")
        print(f"    Prompt: {task.prompt[:60]}...")
    print()

    results: list[WorkerResult] = []

    # Note: Each worker needs its own git worktree to avoid conflicts
    # For simplicity, we run sequentially but in separate branches
    # For true parallelism, use git worktree (see advanced mode below)

    # Sequential execution with separate branches (safe mode)
    print("Running workers sequentially (safe mode)...\n")
    for task in tasks:
        print(f"[Worker {task.worker_id}] Starting: {task.directory}")
        result = run_worker(task, project_dir, base_branch)
        results.append(result)

        status = "✓" if result.success else "✗"
        print(f"[Worker {task.worker_id}] {status} Completed in {result.duration_seconds:.1f}s")
        if result.commits:
            print(f"    Commits: {len(result.commits)}")
        print()

    return results


def run_concurrent_workers_parallel(
    tasks: list[WorkerTask],
    project_dir: Path,
    base_branch: str = "main",
    max_workers: int | None = None,
) -> list[WorkerResult]:
    """
    Run workers truly in parallel using git worktrees.

    This creates temporary worktrees for each worker, allowing
    true concurrent execution without git conflicts.
    """
    if not tasks:
        return []

    # Assign worker IDs
    for i, task in enumerate(tasks):
        task.worker_id = i + 1

    if max_workers is None:
        max_workers = min(len(tasks), os.cpu_count() or 4)

    print(f"\n{'='*60}")
    print(f"Concurrent Claude Automator (Parallel Mode)")
    print(f"{'='*60}")
    print(f"Project: {project_dir}")
    print(f"Base branch: {base_branch}")
    print(f"Workers: {len(tasks)} tasks, {max_workers} parallel")
    print(f"{'='*60}\n")

    worktree_base = project_dir / ".worktrees"
    worktree_base.mkdir(exist_ok=True)

    results: list[WorkerResult] = []
    worktrees_created: list[Path] = []

    try:
        # Create worktrees for each worker
        for task in tasks:
            branch_name = generate_branch_name(task.worker_id, task.directory)
            task.branch_name = branch_name
            worktree_path = worktree_base / f"worker-{task.worker_id}"

            # Create branch and worktree
            subprocess.run(
                ["git", "branch", branch_name, base_branch],
                cwd=project_dir, capture_output=True
            )
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), branch_name],
                cwd=project_dir, capture_output=True
            )
            worktrees_created.append(worktree_path)

        # Run workers in parallel
        def worker_fn(task: WorkerTask) -> WorkerResult:
            worktree_path = worktree_base / f"worker-{task.worker_id}"
            return run_worker_in_worktree(task, worktree_path)

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {executor.submit(worker_fn, task): task for task in tasks}

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    status = "✓" if result.success else "✗"
                    print(f"[Worker {task.worker_id}] {status} {task.directory} ({result.duration_seconds:.1f}s)")
                except Exception as e:
                    results.append(WorkerResult(
                        worker_id=task.worker_id,
                        directory=task.directory,
                        branch_name=task.branch_name,
                        success=False,
                        output=str(e),
                        duration_seconds=0,
                    ))

    finally:
        # Cleanup worktrees
        for worktree_path in worktrees_created:
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=project_dir, capture_output=True
            )
        if worktree_base.exists():
            try:
                worktree_base.rmdir()
            except OSError:
                pass

    return results


def run_worker_in_worktree(task: WorkerTask, worktree_path: Path) -> WorkerResult:
    """Run a worker in an isolated git worktree."""
    start_time = time.time()
    target_dir = worktree_path / task.directory

    if not target_dir.is_dir():
        return WorkerResult(
            worker_id=task.worker_id,
            directory=task.directory,
            branch_name=task.branch_name,
            success=False,
            output=f"Directory does not exist: {target_dir}",
            duration_seconds=time.time() - start_time,
        )

    scoped_prompt = f"""You are working ONLY on the directory: {task.directory}

IMPORTANT CONSTRAINTS:
- You may ONLY modify files within: {task.directory}/
- Do NOT touch any files outside this directory

YOUR TASK:
{task.prompt}

Commit each logical change with conventional commit messages.
"""

    try:
        result = subprocess.run(
            ["claude", "--print", "--output-format", "json"],
            input=scoped_prompt,
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        output = result.stdout
        success = result.returncode == 0

        cost_usd = 0.0
        try:
            data = json.loads(output)
            cost_usd = data.get("total_cost_usd", 0.0)
        except (json.JSONDecodeError, TypeError):
            pass

    except subprocess.TimeoutExpired:
        output = "Claude timed out"
        success = False
        cost_usd = 0.0
    except FileNotFoundError:
        output = "Claude CLI not found"
        success = False
        cost_usd = 0.0

    commits = []
    try:
        log_result = subprocess.run(
            ["git", "log", "--oneline", f"HEAD~10..HEAD"],
            cwd=worktree_path, capture_output=True, text=True
        )
        if log_result.returncode == 0:
            commits = [line.strip() for line in log_result.stdout.strip().split('\n') if line.strip()]
    except Exception:
        pass

    return WorkerResult(
        worker_id=task.worker_id,
        directory=task.directory,
        branch_name=task.branch_name,
        success=success,
        output=output[:5000],
        duration_seconds=time.time() - start_time,
        commits=commits,
        cost_usd=cost_usd,
    )


def auto_partition_directories(project_dir: Path, exclude: list[str] | None = None) -> list[str]:
    """Auto-detect top-level directories for partitioning."""
    exclude = exclude or [".git", ".venv", "venv", "node_modules", "__pycache__", ".worktrees", "results"]

    directories = []
    for item in project_dir.iterdir():
        if item.is_dir() and item.name not in exclude and not item.name.startswith('.'):
            directories.append(item.name)

    return sorted(directories)


def print_summary(results: list[WorkerResult]) -> None:
    """Print a summary of all worker results."""
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    total_commits = 0
    total_cost = 0.0
    successful = 0

    for r in results:
        status = "✓" if r.success else "✗"
        print(f"\n[Worker {r.worker_id}] {status} {r.directory}")
        print(f"  Branch: {r.branch_name}")
        print(f"  Duration: {r.duration_seconds:.1f}s")
        print(f"  Commits: {len(r.commits)}")
        if r.cost_usd > 0:
            print(f"  Cost: ${r.cost_usd:.4f}")

        if r.commits:
            for commit in r.commits[:5]:
                print(f"    - {commit}")
            if len(r.commits) > 5:
                print(f"    ... and {len(r.commits) - 5} more")

        total_commits += len(r.commits)
        total_cost += r.cost_usd
        if r.success:
            successful += 1

    print(f"\n{'─'*60}")
    print(f"Total: {successful}/{len(results)} successful")
    print(f"Total commits: {total_commits}")
    if total_cost > 0:
        print(f"Total cost: ${total_cost:.4f}")
    print(f"{'='*60}\n")

    # List branches for manual review
    if any(r.commits for r in results):
        print("Branches with changes (review and merge manually):")
        for r in results:
            if r.commits:
                print(f"  git checkout {r.branch_name}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Run multiple Claude workers concurrently, each on its own directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", "-c", type=str, help="JSON config file with worker tasks")
    parser.add_argument("--auto-partition", "-a", action="store_true",
                        help="Auto-partition top-level directories")
    parser.add_argument("--prompt", "-p", type=str,
                        default="Review and improve code quality in this directory",
                        help="Default prompt for all workers (used with --auto-partition)")
    parser.add_argument("--directories", "-d", nargs="+",
                        help="Specific directories to work on")
    parser.add_argument("--project-dir", type=str, default=os.getcwd(),
                        help="Project directory (default: current)")
    parser.add_argument("--base-branch", type=str, default="main",
                        help="Base branch (default: main)")
    parser.add_argument("--max-workers", "-w", type=int, default=None,
                        help="Max parallel workers")
    parser.add_argument("--parallel", action="store_true",
                        help="Use git worktrees for true parallelism")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without executing")

    args = parser.parse_args()
    project_dir = Path(args.project_dir).resolve()

    # Build task list
    tasks: list[WorkerTask] = []

    if args.config:
        # Load from config file
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file not found: {config_path}")
            sys.exit(1)

        with open(config_path) as f:
            config = json.load(f)

        for item in config:
            tasks.append(WorkerTask(
                directory=item["directory"],
                prompt=item.get("prompt", args.prompt),
            ))

    elif args.directories:
        # Use specified directories
        for directory in args.directories:
            tasks.append(WorkerTask(directory=directory, prompt=args.prompt))

    elif args.auto_partition:
        # Auto-detect directories
        directories = auto_partition_directories(project_dir)
        if not directories:
            print("No directories found to partition")
            sys.exit(1)

        for directory in directories:
            tasks.append(WorkerTask(directory=directory, prompt=args.prompt))

    else:
        print("Error: Specify --config, --directories, or --auto-partition")
        parser.print_help()
        sys.exit(1)

    if not tasks:
        print("No tasks to run")
        sys.exit(0)

    if args.dry_run:
        print("DRY RUN - Would execute:\n")
        for i, task in enumerate(tasks, 1):
            print(f"Worker {i}: {task.directory}")
            print(f"  Prompt: {task.prompt[:80]}...")
            print()
        sys.exit(0)

    # Run workers
    if args.parallel:
        results = run_concurrent_workers_parallel(
            tasks, project_dir, args.base_branch, args.max_workers
        )
    else:
        results = run_concurrent_workers(
            tasks, project_dir, args.base_branch, args.max_workers
        )

    # Print summary
    print_summary(results)


if __name__ == "__main__":
    main()
