"""
Ralph CLI - Command line interface for the Ralph agent.

Usage:
    ralph run "Your task description here"
    ralph run --prompt prompt.md --dir ./my-project
    ralph run --prompt prompt.md --max-iterations 10
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from .agent import run_ralph


def main():
    parser = argparse.ArgumentParser(
        description="Ralph: An autonomous coding agent that runs in a loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with inline prompt
  ralph run "Port this Python 2 codebase to Python 3"

  # Run with prompt file
  ralph run --prompt prompt.md

  # Run in a specific directory with max iterations
  ralph run --prompt prompt.md --dir ./my-project --max-iterations 50

  # Run with custom scratchpad directory
  ralph run "Refactor the auth module" --scratchpad .ralph
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run Ralph on a task")
    run_parser.add_argument(
        "task",
        nargs="?",
        help="The task to work on (inline prompt)",
    )
    run_parser.add_argument(
        "--prompt", "-p",
        help="Path to a prompt file (.md)",
    )
    run_parser.add_argument(
        "--dir", "-d",
        default=".",
        help="Working directory (default: current directory)",
    )
    run_parser.add_argument(
        "--scratchpad", "-s",
        default=".agent",
        help="Scratchpad directory for notes/TODOs (default: .agent)",
    )
    run_parser.add_argument(
        "--max-iterations", "-n",
        type=int,
        default=None,
        help="Maximum iterations (default: unlimited)",
    )

    # Init command - creates a prompt template
    init_parser = subparsers.add_parser("init", help="Initialize a Ralph project")
    init_parser.add_argument(
        "--template",
        choices=["port", "maintain", "refactor", "custom"],
        default="custom",
        help="Prompt template to use",
    )

    args = parser.parse_args()

    if args.command == "run":
        # Get prompt from either inline arg or file
        if args.task:
            prompt = args.task
        elif args.prompt:
            prompt_path = Path(args.prompt)
            if not prompt_path.exists():
                print(f"Error: Prompt file not found: {args.prompt}")
                sys.exit(1)
            prompt = prompt_path.read_text()
        else:
            print("Error: Please provide a task or --prompt file")
            parser.print_help()
            sys.exit(1)

        # Run Ralph
        asyncio.run(
            run_ralph(
                prompt=prompt,
                working_dir=args.dir,
                scratchpad_dir=args.scratchpad,
                max_iterations=args.max_iterations,
            )
        )

    elif args.command == "init":
        init_project(args.template)

    else:
        parser.print_help()


def init_project(template: str):
    """Initialize a Ralph project with prompt templates."""
    agent_dir = Path(".agent")
    agent_dir.mkdir(exist_ok=True)

    templates = {
        "port": """Your job is to port {SOURCE_REPO} ({SOURCE_LANG}) to {TARGET_REPO} ({TARGET_LANG}).

Make a commit and push your changes after every single file edit.

Use the .agent/ directory as a scratchpad for your work:
- Store long term plans in .agent/PLAN.md
- Track progress in .agent/TODO.md

When porting:
1. Start by analyzing the source codebase structure
2. Create a comprehensive porting plan
3. Port one module at a time, testing as you go
4. Write tests for critical functionality (aim for 20% of your time on tests)

The original project was tested manually. When porting, write end-to-end and unit tests.
""",
        "maintain": """Your job is to maintain the {REPO_NAME} repository.

Review open issues and PRs, fix bugs, and improve the codebase.

Make a commit and push your changes after every meaningful edit.

Use .agent/ for tracking:
- .agent/TODO.md for current tasks
- .agent/DECISIONS.md for architectural decisions

Focus on:
1. Fixing bugs reported in issues
2. Improving test coverage
3. Updating documentation
4. Code quality improvements
""",
        "refactor": """Your job is to refactor {TARGET_AREA} in this codebase.

Goals:
- Improve code quality and maintainability
- Add or improve tests
- Update documentation

Make a commit after each meaningful change.

Track your progress in .agent/TODO.md

Approach:
1. Analyze the current implementation
2. Create a refactoring plan in .agent/PLAN.md
3. Refactor incrementally with tests
4. Document changes
""",
        "custom": """Your job is to {DESCRIBE_YOUR_TASK}.

Make a commit and push your changes after every single file edit.

Use the .agent/ directory as a scratchpad:
- .agent/TODO.md - Track progress
- .agent/PLAN.md - Long-term plans
- .agent/NOTES.md - Observations and decisions

{ADD_YOUR_SPECIFIC_INSTRUCTIONS}
""",
    }

    prompt_content = templates.get(template, templates["custom"])
    prompt_path = Path("prompt.md")
    prompt_path.write_text(prompt_content)

    # Create initial TODO.md
    todo_path = agent_dir / "TODO.md"
    todo_path.write_text("""# Ralph TODO

## Current Status
Not started - waiting for first iteration.

## Next Steps
- [ ] Analyze the codebase
- [ ] Create implementation plan
- [ ] Begin work

## Completed
(none yet)
""")

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                  RALPH PROJECT INITIALIZED                    ║
╚══════════════════════════════════════════════════════════════╝

Created:
  - prompt.md (edit this with your task)
  - .agent/TODO.md (Ralph will track progress here)

To start Ralph:
  ralph run --prompt prompt.md

Or run with a custom iteration limit:
  ralph run --prompt prompt.md --max-iterations 50
""")


if __name__ == "__main__":
    main()
