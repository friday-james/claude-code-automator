#!/usr/bin/env python3
"""
Code Audit - GPT-5.2 reviews your code and directs Claude to fix it.

Usage:
    audit path/to/file.py                        # Audit once (default)
    audit src/ --until-complete                  # Audit until GPT-5.2 says complete
    audit . --goal "security"                    # Focus audit on security issues
    audit . --goal "performance" --until-complete # Loop until performance is optimized
    audit . --ai-model gpt-5.2                   # Use specific GPT-5 model
    audit . --ai-model gpt-4o-mini               # Use GPT-4 (cheaper testing)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Tuple


def read_target(target_path: Path) -> str:
    """Read the target file or directory contents."""
    if target_path.is_file():
        try:
            return target_path.read_text()
        except Exception as e:
            return f"[Error reading {target_path}: {e}]"
    elif target_path.is_dir():
        # Read all relevant files in directory
        contents = []
        for ext in ['.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.c', '.cpp', '.h']:
            for file_path in target_path.rglob(f'*{ext}'):
                if '.git' not in str(file_path) and 'node_modules' not in str(file_path):
                    try:
                        content = file_path.read_text()
                        contents.append(f"=== {file_path.relative_to(target_path)} ===\n{content}\n")
                    except Exception:
                        pass
        return "\n".join(contents) if contents else "[No readable files found]"
    else:
        return "[Target not found]"


def ask_gpt5(content: str, context: str, model: str = "gpt-5.2", goal: str | None = None, reasoning_effort: str = "high") -> str | None:
    """Send content to GPT-5/GPT-4 for audit and get instructions for Claude."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return None

    try:
        # Add goal-specific instructions if provided
        goal_instruction = ""
        if goal:
            goal_instruction = f"\n**AUDIT FOCUS**: {goal}\nPrioritize finding issues related to this goal.\n"

        prompt = f"""You are a code auditor working with Claude Code (an AI coding assistant).

Your job is to:
1. Review the code below
2. Identify issues, bugs, improvements, or areas that need work
3. Generate SPECIFIC, ACTIONABLE instructions for Claude Code to execute
{goal_instruction}
{context}

Code to audit:
```
{content[:30000]}
```

Respond in this EXACT format:

ISSUES_FOUND: YES or NO
CONTINUE: YES or NO

INSTRUCTIONS_FOR_CLAUDE:
(If CONTINUE is YES, write detailed, specific instructions for what Claude should do.
Make it actionable - "Add error handling to function X", "Fix the bug in line Y", etc.
If CONTINUE is NO or ISSUES_FOUND is NO, write "N/A")

Be specific and direct. Claude will execute these instructions.
"""

        # Use Responses API for GPT-5 models, Chat Completions for GPT-4
        is_gpt5 = model.startswith("gpt-5")

        if is_gpt5:
            url = "https://api.openai.com/v1/responses"
            data = {
                "model": model,
                "input": prompt,
                "reasoning": {
                    "effort": reasoning_effort  # Configurable reasoning effort
                },
                "text": {
                    "verbosity": "medium"
                },
                "max_output_tokens": 16384,
                "stream": True  # Enable streaming to avoid timeouts
            }
        else:
            # GPT-4 models use Chat Completions API
            url = "https://api.openai.com/v1/chat/completions"
            data = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 4096
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

        print(f"🔍 Sending to {model} for audit...")

        # GPT-5 models can take longer, especially with high reasoning effort
        # With streaming, we get chunks as they arrive (no timeout issues)
        timeout = 600 if is_gpt5 else 120

        with urllib.request.urlopen(req, timeout=timeout) as response:
            if is_gpt5 and data.get("stream"):
                # Handle streaming response (Server-Sent Events)
                output_chunks = []
                print("💭 Streaming response...", flush=True)

                for line in response:
                    line = line.decode('utf-8').strip()

                    # SSE format: "data: {...}"
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove "data: " prefix

                        if data_str == '[DONE]':
                            break

                        try:
                            chunk_data = json.loads(data_str)
                            chunk_type = chunk_data.get("type", "")

                            # Collect output deltas
                            if chunk_type == "response.output.delta":
                                delta = chunk_data.get("delta", "")
                                if delta:
                                    output_chunks.append(delta)
                                    print(".", end="", flush=True)  # Progress indicator

                            # Final response
                            elif chunk_type == "response.done":
                                response_obj = chunk_data.get("response", {})
                                if response_obj.get("output"):
                                    # Prefer complete output from response.done
                                    print("\n✓ Stream complete", flush=True)
                                    return response_obj["output"]
                        except json.JSONDecodeError:
                            continue

                # Fallback to assembled chunks
                if output_chunks:
                    print("\n✓ Stream complete", flush=True)
                    return "".join(output_chunks)

                print("\n⚠️  No output in stream", flush=True)
                return None
            else:
                # Non-streaming response (GPT-4 or non-stream GPT-5)
                result = json.loads(response.read().decode('utf-8'))

                if is_gpt5:
                    if result.get("output"):
                        return result["output"]
                else:
                    # GPT-4 response format
                    if result.get("choices") and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]

                print(f"Error: No output from {model}")
                return None

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ""
        print(f"HTTP {e.code} error: {error_body[:500]}")
        return None
    except urllib.error.URLError as e:
        print(f"URL error: {e.reason}")
        return None
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return None


