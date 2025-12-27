// Jolt Device - peripheral device for RISC-V emulator I/O
// Ported from Rust to Zig

const std = @import("std");
const constants = @import("constants.zig");

/// Configuration for memory layout
pub const MemoryConfig = struct {
    max_input_size: u64,
    max_trusted_advice_size: u64,
    max_untrusted_advice_size: u64,
    max_output_size: u64,
    stack_size: u64,
    memory_size: u64,
    program_size: ?u64,

    pub fn default() MemoryConfig {
        return MemoryConfig{
            .max_input_size = constants.DEFAULT_MAX_INPUT_SIZE,
            .max_trusted_advice_size = constants.DEFAULT_MAX_TRUSTED_ADVICE_SIZE,
            .max_untrusted_advice_size = constants.DEFAULT_MAX_UNTRUSTED_ADVICE_SIZE,
            .max_output_size = constants.DEFAULT_MAX_OUTPUT_SIZE,
            .stack_size = constants.DEFAULT_STACK_SIZE,
            .memory_size = constants.DEFAULT_MEMORY_SIZE,
            .program_size = null,
        };
    }
};

/// Memory layout for the VM
pub const MemoryLayout = struct {
    /// The total size of the elf's sections, including the .text, .data, .rodata, and .bss sections.
    program_size: u64,
    max_trusted_advice_size: u64,
    trusted_advice_start: u64,
    trusted_advice_end: u64,
    max_untrusted_advice_size: u64,
    untrusted_advice_start: u64,
    untrusted_advice_end: u64,
    max_input_size: u64,
    max_output_size: u64,
    input_start: u64,
    input_end: u64,
    output_start: u64,
    output_end: u64,
    stack_size: u64,
    /// Stack starts from (RAM_START_ADDRESS + `program_size` + `stack_size`) and grows in descending addresses by `stack_size` bytes.
    stack_end: u64,
    memory_size: u64,
    /// Heap starts just after the start of the stack and is `memory_size` bytes.
    memory_end: u64,
    panic: u64,
    termination: u64,
    /// End of the memory region containing inputs, outputs, the panic bit,
    /// and the termination bit
    io_end: u64,

    /// Helper to align 'val' *up* to a multiple of 'align'
    fn alignUp(val: u64, align_val: u64) !u64 {
        if (align_val == 0) return val;
        const rem = val % align_val;
        if (rem == 0) return val;
        return try std.math.add(u64, val, align_val - rem);
    }

    pub fn init(config: *const MemoryConfig) !MemoryLayout {
        if (config.program_size == null) {
            return error.ProgramSizeRequired;
        }

        // Must be 8-byte aligned
        const max_trusted_advice_size = try alignUp(config.max_trusted_advice_size, 8);
        const max_untrusted_advice_size = try alignUp(config.max_untrusted_advice_size, 8);
        const max_input_size = try alignUp(config.max_input_size, 8);
        const max_output_size = try alignUp(config.max_output_size, 8);
        const stack_size = try alignUp(config.stack_size, 8);
        const memory_size = try alignUp(config.memory_size, 8);

        // Critical for ValEvaluation and ValFinal sumchecks in RAM
        if (max_trusted_advice_size != 0 and !std.math.isPowerOfTwo(max_trusted_advice_size)) {
            return error.TrustedAdviceSizeMustBePowerOfTwo;
        }
        if (max_untrusted_advice_size != 0 and !std.math.isPowerOfTwo(max_untrusted_advice_size)) {
            return error.UntrustedAdviceSizeMustBePowerOfTwo;
        }

        // Adds 16 to account for panic bit and termination bit
        // (they each occupy one full 8-byte word)
        var io_region_bytes = try std.math.add(u64, max_input_size, max_trusted_advice_size);
        io_region_bytes = try std.math.add(u64, io_region_bytes, max_untrusted_advice_size);
        io_region_bytes = try std.math.add(u64, io_region_bytes, max_output_size);
        io_region_bytes = try std.math.add(u64, io_region_bytes, 16);

        // Padded so that the witness index corresponding to `input_start`
        // has the form 0b11...100...0
        const io_region_words = std.math.ceilPowerOfTwo(u64, io_region_bytes / 8) catch return error.IORegionTooLarge;
        const io_bytes = try std.math.mul(u64, io_region_words, 8);

        // Place the larger or equal-sized advice region first in memory (at the lower address).
        var trusted_advice_start: u64 = undefined;
        var trusted_advice_end: u64 = undefined;
        var untrusted_advice_start: u64 = undefined;
        var untrusted_advice_end: u64 = undefined;

        if (max_trusted_advice_size >= max_untrusted_advice_size) {
            // Trusted advice goes first
            trusted_advice_start = try std.math.sub(u64, constants.RAM_START_ADDRESS, io_bytes);
            trusted_advice_end = try std.math.add(u64, trusted_advice_start, max_trusted_advice_size);
            untrusted_advice_start = trusted_advice_end;
            untrusted_advice_end = try std.math.add(u64, untrusted_advice_start, max_untrusted_advice_size);
        } else {
            // Untrusted advice goes first
            untrusted_advice_start = try std.math.sub(u64, constants.RAM_START_ADDRESS, io_bytes);
            untrusted_advice_end = try std.math.add(u64, untrusted_advice_start, max_untrusted_advice_size);
            trusted_advice_start = untrusted_advice_end;
            trusted_advice_end = try std.math.add(u64, trusted_advice_start, max_trusted_advice_size);
        }

        const input_start = @max(untrusted_advice_end, trusted_advice_end);
        const input_end = try std.math.add(u64, input_start, max_input_size);
        const output_start = input_end;
        const output_end = try std.math.add(u64, output_start, max_output_size);
        const panic = output_end;
        const termination = try std.math.add(u64, panic, 8);
        const io_end = try std.math.add(u64, termination, 8);

        const program_size = config.program_size.?;

        // stack grows downwards (decreasing addresses) from the bytecode_end + stack_size up to bytecode_end
        const stack_end = try std.math.add(u64, constants.RAM_START_ADDRESS, program_size);
        const stack_start = try std.math.add(u64, stack_end, stack_size);

        // heap grows *up* (increasing addresses) from the stack of the stack
        const memory_end = try std.math.add(u64, stack_start, memory_size);

        return MemoryLayout{
            .program_size = program_size,
            .max_trusted_advice_size = max_trusted_advice_size,
            .max_untrusted_advice_size = max_untrusted_advice_size,
            .max_input_size = max_input_size,
            .max_output_size = max_output_size,
            .trusted_advice_start = trusted_advice_start,
            .trusted_advice_end = trusted_advice_end,
            .untrusted_advice_start = untrusted_advice_start,
            .untrusted_advice_end = untrusted_advice_end,
            .input_start = input_start,
            .input_end = input_end,
            .output_start = output_start,
            .output_end = output_end,
            .stack_size = stack_size,
            .stack_end = stack_end,
            .memory_size = memory_size,
            .memory_end = memory_end,
            .panic = panic,
            .termination = termination,
            .io_end = io_end,
        };
    }

    /// Returns the start address memory.
    pub fn getLowestAddress(self: *const MemoryLayout) u64 {
        return @min(self.trusted_advice_start, self.untrusted_advice_start);
    }

    /// Returns the total emulator memory
    pub fn getTotalMemorySize(self: *const MemoryLayout) u64 {
        return self.memory_size + self.stack_size + constants.STACK_CANARY_SIZE;
    }

    pub fn format(
        self: MemoryLayout,
        comptime fmt: []const u8,
        options: std.fmt.FormatOptions,
        writer: anytype,
    ) !void {
        _ = fmt;
        _ = options;
        try writer.print("MemoryLayout {{\n", .{});
        try writer.print("  program_size: {}\n", .{self.program_size});
        try writer.print("  max_input_size: {}\n", .{self.max_input_size});
        try writer.print("  max_trusted_advice_size: {}\n", .{self.max_trusted_advice_size});
        try writer.print("  max_untrusted_advice_size: {}\n", .{self.max_untrusted_advice_size});
        try writer.print("  max_output_size: {}\n", .{self.max_output_size});
        try writer.print("  trusted_advice_start: 0x{X}\n", .{self.trusted_advice_start});
        try writer.print("  trusted_advice_end: 0x{X}\n", .{self.trusted_advice_end});
        try writer.print("  untrusted_advice_start: 0x{X}\n", .{self.untrusted_advice_start});
        try writer.print("  untrusted_advice_end: 0x{X}\n", .{self.untrusted_advice_end});
        try writer.print("  input_start: 0x{X}\n", .{self.input_start});
        try writer.print("  input_end: 0x{X}\n", .{self.input_end});
        try writer.print("  output_start: 0x{X}\n", .{self.output_start});
        try writer.print("  output_end: 0x{X}\n", .{self.output_end});
        try writer.print("  stack_size: 0x{X}\n", .{self.stack_size});
        try writer.print("  stack_end: 0x{X}\n", .{self.stack_end});
        try writer.print("  memory_size: 0x{X}\n", .{self.memory_size});
        try writer.print("  memory_end: 0x{X}\n", .{self.memory_end});
        try writer.print("  panic: 0x{X}\n", .{self.panic});
        try writer.print("  termination: 0x{X}\n", .{self.termination});
        try writer.print("  io_end: 0x{X}\n", .{self.io_end});
        try writer.print("}}", .{});
    }
};

