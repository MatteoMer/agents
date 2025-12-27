Your job is to port the Python codebase in ./source to TypeScript in ./target.

Make a commit and push your changes after every single file edit.

Use the .agent/ directory as a scratchpad for your work:
- Store your porting plan in .agent/PLAN.md
- Track progress in .agent/TODO.md

Guidelines:
1. Start by analyzing the Python codebase structure
2. Set up the TypeScript project with proper tooling (tsconfig, package.json, etc.)
3. Port one module at a time, maintaining the same structure when possible
4. Use TypeScript idioms - proper types, interfaces, async/await patterns
5. Write tests as you go (aim for 20% testing, 80% porting)

Type mapping hints:
- Python dataclasses -> TypeScript interfaces or classes
- Python typing.Optional -> TypeScript optional (?)
- Python Dict -> TypeScript Record or Map
- Python List -> TypeScript array
- Python async/await -> TypeScript async/await
- Python context managers -> TypeScript try/finally or using

When you believe the port is complete, verify by:
1. Running the TypeScript compiler (no errors)
2. Running the test suite
3. Documenting any features that couldn't be ported directly
