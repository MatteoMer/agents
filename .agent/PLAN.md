# Jolt zkVM Rust to Zig Port - Implementation Plan

## Overview
Port the Jolt zkVM from Rust to Zig, maintaining the same architecture while using idiomatic Zig patterns.

## Source Structure Analysis

### Crate Dependencies (Porting Order)
1. **common** (smallest, no deps) - 4 files
   - constants.rs → constants.zig
   - attributes.rs → attributes.zig (skip syn parsing, keep struct only)
   - jolt_device.rs → jolt_device.zig
   - lib.rs → root module

2. **jolt-platform** (depends on nothing significant) - 6 files
   - alloc.rs → alloc.zig
   - cycle_tracking.rs → cycle_tracking.zig
   - lib.rs → root module
   - malloc_shim.rs → malloc_shim.zig
   - print.rs → print.zig
   - random.rs → random.zig

3. **tracer** (RISC-V emulator, 125+ instruction files)
   - Core emulator
   - All RISC-V instruction definitions
   - Utilities

4. **jolt-core** (main implementation, 296 files)
   - field/ - Field arithmetic abstractions
   - poly/ - Polynomial types and commitments
   - msm/ - Multi-scalar multiplication
   - subprotocols/ - Cryptographic protocols
   - transcripts/ - Fiat-Shamir transcripts
   - zkvm/ - Main zkVM implementation
   - utils/ - Helper utilities

## Type Mapping Strategy

### Rust → Zig Mappings
| Rust | Zig |
|------|-----|
| `struct Foo { ... }` | `const Foo = struct { ... };` |
| `enum Foo { A, B(T) }` | `const Foo = union(enum) { a, b: T };` |
| `trait Foo` | `fn Interface(comptime T: type)` or vtable |
| `Vec<T>` | `std.ArrayList(T)` or `[]T` slice |
| `Result<T, E>` | `T!E` (error union) |
| `Option<T>` | `?T` (optional) |
| `Arc<T>` / `Rc<T>` | Manual with allocator |
| `Box<T>` | Pointer with allocator |
| `impl Trait for Type` | Generic functions with `anytype` |
| `#[derive(...)]` | Zig comptime (autogen) |
| `?` operator | `try` keyword |
| `unwrap()` | `.?` or `orelse unreachable` |
| `match` | `switch` |
| `mod foo;` | `@import("foo.zig")` |
| `use crate::foo` | `@import("root").foo` |
| `pub(crate)` | No direct equiv, use `pub` |

### Memory Management
- Use `std.mem.Allocator` throughout
- Pass allocator to all allocation functions
- Use arena allocators where appropriate
- Prefer slices over ArrayList when size is known

### Concurrency
- Rust `rayon` parallel iterators → Zig `std.Thread.Pool` or manual threading
- `Send + Sync` → Zig's data race safety via design

### Serialization
- Rust `serde` → Custom serialization or use postcard/bincode patterns
- `ark_serialize` → Port the serialize/deserialize traits

## Implementation Phases

### Phase 1: Project Setup & Common Module
- [x] Create build.zig
- [x] Create directory structure
- [ ] Port common/constants.zig
- [ ] Port common/attributes.zig
- [ ] Port common/jolt_device.zig

### Phase 2: Field Arithmetic Foundation
- [ ] Create field module with JoltField trait as interface
- [ ] Port BigInt/limb arithmetic
- [ ] Port Montgomery reduction
- [ ] Port Barrett reduction
- [ ] Port BN254 scalar field

### Phase 3: Polynomial Layer
- [ ] Port dense MLPoly
- [ ] Port eq_poly, identity_poly
- [ ] Port sparse polynomial representations
- [ ] Port polynomial commitment interface

### Phase 4: Cryptographic Primitives
- [ ] Port transcript (Fiat-Shamir)
- [ ] Port Dory commitment scheme
- [ ] Port HyperKZG commitment scheme
- [ ] Port sumcheck protocol
- [ ] Port MSM

### Phase 5: Tracer / RISC-V
- [ ] Port RISC-V instruction definitions
- [ ] Port emulator core
- [ ] Port memory model

### Phase 6: zkVM Core
- [ ] Port R1CS constraint system
- [ ] Port Spartan prover/verifier
- [ ] Port instruction lookups
- [ ] Port memory checking
- [ ] Port bytecode handling

### Phase 7: Integration & Testing
- [ ] End-to-end prove/verify test
- [ ] Benchmark comparisons
- [ ] Documentation

## File Count Estimates
- common: 4 files → ~4 Zig files
- jolt-platform: 6 files → ~6 Zig files
- tracer: ~130 files → ~50 Zig files (consolidate instructions)
- jolt-core: 296 files → ~100 Zig files (consolidate)

Total: ~160 Zig files

## Key Zig Idioms to Use

### 1. Comptime Generics (for traits)
```zig
pub fn JoltField(comptime Self: type) type {
    return struct {
        pub fn add(a: Self, b: Self) Self { ... }
        pub fn mul(a: Self, b: Self) Self { ... }
    };
}
```

### 2. Error Unions
```zig
pub const FieldError = error {
    DivisionByZero,
    InvalidInput,
};

pub fn inverse(self: Field) FieldError!Field { ... }
```

### 3. SIMD
```zig
const Vec4u64 = @Vector(4, u64);
fn parallel_add(a: Vec4u64, b: Vec4u64) Vec4u64 {
    return a + b;
}
```

### 4. Memory-Mapped Polynomials
```zig
pub const DensePolynomial = struct {
    coeffs: []Field,
    allocator: Allocator,

    pub fn init(allocator: Allocator, size: usize) !DensePolynomial { ... }
    pub fn deinit(self: *DensePolynomial) void { ... }
};
```

## Notes
- Focus on correctness first, then optimize
- Keep close mapping to Rust structure for easier verification
- Write tests alongside each module
- Use Zig's built-in test framework
