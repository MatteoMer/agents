// Bump allocator for guest RISC-V environment
// Ported from Rust to Zig

const std = @import("std");

/// Simple bump allocator that never frees memory
/// This is suitable for guest environments where memory is managed externally
pub const BumpAllocator = struct {
    next: usize = 0,
    heap_ptr: ?*u8 = null,

    /// Align address up to the specified alignment
    fn alignUp(addr: usize, align_val: usize) usize {
        return (addr + align_val - 1) & ~(align_val - 1);
    }

    /// Allocate memory with specified size and alignment
    pub fn alloc(self: *BumpAllocator, size: usize, alignment: usize) ?*u8 {
        var next = self.next;

        // Initialize heap pointer on first allocation
        if (next == 0) {
            if (self.heap_ptr) |ptr| {
                next = @intFromPtr(ptr);
            } else {
                // In a real RISC-V environment, this would reference _HEAP_PTR from linker script
                return null;
            }
        }

        next = alignUp(next, alignment);
        const ptr: *u8 = @ptrFromInt(next);
        next += size;
        self.next = next;

        return ptr;
    }

    /// Deallocate does nothing in a bump allocator
    pub fn dealloc(_: *BumpAllocator, _: *u8, _: usize, _: usize) void {
        // No-op: bump allocator never frees
    }
};

/// Create a Zig allocator interface from BumpAllocator
pub fn bumpAllocator(bump: *BumpAllocator) std.mem.Allocator {
    return std.mem.Allocator{
        .ptr = bump,
        .vtable = &.{
            .alloc = allocFn,
            .resize = resizeFn,
            .free = freeFn,
        },
    };
}

fn allocFn(ctx: *anyopaque, len: usize, ptr_align: u8, _: usize) ?[*]u8 {
    const bump: *BumpAllocator = @ptrCast(@alignCast(ctx));
    const alignment = @as(usize, 1) << @intCast(ptr_align);
    return @ptrCast(bump.alloc(len, alignment));
}

fn resizeFn(_: *anyopaque, _: []u8, _: u8, _: usize, _: usize) bool {
    // Can't resize in a bump allocator
    return false;
}

fn freeFn(_: *anyopaque, _: []u8, _: u8, _: usize) void {
    // No-op: bump allocator never frees
}

test "BumpAllocator basic allocation" {
    var bump = BumpAllocator{};
    // Set a fake heap pointer for testing
    var heap: [1024]u8 = undefined;
    bump.heap_ptr = &heap[0];

    const ptr1 = bump.alloc(16, 8);
    try std.testing.expect(ptr1 != null);

    const ptr2 = bump.alloc(32, 8);
    try std.testing.expect(ptr2 != null);

    // Check that ptr2 is after ptr1
    try std.testing.expect(@intFromPtr(ptr2.?) > @intFromPtr(ptr1.?));
}

test "BumpAllocator alignment" {
    var bump = BumpAllocator{};
    var heap: [1024]u8 = undefined;
    bump.heap_ptr = &heap[0];

    const ptr = bump.alloc(1, 16);
    try std.testing.expect(ptr != null);
    // Check alignment
    try std.testing.expect(@intFromPtr(ptr.?) % 16 == 0);
}
