// Platform module for Jolt zkVM
// Ported from Rust to Zig
//
// This module provides platform-specific functionality for
// guest code running in the RISC-V emulator.

pub const alloc = @import("alloc.zig");
pub const print = @import("print.zig");
pub const cycle_tracking = @import("cycle_tracking.zig");
pub const random = @import("random.zig");

// Re-export commonly used types and functions
pub const BumpAllocator = alloc.BumpAllocator;
pub const bumpAllocator = alloc.bumpAllocator;

// Re-export print functions
pub const joltPrint = print.print;
pub const joltPrintln = print.println;

// Re-export cycle tracking
pub const startCycleTracking = cycle_tracking.startCycleTracking;
pub const endCycleTracking = cycle_tracking.endCycleTracking;

// Re-export random
pub const sysRand = random.sysRand;
pub const randU64 = random.randU64;

test {
    @import("std").testing.refAllDecls(@This());
}
