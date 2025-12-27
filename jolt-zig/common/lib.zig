// Common module for Jolt zkVM
// Ported from Rust to Zig

pub const attributes = @import("attributes.zig");
pub const constants = @import("constants.zig");
pub const jolt_device = @import("jolt_device.zig");

// Re-export commonly used types
pub const Attributes = attributes.Attributes;
pub const JoltDevice = jolt_device.JoltDevice;
pub const MemoryConfig = jolt_device.MemoryConfig;
pub const MemoryLayout = jolt_device.MemoryLayout;

test {
    @import("std").testing.refAllDecls(@This());
}
