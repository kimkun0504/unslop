# Project

Rust 2024 edition in a Cargo workspace. `crates/domain` holds pure logic and may not do I/O (its `clippy.toml` bans it); `crates/app` is the command-line adapter. Cargo makes the dependency direction one-way.

- `scripts/setup` checks the toolchain from `rust-toolchain.toml` and the cargo tools, then fetches locked dependencies.
- `scripts/fast-check` must pass before you stop: no comments, suppressions, rustfmt, clippy with `all`, `pedantic`, `nursery`, `cargo` and restriction lints denied, tests.
- `scripts/verify` is what CI runs: fast-check plus cargo-deny, 100% line coverage and a release build.
- `scripts/mutation` runs cargo-mutants and must report no missed mutants.

Parse input into types with private fields and a fallible constructor, as `Money::parse` does. Return `Result`; never `unwrap`, `expect`, `panic!`, index slices or use unchecked arithmetic. Write output through an injected `Write`, never `println!`. `#[allow]` is denied.

You cannot edit `Cargo.toml` files, `Cargo.lock`, `clippy.toml`, `deny.toml` or `rust-toolchain.toml`. If you need a dependency, say which one and why in your final message.
