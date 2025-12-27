// Cycle tracking utility for emulated RISC-V cycles (both virtual and real)
// Ported from Rust to Zig
//
// Important for usage: often the compiler will optimize away computations
// when trying to profile cycles. This will result in inaccurate measurements.
// Use @import("std").mem.doNotOptimizeAway() to prevent the compiler from
// moving your code.

const std = @import("std");
const builtin = @import("builtin");

// Constants to signal the emulator
pub const JOLT_CYCLE_TRACK_ECALL_NUM: u32 = 0xC7C1E; // "C Y C L E"
pub const JOLT_CYCLE_MARKER_START: u32 = 1;
pub const JOLT_CYCLE_MARKER_END: u32 = 2;

/// Emit a JOLT cycle marker ecall for RISC-V
/// This is only available on RISC-V targets
fn emitJoltCycleMarkerEcall(marker_id: u32, marker_len: u32, event_type: u32) void {
    if (builtin.cpu.arch == .riscv32 or builtin.cpu.arch == .riscv64) {
        // Insert ECALL directly into the compiled code
        asm volatile (
            \\.word 0x00000073
            :
            : [_] "{x10}" (JOLT_CYCLE_TRACK_ECALL_NUM),
              [_] "{x11}" (marker_id),
              [_] "{x12}" (marker_len),
              [_] "{x13}" (event_type),
            : "memory"
        );
    }
}

/// Start tracking cycles for a named marker
pub fn startCycleTracking(marker_id: []const u8) void {
    if (builtin.cpu.arch == .riscv32 or builtin.cpu.arch == .riscv64) {
        const marker_id_ptr = @intFromPtr(marker_id.ptr);
        const marker_len = marker_id.len;
        emitJoltCycleMarkerEcall(@intCast(marker_id_ptr), @intCast(marker_len), JOLT_CYCLE_MARKER_START);
    }
}

/// End tracking cycles for a named marker
pub fn endCycleTracking(marker_id: []const u8) void {
    if (builtin.cpu.arch == .riscv32 or builtin.cpu.arch == .riscv64) {
        const marker_id_ptr = @intFromPtr(marker_id.ptr);
        const marker_len = marker_id.len;
        emitJoltCycleMarkerEcall(@intCast(marker_id_ptr), @intCast(marker_len), JOLT_CYCLE_MARKER_END);
    }
}

test "cycle tracking constants" {
    try std.testing.expect(JOLT_CYCLE_TRACK_ECALL_NUM == 0xC7C1E);
    try std.testing.expect(JOLT_CYCLE_MARKER_START == 1);
    try std.testing.expect(JOLT_CYCLE_MARKER_END == 2);
}