/// Represented as a "peripheral device" in the RISC-V emulator, this captures
/// all reads from the reserved memory address space for program inputs and all writes
/// to the reserved memory address space for program outputs.
/// The inputs and outputs are part of the public inputs to the proof.
pub const JoltDevice = struct {
    inputs: std.ArrayList(u8),
    trusted_advice: std.ArrayList(u8),
    untrusted_advice: std.ArrayList(u8),
    outputs: std.ArrayList(u8),
    panic: bool,
    memory_layout: MemoryLayout,
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator, memory_config: *const MemoryConfig) !JoltDevice {
        return JoltDevice{
            .inputs = std.ArrayList(u8).init(allocator),
            .trusted_advice = std.ArrayList(u8).init(allocator),
            .untrusted_advice = std.ArrayList(u8).init(allocator),
            .outputs = std.ArrayList(u8).init(allocator),
            .panic = false,
            .memory_layout = try MemoryLayout.init(memory_config),
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *JoltDevice) void {
        self.inputs.deinit();
        self.trusted_advice.deinit();
        self.untrusted_advice.deinit();
        self.outputs.deinit();
    }

    pub fn load(self: *const JoltDevice, address: u64) u8 {
        if (self.isPanic(address)) {
            return @intFromBool(self.panic);
        } else if (self.isTermination(address)) {
            return 0; // Termination bit should never be loaded after it is set
        } else if (self.isInput(address)) {
            const internal_address = self.convertReadAddress(address);
            if (self.inputs.items.len <= internal_address) {
                return 0;
            } else {
                return self.inputs.items[internal_address];
            }
        } else if (self.isTrustedAdvice(address)) {
            const internal_address = self.convertTrustedAdviceReadAddress(address);
            if (self.trusted_advice.items.len <= internal_address) {
                return 0;
            } else {
                return self.trusted_advice.items[internal_address];
            }
        } else if (self.isUntrustedAdvice(address)) {
            const internal_address = self.convertUntrustedAdviceReadAddress(address);
            if (self.untrusted_advice.items.len <= internal_address) {
                return 0;
            } else {
                return self.untrusted_advice.items[internal_address];
            }
        } else if (self.isOutput(address)) {
            const internal_address = self.convertWriteAddress(address);
            if (self.outputs.items.len <= internal_address) {
                return 0;
            } else {
                return self.outputs.items[internal_address];
            }
        } else {
            std.debug.assert(address <= constants.RAM_START_ADDRESS - 8);
            return 0; // zero-padding
        }
    }

    pub fn store(self: *JoltDevice, address: u64, value: u8) !void {
        if (address == self.memory_layout.panic) {
            self.panic = true;
            return;
        } else if (self.isPanic(address) or self.isTermination(address)) {
            return;
        }

        const internal_address = self.convertWriteAddress(address);
        if (self.outputs.items.len <= internal_address) {
            try self.outputs.resize(internal_address + 1);
            // Zero-fill the new elements
            for (self.outputs.items[self.outputs.items.len - (internal_address + 1 - self.outputs.items.len)..]) |*byte| {
                byte.* = 0;
            }
        }
        self.outputs.items[internal_address] = value;
    }

    pub fn size(self: *const JoltDevice) usize {
        return self.inputs.items.len + self.outputs.items.len;
    }

    pub fn isInput(self: *const JoltDevice, address: u64) bool {
        return address >= self.memory_layout.input_start and address < self.memory_layout.input_end;
    }

    pub fn isTrustedAdvice(self: *const JoltDevice, address: u64) bool {
        return address >= self.memory_layout.trusted_advice_start and address < self.memory_layout.trusted_advice_end;
    }

    pub fn isUntrustedAdvice(self: *const JoltDevice, address: u64) bool {
        return address >= self.memory_layout.untrusted_advice_start and address < self.memory_layout.untrusted_advice_end;
    }

    pub fn isOutput(self: *const JoltDevice, address: u64) bool {
        return address >= self.memory_layout.output_start and address < self.memory_layout.termination;
    }

    pub fn isPanic(self: *const JoltDevice, address: u64) bool {
        return address >= self.memory_layout.panic and address < self.memory_layout.termination;
    }

    pub fn isTermination(self: *const JoltDevice, address: u64) bool {
        return address >= self.memory_layout.termination and address < self.memory_layout.io_end;
    }

    fn convertReadAddress(self: *const JoltDevice, address: u64) usize {
        return @intCast(address - self.memory_layout.input_start);
    }

    fn convertTrustedAdviceReadAddress(self: *const JoltDevice, address: u64) usize {
        return @intCast(address - self.memory_layout.trusted_advice_start);
    }

    fn convertUntrustedAdviceReadAddress(self: *const JoltDevice, address: u64) usize {
        return @intCast(address - self.memory_layout.untrusted_advice_start);
    }

    fn convertWriteAddress(self: *const JoltDevice, address: u64) usize {
        return @intCast(address - self.memory_layout.output_start);
    }
};

test "MemoryLayout initialization" {
    var config = MemoryConfig.default();
    config.program_size = 1024;
    const layout = try MemoryLayout.init(&config);
    try std.testing.expect(layout.program_size == 1024);
}

test "JoltDevice basic operations" {
    const allocator = std.testing.allocator;
    var config = MemoryConfig.default();
    config.program_size = 1024;
    var device = try JoltDevice.init(allocator, &config);
    defer device.deinit();

    try std.testing.expect(device.size() == 0);
    try std.testing.expect(!device.panic);
}
