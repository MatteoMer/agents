// Print utility for emulated RISC-V environment
// Ported from Rust to Zig

const std = @import("std");
const builtin = @import("builtin");

// Constants to signal the emulator
// PRI in hex (ASCII)
pub const JOLT_PRINT_ECALL_NUM: u32 = 0x505249;
pub const JOLT_PRINT_STRING: u32 = 1;
pub const JOLT_PRINT_LINE: u32 = 2; // with newline

/// Emit a JOLT print ecall for RISC-V
/// This is only available on RISC-V targets
fn emitJoltPrintEcall(text_ptr: u32, text_len: u32, print_type: u32) void {
    if (builtin.cpu.arch == .riscv32 or builtin.cpu.arch == .riscv64) {
        // Insert ECALL directly into the compiled code
        asm volatile (
            \\.word 0x00000073
            :
            : [_] "{x10}" (JOLT_PRINT_ECALL_NUM),
              [_] "{x11}" (text_ptr),
              [_] "{x12}" (text_len),
              [_] "{x13}" (print_type),
            : "memory"
        );
    }
}

/// Print a string without newline
pub fn print(text: []const u8) void {
    if (builtin.cpu.arch == .riscv32 or builtin.cpu.arch == .riscv64) {
        const text_ptr = @intFromPtr(text.ptr);
        const text_len = text.len;
        emitJoltPrintEcall(@intCast(text_ptr), @intCast(text_len), JOLT_PRINT_STRING);
    } else {
        // On non-RISC-V platforms, use standard output
        std.debug.print("{s}", .{text});
    }
}

/// Print a string with newline
pub fn println(text: []const u8) void {
    if (builtin.cpu.arch == .riscv32 or builtin.cpu.arch == .riscv64) {
        const text_ptr = @intFromPtr(text.ptr);
        const text_len = text.len;
        emitJoltPrintEcall(@intCast(text_ptr), @intCast(text_len), JOLT_PRINT_LINE);
    } else {
        // On non-RISC-V platforms, use standard output
        std.debug.print("{s}\n", .{text});
    }
}

test "print constants" {
    try std.testing.expect(JOLT_PRINT_ECALL_NUM == 0x505249);
    try std.testing.expect(JOLT_PRINT_STRING == 1);
    try std.testing.expect(JOLT_PRINT_LINE == 2);
}
