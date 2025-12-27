const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Common library (foundation)
    const common = b.addStaticLibrary(.{
        .name = "jolt-common",
        .root_source_file = b.path("common/lib.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(common);

    // Platform library (guest execution platform)
    const platform = b.addStaticLibrary(.{
        .name = "jolt-platform",
        .root_source_file = b.path("jolt-platform/lib.zig"),
        .target = target,
        .optimize = optimize,
    });
    platform.root_module.addImport("common", &common.root_module);
    b.installArtifact(platform);

    // Tracer library (instruction tracing)
    const tracer = b.addStaticLibrary(.{
        .name = "jolt-tracer",
        .root_source_file = b.path("tracer/lib.zig"),
        .target = target,
        .optimize = optimize,
    });
    tracer.root_module.addImport("common", &common.root_module);
    b.installArtifact(tracer);

    // Core library (main zkVM implementation)
    const core = b.addStaticLibrary(.{
        .name = "jolt-core",
        .root_source_file = b.path("jolt-core/lib.zig"),
        .target = target,
        .optimize = optimize,
    });
    core.root_module.addImport("common", &common.root_module);
    core.root_module.addImport("platform", &platform.root_module);
    core.root_module.addImport("tracer", &tracer.root_module);
    b.installArtifact(core);

    // Main executable
    const exe = b.addExecutable(.{
        .name = "jolt",
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });
    exe.root_module.addImport("common", &common.root_module);
    exe.root_module.addImport("platform", &platform.root_module);
    exe.root_module.addImport("tracer", &tracer.root_module);
    exe.root_module.addImport("core", &core.root_module);
    b.installArtifact(exe);

    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());
    if (b.args) |args| {
        run_cmd.addArgs(args);
    }

    const run_step = b.step("run", "Run the app");
    run_step.dependOn(&run_cmd.step);

    // Tests
    const common_tests = b.addTest(.{
        .root_source_file = b.path("common/lib.zig"),
        .target = target,
        .optimize = optimize,
    });

    const platform_tests = b.addTest(.{
        .root_source_file = b.path("jolt-platform/lib.zig"),
        .target = target,
        .optimize = optimize,
    });
    platform_tests.root_module.addImport("common", &common.root_module);

    const tracer_tests = b.addTest(.{
        .root_source_file = b.path("tracer/lib.zig"),
        .target = target,
        .optimize = optimize,
    });
    tracer_tests.root_module.addImport("common", &common.root_module);

    const core_tests = b.addTest(.{
        .root_source_file = b.path("jolt-core/lib.zig"),
        .target = target,
        .optimize = optimize,
    });
    core_tests.root_module.addImport("common", &common.root_module);
    core_tests.root_module.addImport("platform", &platform.root_module);
    core_tests.root_module.addImport("tracer", &tracer.root_module);

    const run_common_tests = b.addRunArtifact(common_tests);
    const run_platform_tests = b.addRunArtifact(platform_tests);
    const run_tracer_tests = b.addRunArtifact(tracer_tests);
    const run_core_tests = b.addRunArtifact(core_tests);

    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_common_tests.step);
    test_step.dependOn(&run_platform_tests.step);
    test_step.dependOn(&run_tracer_tests.step);
    test_step.dependOn(&run_core_tests.step);
}
