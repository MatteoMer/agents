// Attributes for Jolt programs
// Ported from Rust to Zig

const constants = @import("constants.zig");

/// Configuration attributes for Jolt programs
pub const Attributes = struct {
    wasm: bool,
    nightly: bool,
    guest_only: bool,
    memory_size: u64,
    stack_size: u64,
    max_input_size: u64,
    max_output_size: u64,
    max_trusted_advice_size: u64,
    max_untrusted_advice_size: u64,
    max_trace_length: u64,

    /// Create default attributes
    pub fn default() Attributes {
        return Attributes{
            .wasm = false,
            .nightly = false,
            .guest_only = false,
            .memory_size = constants.DEFAULT_MEMORY_SIZE,
            .stack_size = constants.DEFAULT_STACK_SIZE,
            .max_input_size = constants.DEFAULT_MAX_INPUT_SIZE,
            .max_output_size = constants.DEFAULT_MAX_OUTPUT_SIZE,
            .max_trusted_advice_size = constants.DEFAULT_MAX_TRUSTED_ADVICE_SIZE,
            .max_untrusted_advice_size = constants.DEFAULT_MAX_UNTRUSTED_ADVICE_SIZE,
            .max_trace_length = constants.DEFAULT_MAX_TRACE_LENGTH,
        };
    }
};

test "default attributes" {
    const std = @import("std");
    const attrs = Attributes.default();
    try std.testing.expect(!attrs.wasm);
    try std.testing.expect(!attrs.nightly);
    try std.testing.expect(!attrs.guest_only);
    try std.testing.expect(attrs.memory_size == constants.DEFAULT_MEMORY_SIZE);
    try std.testing.expect(attrs.stack_size == constants.DEFAULT_STACK_SIZE);
}