def run_claude_with_instructions(instructions: str, project_dir: Path) -> Tuple[bool, str]:
    """Run Claude Code with the given instructions."""
    print(f"\n{'='*60}")
    print("🤖 Running Claude Code with instructions:")
    print(f"{'='*60}")
    print(instructions[:500] + ("..." if len(instructions) > 500 else ""))
    print(f"{'='*60}\n")

    # Write instructions to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(instructions)
        temp_file = f.name

    try:
        # Run claude with the instructions
        cmd = ["bash", "-c", f"claude --print < '{temp_file}'"]

        process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                continue

            print(line, end="", flush=True)
            output_lines.append(line)

        success = process.returncode == 0
        summary = "".join(output_lines[-100:]) if output_lines else ""

        return success, summary

    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def parse_audit_response(response: str) -> Tuple[bool, bool, str]:
    """Parse the GPT-5.2 audit response.

    Returns:
        (issues_found, should_continue, instructions)
    """
    issues_found = False
    should_continue = False
    instructions = None

    lines = response.split('\n')
    in_instructions_section = False
    instruction_lines = []

    for line in lines:
        line_stripped = line.strip()

        if line_stripped.startswith('ISSUES_FOUND:'):
            value = line_stripped.split(':', 1)[1].strip().upper()
            issues_found = 'YES' in value
            in_instructions_section = False
        elif line_stripped.startswith('CONTINUE:'):
            value = line_stripped.split(':', 1)[1].strip().upper()
            should_continue = 'YES' in value
            in_instructions_section = False
        elif line_stripped.startswith('INSTRUCTIONS_FOR_CLAUDE:'):
            in_instructions_section = True
            # Check if instructions on same line
            rest = line_stripped.split(':', 1)[1].strip()
            if rest and rest.upper() != 'N/A':
                instruction_lines.append(rest)
        elif in_instructions_section:
            if line_stripped and line_stripped.upper() != 'N/A':
                instruction_lines.append(line)

    if instruction_lines:
        instructions = '\n'.join(instruction_lines).strip()
        if instructions.upper() == 'N/A':
            instructions = None

    return issues_found, should_continue, instructions


def main():
    parser = argparse.ArgumentParser(
        description="GPT-5.2 audits your code and directs Claude Code to fix it",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", type=str, help="File or directory to audit")
    parser.add_argument("--until-complete", action="store_true", help="Loop until GPT-5.2 determines all issues are fixed (default: run once)")
    parser.add_argument("--goal", "-g", type=str, help="Custom audit goal/focus (e.g., 'security', 'performance', 'code style')")
    parser.add_argument("--ai-model", type=str, default="gpt-5.2",
                       help="AI model: gpt-5.2 (default), gpt-5.2-pro, gpt-5-mini, gpt-4o, gpt-4o-mini")
    parser.add_argument("--reasoning", type=str, default="high", choices=["none", "low", "medium", "high", "xhigh"],
                       help="GPT-5 reasoning effort (default: high). Use 'medium' or 'low' for faster responses.")

    args = parser.parse_args()

    # Validate target exists
    target_path = Path(args.target).resolve()
    if not target_path.exists():
        print(f"Error: Target not found: {target_path}")
        sys.exit(1)

    project_dir = target_path.parent if target_path.is_file() else target_path

    # Check for OPENAI_API_KEY
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Get your API key from: https://platform.openai.com/api-keys")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Code Audit with {args.ai_model}")
    print(f"{'='*60}")
    print(f"Target: {target_path}")
    if args.goal:
        print(f"Goal: {args.goal}")
    print(f"Mode: {'Loop until complete' if args.until_complete else 'Single run'}")
    print(f"{'='*60}\n")

    iteration = 0
    max_iterations = 10 if args.until_complete else 1

    while iteration < max_iterations:
        iteration += 1
        print(f"\n{'#'*60}")
        print(f"# Iteration {iteration}")
        print(f"{'#'*60}\n")

        # Read current state of target
        content = read_target(target_path)

        # Send to GPT-5.2 for audit
        context = f"This is iteration {iteration}. Previous iterations may have made changes."
        audit_response = ask_gpt5(content, context, args.ai_model, args.goal, args.reasoning)

        if not audit_response:
            print("❌ Failed to get audit response from GPT-5.2")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"📋 {args.ai_model} Audit Result:")
        print(f"{'='*60}")
        print(audit_response)
        print(f"{'='*60}\n")

        # Parse response
        issues_found, should_continue, instructions = parse_audit_response(audit_response)

        if not issues_found:
            print("✅ No issues found! Code looks good.")
            break

        if not should_continue:
            print("✅ Audit complete!")
            break

        if not instructions:
            print("⚠️  No instructions provided by auditor")
            break

        # Run Claude with instructions
        success, summary = run_claude_with_instructions(instructions, project_dir)

        if not success:
            print("❌ Claude Code failed to execute instructions")
            if args.until_complete:
                print("Continuing to next iteration anyway...")
            else:
                sys.exit(1)

        print(f"\n✓ Iteration {iteration} complete")

        if not args.until_complete:
            break

    if iteration >= max_iterations:
        print(f"\n⚠️  Reached max iterations ({max_iterations})")

    print("\n✓ Audit complete!")
    sys.exit(0)


if __name__ == "__main__":
    main()
