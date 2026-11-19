build_legacy() {
  mkdir -p src tests
  printf '[package]\nname = "legacy"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\n' > Cargo.toml
  printf '// legacy\npub fn add(a: i32, b: i32) -> i32 { let unused = 1; a + b }\n\npub fn parse(s: &str) -> i32 { s.parse().unwrap() }\n' > src/lib.rs
  printf 'use legacy::add;\n\n#[test]\nfn adds() {\n    assert_eq!(add(1, 2), 3);\n}\n' > tests/calc.rs
  printf 'target/\n' > .gitignore
  cargo generate-lockfile
}
cases() {
  printf '\npub mod mul;\n' >> src/lib.rs
  printf '#[must_use]\npub const fn mul(a: i32, b: i32) -> i32 {\n    a * b \x2f\x2f product\n}\n' > src/mul.rs
  expect_fail "comment" "comments are forbidden"
  printf '\npub mod half;\n' >> src/lib.rs
  printf '#[must_use]\npub fn half(raw: &str) -> i32 {\n    raw.parse::<i32>().unwrap() / 2\n}\n' > src/half.rs
  printf 'use legacy::half::half;\n\n#[test]\nfn halves() {\n    assert_eq!(half("4"), 2);\n}\n' > tests/half.rs
  expect_fail "unwrap in new code" "clippy::unwrap_used"
  printf '\npub mod triple;\n' >> src/lib.rs
  printf '#[must_use]\npub const fn triple(value: i32) -> i32 {\n    value * 3\n}\n' > src/triple.rs
  expect_fail "untested new code" "every changed line must be covered"
  printf '\npub mod quad;\n' >> src/lib.rs
  printf '#[must_use] pub const fn quad(value: i32) -> i32 { value * 4 }\n' > src/quad.rs
  printf 'use legacy::quad::quad;\n\n#[test]\nfn quads() {\n    assert_eq!(quad(1), 4);\n}\n' > tests/quad.rs
  expect_fail "unformatted new file" "new file is not formatted"
  printf '#[test]\n#[ignore = "later"]\nfn later() {}\n' > tests/later.rs
  expect_fail "ignored test" "new skip or suppression"
  printf '\npub mod double;\n' >> src/lib.rs
  printf '#[must_use]\npub const fn double(value: i32) -> i32 {\n    value * 2\n}\n' > src/double.rs
  printf 'use legacy::double::double;\n\n#[test]\nfn doubles() {\n    assert_eq!(double(2), 4);\n}\n' > tests/double.rs
  expect_pass "clean, tested new code"
}
