"""
Ralph Agent - Core implementation using Claude Agent SDK.

Ralph runs in a continuous loop, working on tasks autonomously,
committing after each change, and tracking progress in a scratchpad.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from claude_code_sdk import query, ClaudeCodeOptions, AssistantMessage, ResultMessage


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
    ):
        """
        Initialize Ralph.

        Args:
            prompt: The task for Ralph to work on (can be a string or path to .md file)
            working_dir: Directory to work in
            scratchpad_dir: Directory for Ralph's notes, TODOs, and plans
            max_iterations: Maximum loop iterations (None = infinite)
            allowed_tools: Tools Ralph can use (None = all safe tools)
        """
        self.prompt = self._load_prompt(prompt)
        self.working_dir = Path(working_dir).resolve()
        self.scratchpad_dir = self.working_dir / scratchpad_dir
        self.max_iterations = max_iterations
        self.allowed_tools = allowed_tools or [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep"
        ]

        # Stats
        self.iterations = 0
        self.total_cost = 0.0
        self.start_time = None

        # Ensure scratchpad exists
        self.scratchpad_dir.mkdir(parents=True, exist_ok=True)

    def _load_prompt(self, prompt: str) -> str:
        """Load prompt from file if it's a path, otherwise return as-is."""
        if prompt.endswith(".md") and Path(prompt).exists():
            return Path(prompt).read_text()
        return prompt

    def _build_system_prompt(self) -> str:
        """Build the system prompt for Ralph."""
        return f"""You are Ralph, an autonomous coding agent that works continuously on tasks.

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

        return iteration_context

    async def run_iteration(self) -> dict:
        """Run a single iteration of the Ralph loop."""
        self.iterations += 1
        iteration_start = datetime.now()

        print(f"\n{'='*60}")
        print(f"RALPH ITERATION {self.iterations}")
        print(f"Started: {iteration_start.isoformat()}")
        print(f"{'='*60}\n")

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
                            print(block.text)

                elif isinstance(message, ResultMessage):
                    result["completed"] = True
                    result["turns"] = getattr(message, "num_turns", 0)
                    result["cost"] = getattr(message, "total_cost_usd", 0.0) or 0.0
                    result["duration_ms"] = getattr(message, "duration_ms", 0)

                    self.total_cost += result["cost"]

                    print(f"\n--- Iteration Complete ---")
                    print(f"Turns: {result['turns']}")
                    print(f"Cost: ${result['cost']:.4f}")
                    print(f"Total cost so far: ${self.total_cost:.4f}")

        except Exception as e:
            print(f"\n[ERROR] Iteration failed: {e}")
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

        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                     RALPH AGENT STARTED                       ║
╠══════════════════════════════════════════════════════════════╣
║  Working directory: {str(self.working_dir)[:40]:<40} ║
║  Scratchpad: {str(self.scratchpad_dir.name):<47} ║
║  Max iterations: {str(self.max_iterations or 'unlimited'):<43} ║
╚══════════════════════════════════════════════════════════════╝
""")

        print("TASK:")
        print("-" * 60)
        print(self.prompt[:500] + ("..." if len(self.prompt) > 500 else ""))
        print("-" * 60)

        try:
            while True:
                if self.max_iterations and self.iterations >= self.max_iterations:
                    print(f"\n[RALPH] Max iterations ({self.max_iterations}) reached. Stopping.")
                    break

                result = await self.run_iteration()

                # Brief pause between iterations to avoid hammering the API
                await asyncio.sleep(2)

        except KeyboardInterrupt:
            print("\n\n[RALPH] Interrupted by user. Shutting down...")

        finally:
            self._print_summary()

    def _print_summary(self):
        """Print final summary."""
        duration = datetime.now() - self.start_time if self.start_time else None

        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                     RALPH SESSION COMPLETE                    ║
╠══════════════════════════════════════════════════════════════╣
║  Total iterations: {self.iterations:<41} ║
║  Total cost: ${self.total_cost:<44.2f} ║
║  Duration: {str(duration).split('.')[0] if duration else 'N/A':<49} ║
╚══════════════════════════════════════════════════════════════╝
""")


async def run_ralph(
    prompt: str,
    working_dir: str = ".",
    scratchpad_dir: str = ".agent",
    max_iterations: Optional[int] = None,
):
    """Convenience function to run Ralph."""
    agent = RalphAgent(
        prompt=prompt,
        working_dir=working_dir,
        scratchpad_dir=scratchpad_dir,
        max_iterations=max_iterations,
    )
    await agent.run()
