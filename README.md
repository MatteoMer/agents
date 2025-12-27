# Ralph

An autonomous coding agent that runs in a loop, inspired by [Geoff Huntley's technique](https://ghuntley.com/ralph/) and the [YC Agents hackathon](https://github.com/repomirrorhq/repomirror).

Ralph can port codebases between languages/frameworks, maintain repositories, refactor code, and work on long-running tasks—all autonomously, while you sleep.

## How It Works

Ralph runs Claude in a continuous loop:

```
┌─────────────────────────────────────────────────────────┐
│                     RALPH LOOP                          │
│                                                         │
│   ┌─────────┐    ┌──────────┐    ┌─────────────────┐   │
│   │  Read   │───►│  Work on │───►│ Commit & Push   │   │
│   │ prompt  │    │   task   │    │    changes      │   │
│   └─────────┘    └──────────┘    └─────────────────┘   │
│        ▲                                    │          │
│        │         ┌──────────┐               │          │
│        └─────────│  Update  │◄──────────────┘          │
│                  │  TODO.md │                          │
│                  └──────────┘                          │
└─────────────────────────────────────────────────────────┘
```

Each iteration, Ralph:
1. Reads the task prompt
2. Checks `.agent/TODO.md` for current progress
3. Works on the next step
4. Commits and pushes changes
5. Updates TODO.md
6. Repeats

## Installation

```bash
# Or install from source
git clone https://github.com/yourusername/ralph.git
cd ralph
pip install -e .
```

### Prerequisites

- Python 3.10+
- [Claude Code SDK](https://github.com/anthropics/claude-code-sdk) installed
- `ANTHROPIC_API_KEY` environment variable set

## Quick Start

### 1. Initialize a project

```bash
ralph init --template port
```

This creates:
- `prompt.md` - Your task description (edit this!)
- `.agent/TODO.md` - Ralph's progress tracker

### 2. Edit your prompt

```markdown
Your job is to port browser-use (Python) to browser-use-ts (TypeScript).

Make a commit and push your changes after every single file edit.

Use the .agent/ directory as a scratchpad for your work.
```

### 3. Run Ralph

```bash
# Run indefinitely
ralph run --prompt prompt.md

# Or limit iterations
ralph run --prompt prompt.md --max-iterations 50
```

## Usage

### Basic Commands

```bash
# Run with inline prompt
ralph run "Port this Python 2 codebase to Python 3"

# Run with prompt file
ralph run --prompt prompt.md

# Specify working directory
ralph run --prompt prompt.md --dir ./my-project

# Limit iterations
ralph run --prompt prompt.md --max-iterations 100

# Custom scratchpad location
ralph run --prompt prompt.md --scratchpad .ralph
```

### Programmatic Usage

```python
import asyncio
from ralph import RalphAgent

async def main():
    agent = RalphAgent(
        prompt="Port the auth module from Flask to FastAPI",
        working_dir="./my-project",
        max_iterations=50,
    )
    await agent.run()

asyncio.run(main())
```

## Example Prompts

Ralph works best with simple, focused prompts. Here are examples:

### Porting Codebases

```markdown
Your job is to port browser-use (Python) to browser-use-ts (TypeScript).

Make a commit and push your changes after every single file edit.

Use the .agent/ directory as a scratchpad for your work.
Track progress in .agent/TODO.md
```

### Maintaining a Repository

```markdown
Your job is to maintain this repository.

Focus on:
1. Fixing open GitHub issues
2. Improving test coverage
3. Updating dependencies

Commit after each meaningful change.
Track your work in .agent/TODO.md
```

### Refactoring

```markdown
Refactor the authentication system to use JWT tokens.

Requirements:
- Replace session-based auth with JWT
- Add refresh token support
- Update all tests
- Maintain backwards compatibility during migration

Commit incrementally. Track progress in .agent/TODO.md
```

See the `ralph/prompts/` directory for more examples.

## The Scratchpad

Ralph uses `.agent/` as a scratchpad to maintain context across iterations:

```
.agent/
├── TODO.md          # Current tasks and progress
├── PLAN.md          # Long-term implementation plan
├── NOTES.md         # Observations and decisions
├── BLOCKED.md       # Issues Ralph got stuck on
└── iterations.log   # Log of all iterations
```

**Why this works:** Between iterations, Ralph loses context. The scratchpad gives Ralph "memory" by persisting plans, progress, and decisions to files that get re-read each iteration.

## Tips for Best Results

### Keep Prompts Simple
The [RepoMirror team](https://github.com/repomirrorhq/repomirror) found that shorter prompts work better:

> "At one point we tried 'improving' the prompt with Claude's help. It ballooned to 1,500 words. The agent immediately got slower and dumber. We went back to 103 words and it was back on track."

### Commit Often
Instruct Ralph to commit after each file edit. This:
- Creates a clear history of changes
- Allows easy rollback if something breaks
- Lets you monitor progress via git log

### Start Supervised
Run Ralph with `--max-iterations 5` first to verify it understands the task, then let it run longer.

### Check the TODO.md
Ralph's `.agent/TODO.md` shows exactly what it thinks it's doing and what's left.

## Cost Considerations

Running Ralph overnight isn't free. The RepoMirror team reported:
- ~$10.50/hour with Claude Sonnet
- ~$800 total for 6 ported codebases overnight

Tips to manage costs:
- Use `--max-iterations` to cap spending
- Monitor `.agent/iterations.log` for cost tracking
- Start with smaller tasks to validate prompts

## How It Compares

| Approach | Description |
|----------|-------------|
| **Shell loop** | `while :; do cat prompt.md \| claude -p; done` |
| **Ralph** | Same concept, but with progress tracking, cost monitoring, and better prompts |
| **RepoMirror** | Full tool for setting up source/target repo pairs |

Ralph is the middle ground—more structured than a shell loop, simpler than a full framework.

## Troubleshooting

### Ralph gets stuck in a loop
Check `.agent/TODO.md`—if Ralph keeps updating the same task, your prompt may be ambiguous. Try making the success criteria clearer.

### Ralph drifts off-task
Add constraints to your prompt like "Focus only on X" or "Do not add new features."

### High costs
Ralph works hard! Use `--max-iterations` and monitor `.agent/iterations.log`.

## Credits

- [Geoff Huntley](https://ghuntley.com/ralph/) for the original "Ralph" technique
- [RepoMirror team](https://github.com/repomirrorhq/repomirror) for proving it works at scale
- Built with the [Claude Code SDK](https://github.com/anthropics/claude-code-sdk)

## License

MIT
