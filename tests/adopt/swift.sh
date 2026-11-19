build_legacy() {
  mkdir -p Sources/Legacy Tests/LegacyTests
  printf '// swift-tools-version: 6.0\nimport PackageDescription\n\nlet package = Package(\n    name: "Legacy",\n    targets: [\n        .target(name: "Legacy"),\n        .testTarget(name: "LegacyTests", dependencies: ["Legacy"]),\n    ]\n)\n' > Package.swift
  printf '// legacy\npublic func add(_ a: Int, _ b: Int) -> Int {\n    let unused = 1\n    return a + b\n}\n\npublic func parse(_ raw: String) -> Int {\n    Int(raw)!\n}\n' > Sources/Legacy/Calc.swift
  printf 'import Legacy\nimport Testing\n\n@Test func adds() {\n    #expect(add(1, 2) == 3)\n}\n' > Tests/LegacyTests/CalcTests.swift
  printf '.build/\n' > .gitignore
}
cases() {
  printf 'public func mul(_ a: Int, _ b: Int) -> Int {\n    a * b \x2f\x2f product\n}\n' > Sources/Legacy/Mul.swift
  expect_fail "comment" "comments are forbidden"
  printf 'public func half(_ raw: String) -> Int {\n    Int(raw)! / 2\n}\n' > Sources/Legacy/Half.swift
  printf 'import Legacy\nimport Testing\n\n@Test func halves() {\n    #expect(half("4") == 2)\n}\n' > Tests/LegacyTests/HalfTests.swift
  expect_fail "new force unwrap" "force_unwrapping"
  printf 'public func waste(_ value: Int) -> Int {\n    let unused = value\n    return 1\n}\n' > Sources/Legacy/Waste.swift
  printf 'import Legacy\nimport Testing\n\n@Test func wastes() {\n    #expect(waste(2) == 1)\n}\n' > Tests/LegacyTests/WasteTests.swift
  expect_fail "new compiler warning" "was never used"
  printf 'public func triple(_ value: Int) -> Int {\n    value * 3\n}\n' > Sources/Legacy/Triple.swift
  expect_fail "untested new code" "every changed line must be covered"
  printf 'import Testing\n\n@Test(.disabled("later")) func later() {}\n' > Tests/LegacyTests/LaterTests.swift
  expect_fail "disabled test" "check-diff"
  printf 'public func twice(_ value: Int) -> Int {\n    value * 2\n}\n' > Sources/Legacy/Twice.swift
  printf 'import Legacy\nimport Testing\n\n@Test func doubles() {\n    #expect(twice(2) == 4)\n}\n' > Tests/LegacyTests/TwiceTests.swift
  expect_pass "clean, tested new code"
}
