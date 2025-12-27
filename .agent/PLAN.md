# Jolt zkVM Rust to Zig Port Plan

## Overview
Port the Jolt zkVM from Rust to Zig, maintaining the core functionality while leveraging Zig's features.

## Project Structure
Source has ~581 Rust files total, with jolt-core containing ~296 files.

### Module Dependency Order
1. **common** - Basic types, attributes, constants, device interface (6 files)
2. **jolt-platform** - Platform-specific code for guest execution (8 files)
3. **tracer** - Instruction tracing and ELF handling
4. **jolt-core** - Main prover/verifier implementation (296 files)
   - field/ - Finite field arithmetic
   - utils/ - Utility functions (math, errors, profiling, etc.)
   - transcripts/ - Fiat-Shamir transformations
   - poly/ - Polynomial commitments (Dory, HyperKZG)
   - subprotocols/ - Sumcheck, grand products, etc.
   - msm/ - Multi-scalar multiplication
   - guest/ - Guest-side code
   - zkvm/ - Main zkVM logic (R1CS, bytecode, memory)
   - host/ - Host-side program execution

## Type Mapping Strategy

### Basic Types
- `Vec<T>` → `std.ArrayList(T)` or `[]T` (slices)
- `Option<T>` → `?T`
- `Result<T, E>` → `T!E` (error unions)
- `Arc<T>/Rc<T>` → Manual allocators
- `Box<T>` → `*T` with allocator

### Traits → Zig Patterns
- Simple traits → `comptime` generic functions
- Complex traits → vtable pattern (struct with function pointers)
- Trait bounds → `comptime` checks or interface types

### Concurrency
- `rayon` parallel iterators → Zig's `std.Thread` or custom thread pool
- `Mutex<T>` → `std.Thread.Mutex`
- `RwLock<T>` → `std.Thread.RwLock`

### Crypto Libraries
- `ark-bn254`, `ark-ff`, `ark-ec` → Need Zig implementations or C bindings
- Consider using existing Zig crypto libraries or porting minimal required functionality
- `sha2`, `sha3`, `blake2`, `blake3` → Zig's std.crypto or third-party

## Porting Phases

### Phase 1: Foundation (Common & Platform)
- [x] Setup project structure
- [ ] Port common/ module
  - [ ] attributes.rs → attributes.zig
  - [ ] constants.rs → constants.zig
  - [ ] jolt_device.rs → jolt_device.zig
- [ ] Port jolt-platform/ module
  - [ ] alloc.rs → alloc.zig
  - [ ] cycle_tracking.rs → cycle_tracking.zig
  - [ ] malloc_shim.rs → malloc_shim.zig
  - [ ] print.rs → print.zig
  - [ ] random.rs → random.zig

### Phase 2: Core Utilities
- [ ] Port jolt-core/utils/
  - [ ] errors.rs → errors.zig
  - [ ] math.rs → math.zig
  - [ ] thread.rs → thread.zig
  - [ ] profiling.rs → profiling.zig
  - [ ] Other utilities

### Phase 3: Field Arithmetic
- [ ] Port jolt-core/field/
  - [ ] Finite field implementations
  - [ ] Extension fields
  - [ ] Field operations

### Phase 4: Polynomial Commitments
- [ ] Port jolt-core/poly/
  - [ ] Dense polynomials
  - [ ] Commitment schemes (Dory, HyperKZG)
  - [ ] Opening proofs

### Phase 5: Subprotocols
- [ ] Port jolt-core/subprotocols/
  - [ ] Sumcheck protocol
  - [ ] Grand product arguments
  - [ ] Zero-check

### Phase 6: zkVM Core
- [ ] Port jolt-core/zkvm/
  - [ ] R1CS constraint system
  - [ ] Bytecode handling
  - [ ] Memory checking (RAM, registers)
  - [ ] Instruction execution

### Phase 7: Host & Integration
- [ ] Port jolt-core/host/
  - [ ] Program execution
  - [ ] Toolchain integration
  - [ ] Analysis tools

### Phase 8: Testing & Validation
- [ ] Port tests
- [ ] Create integration tests
- [ ] Benchmark comparisons
- [ ] Document differences

## Key Technical Challenges

### 1. Arkworks Dependencies
Jolt heavily uses arkworks for elliptic curves and field arithmetic. Options:
- Port minimal arkworks functionality to Zig
- Use C bindings to arkworks libraries
- Use alternative Zig crypto libraries

### 2. Macro System
Rust macros are used extensively. Convert to:
- Zig `comptime` functions
- Code generation scripts
- Manual expansion for complex cases

### 3. Trait System
Many complex trait hierarchies. Convert to:
- `comptime` generic interfaces where possible
- Vtable pattern for runtime polymorphism
- Explicit function passing

### 4. Memory Management
Rust's ownership system ensures memory safety. In Zig:
- Use allocators explicitly
- Leverage Zig's defer for cleanup
- Consider arena allocators for temporary allocations

### 5. Error Handling
Rust's Result type is pervasive. In Zig:
- Use error unions (`!T`)
- Define error sets
- Use `try`/`catch` for propagation

## Build System

Create `build.zig` with:
- Library modules for each component
- Test runner
- Benchmark suite
- Example programs

## Testing Strategy

- Port existing Rust tests where possible
- Add Zig-specific tests for allocator usage
- Integration tests for end-to-end proving/verification
- Fuzzing tests for critical components

## Documentation

- Maintain inline documentation
- Create Zig-specific guides
- Document API differences from Rust version
- Performance comparison notes

## Success Criteria

1. `zig build` completes without errors
2. `zig build test` passes all tests
3. Can prove and verify a simple RISC-V program
4. Performance within 2x of Rust implementation
5. Memory usage reasonable (no major leaks)
