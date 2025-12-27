// Random number generation for guest environment
// Ported from Rust to Zig
//
// WARNING: This is a deterministic PRNG implementation.
// It is NOT cryptographically secure. Use with caution.

const std = @import("std");
const print = @import("print.zig");

// JOLT in ASCII padded with 1s
const SEED: u64 = 0x11114A4F4C541111;

var rng_state: ?std.rand.DefaultPrng = null;

/// Get random bytes using a deterministic PRNG
/// WARNING: This is NOT cryptographically secure!
pub fn sysRand(dest: []u8) void {
    // Print warning on first use
    if (rng_state == null) {
        print.println("Warning: sys_rand is a deterministic PRNG, not a cryptographically secure RNG. Use with caution.");
        rng_state = std.rand.DefaultPrng.init(SEED);
    }

    if (rng_state) |*rng| {
        rng.fill(dest);
    }
}

/// Get a single random u64
pub fn randU64() u64 {
    if (rng_state == null) {
        print.println("Warning: sys_rand is a deterministic PRNG, not a cryptographically secure RNG. Use with caution.");
        rng_state = std.rand.DefaultPrng.init(SEED);
    }

    if (rng_state) |*rng| {
        return rng.random().int(u64);
    }
    return 0;
}

/// Reset the RNG state (useful for testing)
pub fn resetRng() void {
    rng_state = null;
}

test "random generation" {
    var buffer: [32]u8 = undefined;
    sysRand(&buffer);

    // Check that we got some data (not all zeros)
    var all_zeros = true;
    for (buffer) |byte| {
        if (byte != 0) {
            all_zeros = false;
            break;
        }
    }
    try std.testing.expect(!all_zeros);
}

test "deterministic random" {
    resetRng();
    var buffer1: [32]u8 = undefined;
    sysRand(&buffer1);

    resetRng();
    var buffer2: [32]u8 = undefined;
    sysRand(&buffer2);

    // Should produce the same sequence with the same seed
    try std.testing.expectEqualSlices(u8, &buffer1, &buffer2);
}
