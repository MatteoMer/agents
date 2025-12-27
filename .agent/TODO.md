# Jolt zkVM Porting TODO

## Current Status
Starting Phase 1: Foundation (Common & Platform)

## Immediate Tasks

### Project Setup
- [ ] Create target/ directory structure
- [ ] Create build.zig
- [ ] Setup basic module structure

### Phase 1: Common Module
- [ ] Port attributes.rs
- [ ] Port constants.rs
- [ ] Port jolt_device.rs

### Phase 1: Platform Module
- [ ] Port alloc.rs
- [ ] Port cycle_tracking.rs
- [ ] Port malloc_shim.rs
- [ ] Port print.rs
- [ ] Port random.rs

## Completed Tasks
- [x] Initial project analysis
- [x] Created PLAN.md
- [x] Created TODO.md

## Blockers
None currently

## Notes
- Total files to port: ~581
- Core module has ~296 files
- Will need to handle arkworks crypto library dependencies
- Focus on getting basic structure working first, then fill in implementations
