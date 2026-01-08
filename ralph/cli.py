"""
Ralph CLI - Command line interface for the Ralph agent.

Usage:
    ralph run "Your task description here"
    ralph run --prompt prompt.md --dir ./my-project
    ralph run --prompt prompt.md --max-iterations 10
    ralph run --prompt prompt.md --telegram --name "my-agent"
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from .agent import RalphAgent
from .display import display


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
    run_parser.add_argument(
        "--telegram", "-t",
        action="store_true",
        help="Enable Telegram monitoring and control",
    )
    run_parser.add_argument(
        "--name",
        help="Agent name for identification (default: working directory name)",
    )

    # Init command - creates a prompt template
    init_parser = subparsers.add_parser("init", help="Initialize a Ralph project")
    init_parser.add_argument(
        "--template",
        choices=["port", "maintain", "refactor", "custom"],
        default="custom",
        help="Prompt template to use",
    )

    # Telegram command
    telegram_parser = subparsers.add_parser("telegram", help="Telegram integration commands")
    telegram_subparsers = telegram_parser.add_subparsers(dest="telegram_command", help="Telegram commands")

    telegram_subparsers.add_parser("setup", help="Interactive setup for Telegram")
    telegram_subparsers.add_parser("test", help="Test Telegram connection")
    telegram_subparsers.add_parser("config", help="Show/create notification config")

    args = parser.parse_args()

    if args.command == "run":
        # Get prompt from either inline arg or file
        if args.task:
            prompt = args.task
        elif args.prompt:
            prompt_path = Path(args.prompt)
            if not prompt_path.exists():
                display.print_error(f"Prompt file not found: {args.prompt}")
                sys.exit(1)
            prompt = prompt_path.read_text()
        else:
            display.print_error("Please provide a task or --prompt file")
            parser.print_help()
            sys.exit(1)

        # Set up Telegram if requested
        telegram_handler = None
        if args.telegram:
            from .telegram import TelegramHandler
            from .telegram_config import TelegramConfig

            config = TelegramConfig.load()
            if not config.is_configured:
                display.print_error(
                    "Telegram not configured. Set environment variables:\n"
                    "  RALPH_TELEGRAM_TOKEN=<your_bot_token>\n"
                    "  RALPH_TELEGRAM_CHAT_ID=<your_chat_id>\n"
                    "  RALPH_TELEGRAM_USER_ID=<your_user_id>\n\n"
                    "Or run 'ralph telegram setup' for interactive setup."
                )
                sys.exit(1)
            telegram_handler = TelegramHandler(config)

        # Run Ralph
        agent = RalphAgent(
            prompt=prompt,
            working_dir=args.dir,
            scratchpad_dir=args.scratchpad,
            max_iterations=args.max_iterations,
            name=args.name,
            telegram_handler=telegram_handler,
        )
        asyncio.run(agent.run())

    elif args.command == "init":
        init_project(args.template)

    elif args.command == "telegram":
        handle_telegram_command(args)

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

    display.print_init_success()


def handle_telegram_command(args):
    """Handle telegram subcommands."""
    from .telegram import test_connection
    from .telegram_config import TelegramConfig, create_default_config, get_config_path

    if args.telegram_command == "setup":
        telegram_setup()

    elif args.telegram_command == "test":
        config = TelegramConfig.load()
        if not config.is_configured:
            display.print_error(
                "Telegram not configured. Set environment variables first:\n"
                "  RALPH_TELEGRAM_TOKEN=<your_bot_token>\n"
                "  RALPH_TELEGRAM_CHAT_ID=<your_chat_id>\n"
                "  RALPH_TELEGRAM_USER_ID=<your_user_id>"
            )
            sys.exit(1)

        display.print_info("Testing Telegram connection...")
        success = asyncio.run(test_connection(config))
        if success:
            display.print_info("Connection successful! Check your Telegram chat.")
        else:
            display.print_error("Connection failed. Check your credentials.")
            sys.exit(1)

    elif args.telegram_command == "config":
        create_default_config()
        config_path = get_config_path()
        display.print_info(f"Notification config: {config_path}")
        if config_path.exists():
            print(config_path.read_text())
        else:
            display.print_warning("Config file not found.")

    else:
        display.print_error("Usage: ralph telegram [setup|test|config]")


def telegram_setup():
    """Interactive Telegram setup."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    console.print(Panel.fit(
        "[bold cyan]Ralph Telegram Setup[/bold cyan]\n\n"
        "This will guide you through setting up Telegram integration.",
        border_style="cyan",
    ))

    console.print("\n[bold]Step 1: Create a Telegram Bot[/bold]")
    console.print("1. Open Telegram and search for @BotFather")
    console.print("2. Send /newbot and follow the instructions")
    console.print("3. Copy the bot token (looks like: 123456789:ABCdefGHI...)")
    console.print()

    console.print("[bold]Step 2: Get your Chat ID[/bold]")
    console.print("1. Start a chat with your new bot")
    console.print("2. Send any message to the bot")
    console.print("3. Visit: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates")
    console.print("4. Find 'chat':{'id': YOUR_CHAT_ID} in the response")
    console.print()

    console.print("[bold]Step 3: Get your User ID[/bold]")
    console.print("Your user ID is in the same response as the chat ID.")
    console.print("Look for 'from':{'id': YOUR_USER_ID}")
    console.print()

    console.print("[bold]Step 4: Set Environment Variables[/bold]")
    console.print("Add these to your shell profile (~/.bashrc, ~/.zshrc, etc.):\n")
    console.print("[green]export RALPH_TELEGRAM_TOKEN='your_bot_token'[/green]")
    console.print("[green]export RALPH_TELEGRAM_CHAT_ID='your_chat_id'[/green]")
    console.print("[green]export RALPH_TELEGRAM_USER_ID='your_user_id'[/green]")
    console.print()

    console.print("[bold]Step 5: Test the connection[/bold]")
    console.print("Run: [cyan]ralph telegram test[/cyan]")
    console.print()

    console.print("[bold]Step 6: Configure notifications (optional)[/bold]")
    console.print("Run: [cyan]ralph telegram config[/cyan]")
    console.print("Edit ~/.ralph/notifications.yaml to customize when you get notified.")


if __name__ == "__main__":
    main()
