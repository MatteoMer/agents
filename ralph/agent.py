"""
Ralph Agent - Core implementation using Claude Agent SDK.

Ralph runs in a continuous loop, working on tasks autonomously,
committing after each change, and tracking progress in a scratchpad.
"""

import asyncio
import glob as glob_module
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from claude_code_sdk import query, ClaudeCodeOptions, AssistantMessage, ResultMessage

from ralph.display import display

if TYPE_CHECKING:
    from ralph.telegram import TelegramHandler


class RalphAgent:
    """
    An autonomous coding agent that runs in a loop.

    Ralph works continuously on a task, making commits after each change
    and tracking progress in a scratchpad directory.
    """

    def __init__(
        self,
        prompt: str,
        working_dir: str = ".",
        scratchpad_dir: str = ".agent",
        max_iterations: Optional[int] = None,
        allowed_tools: Optional[list[str]] = None,
        name: Optional[str] = None,
        telegram_handler: Optional["TelegramHandler"] = None,
    ):
        """
        Initialize Ralph.

        Args:
            prompt: The task for Ralph to work on (can be a string or path to .md file)
            working_dir: Directory to work in
            scratchpad_dir: Directory for Ralph's notes, TODOs, and plans
            max_iterations: Maximum loop iterations (None = infinite)
            allowed_tools: Tools Ralph can use (None = all safe tools)
            name: Agent name for identification (defaults to working directory name)
            telegram_handler: Optional Telegram handler for remote monitoring/control
        """
        self.prompt = self._load_prompt(prompt)
        self.working_dir = Path(working_dir).resolve()
        self.scratchpad_dir = self.working_dir / scratchpad_dir
        self.max_iterations = max_iterations
        self.allowed_tools = allowed_tools or [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep"
        ]

        # Agent identification
        self.name = name or self.working_dir.name

        # Telegram integration
        self.telegram = telegram_handler
        if self.telegram:
            self.telegram.set_agent(self)

        # Stats
        self.iterations = 0
        self.total_cost = 0.0
        self.start_time = None

        # Control flags
        self._paused = False
        self._should_stop = False
        self._prompt_injection: Optional[str] = None
        self._current_task: Optional[asyncio.Task] = None

        # Ensure scratchpad exists
        self.scratchpad_dir.mkdir(parents=True, exist_ok=True)

    def _load_prompt(self, prompt: str) -> str:
        """Load prompt from file if it's a path, otherwise return as-is."""
        if prompt.endswith(".md") and Path(prompt).exists():
            return Path(prompt).read_text()
        return prompt

    def _is_ios_project(self) -> bool:
        """Check if working directory contains iOS project indicators."""
        ios_patterns = [
            "*.xcodeproj",
            "*.xcworkspace",
            "**/*.pbxproj",
            "**/Info.plist",
            "Package.swift",  # Swift Package (could be iOS)
            "Podfile",  # CocoaPods
        ]

        for pattern in ios_patterns:
            matches = glob_module.glob(str(self.working_dir / pattern), recursive=True)
            if matches:
                return True
        return False

    def _get_ios_prompt_additions(self) -> str:
        """Return iOS-specific prompt additions for simulator interaction."""
        return f"""

iOS SIMULATOR CAPABILITIES:
You have access to iOS Simulator screenshot and navigation tools via the simulator module.

AVAILABLE COMMANDS (run via Bash):
```bash
# Take a screenshot and get the path
python -m ralph.simulator screenshot --context "description of expected screen" --json

# Tap at coordinates (you determine coordinates from analyzing screenshots)
python -m ralph.simulator tap --x 200 --y 400

# Swipe (scroll)
python -m ralph.simulator swipe --from 200,800 --to 200,200

# Type text into focused field
python -m ralph.simulator type "text to type"

# Press hardware buttons
python -m ralph.simulator button home

# Check simulator status
python -m ralph.simulator status --json
```

VISUAL VERIFICATION WORKFLOW:
After making UI changes, verify them visually:

1. Take a screenshot:
   python -m ralph.simulator screenshot --context "main screen after adding button" --json

2. Use the Read tool on the screenshot_path to analyze the image visually.
   You can see the UI and estimate coordinates of elements.

3. If you need to navigate to a different screen:
   - Analyze the screenshot to find the button/element
   - Estimate its coordinates (e.g., "Settings icon appears to be at ~200, 750")
   - Tap: python -m ralph.simulator tap --x 200 --y 750
   - Screenshot again to verify

PROACTIVE SCREENSHOT BEHAVIOR:
- After building/running the app: Screenshot to verify the build succeeded
- After UI code changes: Screenshot to verify layout matches intent
- When debugging UI issues: Screenshot to see current state
- After fixing bugs: Screenshot to confirm the fix

Screenshots are saved to: {self.scratchpad_dir}/screenshots/
Document visual observations in: {self.scratchpad_dir}/NOTES.md
"""

    def _build_system_prompt(self) -> str:
        """Build the system prompt for Ralph."""
        base_prompt = f"""You are Ralph, an autonomous coding agent that works continuously on tasks.

CORE BEHAVIORS:
1. Work methodically on the task, one step at a time
2. Make a commit and push after every meaningful change
3. Use {self.scratchpad_dir.name}/ as your scratchpad for:
   - TODO.md: Track your progress and remaining tasks
   - PLAN.md: Store your long-term implementation plan
   - NOTES.md: Any observations or decisions
4. Update TODO.md after each iteration to track progress
5. When you complete the main task, focus on testing, documentation, and polish
6. If you're truly done, clearly state "TASK COMPLETE" in your final message

IMPORTANT:
- Read existing files before modifying them
- Write tests for critical functionality
- Keep commits atomic and well-described
- If stuck, document the issue in {self.scratchpad_dir.name}/BLOCKED.md

Current time: {datetime.now().isoformat()}
Working directory: {self.working_dir}
"""

        # Add iOS-specific capabilities if this is an iOS project
        if self._is_ios_project():
            base_prompt += self._get_ios_prompt_additions()

        return base_prompt

    def _build_iteration_prompt(self) -> str:
        """Build the prompt for each iteration."""
        todo_path = self.scratchpad_dir / "TODO.md"

        iteration_context = f"""
--- ITERATION {self.iterations + 1} ---

Your task:
{self.prompt}
"""

        # If TODO.md exists, remind Ralph of their progress
        if todo_path.exists():
            iteration_context += f"""
Your TODO.md shows your current progress. Review it and continue where you left off.
"""

        # Add one-time prompt injection if present
        if self._prompt_injection:
            iteration_context += f"""

--- USER HINT ---
{self._prompt_injection}
"""
            self._prompt_injection = None

        return iteration_context

    # --- Control Methods ---

    def pause(self):
        """Pause the agent after current iteration."""
        self._paused = True

    def resume(self):
        """Resume a paused agent."""
        self._paused = False

    def force_iteration(self, hint: Optional[str] = None):
        """
        Force start a new iteration, optionally with a hint.

        Args:
            hint: Optional message to inject into the next iteration prompt
        """
        if hint:
            self._prompt_injection = hint
        if self._current_task:
            self._current_task.cancel()

    def stop(self):
        """Gracefully stop the agent."""
        self._should_stop = True
        if self._current_task:
            self._current_task.cancel()

    async def run_iteration(self) -> dict:
        """Run a single iteration of the Ralph loop."""
        self.iterations += 1
        iteration_start = datetime.now()

        display.print_iteration_header(
            iteration=self.iterations,
            started_at=iteration_start.isoformat(),
        )

        options = ClaudeCodeOptions(
            allowed_tools=self.allowed_tools,
            permission_mode="bypassPermissions",
            system_prompt=self._build_system_prompt(),
            cwd=str(self.working_dir),
        )

        result = {
            "iteration": self.iterations,
            "started_at": iteration_start.isoformat(),
            "completed": False,
            "cost": 0.0,
            "turns": 0,
        }

        try:
            async for message in query(
                prompt=self._build_iteration_prompt(),
                options=options,
            ):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if hasattr(block, "text"):
                            display.print_assistant_message(block.text)

                elif isinstance(message, ResultMessage):
                    result["completed"] = True
                    result["turns"] = getattr(message, "num_turns", 0)
                    result["cost"] = getattr(message, "total_cost_usd", 0.0) or 0.0
                    result["duration_ms"] = getattr(message, "duration_ms", 0)

                    self.total_cost += result["cost"]

                    display.print_iteration_complete(
                        turns=result["turns"],
                        cost=result["cost"],
                        total_cost=self.total_cost,
                    )

        except Exception as e:
            display.print_error(f"Iteration failed: {e}")
            result["error"] = str(e)

        result["ended_at"] = datetime.now().isoformat()
        self._log_iteration(result)

        return result

    def _log_iteration(self, result: dict):
        """Log iteration results to the scratchpad."""
        log_path = self.scratchpad_dir / "iterations.log"

        with open(log_path, "a") as f:
            f.write(f"\n--- Iteration {result['iteration']} ---\n")
            f.write(f"Started: {result['started_at']}\n")
            f.write(f"Ended: {result['ended_at']}\n")
            f.write(f"Turns: {result.get('turns', 'N/A')}\n")
            f.write(f"Cost: ${result.get('cost', 0):.4f}\n")
            if result.get("error"):
                f.write(f"Error: {result['error']}\n")
            f.write("\n")

    async def run(self):
        """Run the Ralph loop."""
        self.start_time = datetime.now()

        display.print_banner(
            working_dir=str(self.working_dir),
            scratchpad_dir=self.scratchpad_dir.name,
            max_iterations=self.max_iterations,
        )
        display.print_task(self.prompt)

        # Start Telegram bot if configured
        if self.telegram:
            try:
                await self.telegram.start()
                await self.telegram.notify_start(self)
            except Exception as e:
                display.print_warning(f"Telegram failed to start: {e}")
                self.telegram = None

        try:
            while not self._should_stop:
                if self.max_iterations and self.iterations >= self.max_iterations:
                    display.print_max_iterations_reached(self.max_iterations)
                    break

                # Check pause state
                while self._paused and not self._should_stop:
                    await asyncio.sleep(0.5)

                if self._should_stop:
                    break

                # Run iteration (can be cancelled by force_iteration)
                self._current_task = asyncio.create_task(self._run_iteration_inner())
                try:
                    result = await self._current_task
                except asyncio.CancelledError:
                    # Force iteration requested - continue to next iteration
                    display.print_info("Iteration interrupted, starting new iteration...")
                    continue
                finally:
                    self._current_task = None

                # Send Telegram notification if configured
                if self.telegram:
                    await self.telegram.notify_iteration(self, result)

                # Brief pause between iterations to avoid hammering the API
                await asyncio.sleep(2)

        except KeyboardInterrupt:
            display.print_interrupted()

        finally:
            # Stop Telegram and send notification
            if self.telegram:
                await self.telegram.notify_stop(self)
                await self.telegram.stop()

            self._print_summary()

    async def _run_iteration_inner(self) -> dict:
        """Internal iteration runner that can be cancelled."""
        return await self.run_iteration()

    def _print_summary(self):
        """Print final summary."""
        duration = datetime.now() - self.start_time if self.start_time else None
        duration_str = str(duration).split(".")[0] if duration else "N/A"

        display.print_summary(
            iterations=self.iterations,
            total_cost=self.total_cost,
            duration=duration_str,
        )


async def run_ralph(
    prompt: str,
    working_dir: str = ".",
    scratchpad_dir: str = ".agent",
    max_iterations: Optional[int] = None,
    name: Optional[str] = None,
    telegram_handler: Optional["TelegramHandler"] = None,
):
    """Convenience function to run Ralph."""
    agent = RalphAgent(
        prompt=prompt,
        working_dir=working_dir,
        scratchpad_dir=scratchpad_dir,
        max_iterations=max_iterations,
        name=name,
        telegram_handler=telegram_handler,
    )
    await agent.run()
