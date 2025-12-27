Your job is to port the Jolt zkVM from Rust to Zig. The source is in ./source (a16z/jolt).

Make a commit and push your changes after every single file edit.

Use the .agent/ directory as a scratchpad for your work:
- Store your porting plan in .agent/PLAN.md
- Track progress in .agent/TODO.md

Guidelines:
1. Start by studying jolt-core - this is the main prover/verifier implementation
2. Port modules in dependency order: common -> jolt-platform -> tracer -> jolt-core
3. Use Zig idioms - comptime, error unions, optional types, SIMD intrinsics
4. Leverage Zig's build system (build.zig) for the project structure
5. Write tests as you go (aim for 20% testing, 80% porting)

Type mapping hints:
- Rust structs -> Zig structs
- Rust enums -> Zig tagged unions
- Rust traits -> Zig interfaces (vtable pattern) or comptime generics
- Rust Vec<T> -> Zig ArrayList or slices
- Rust Result<T,E> -> Zig error unions (T!E)
- Rust Option<T> -> Zig optionals (?T)
- Rust Arc/Rc -> Zig manual memory management with allocators
- Rust iterators -> Zig iterators or for loops with slices
- Rust macros -> Zig comptime functions

Key components to port:
- Polynomial commitment schemes (Dory, HyperKZG)
- Sumcheck protocol implementation
- Spartan R1CS constraint system
- RISC-V instruction execution and bytecode handling
- Memory checking (RAM, registers)
- MSM (multi-scalar multiplication)

When you believe the port is complete, verify by:
1. Running zig build (no errors)
2. Running zig build test
3. Documenting any features that couldn't be ported directly
