build_legacy() {
  printf 'module example.com/legacy\n\ngo 1.26.0\n' > go.mod
  printf 'package legacy\n\nimport "fmt"\n\n// Add adds.\nfunc Add(a, b int) int {\n\tfmt.Println("adding")\n\treturn a + b\n}\n' > calc.go
  printf 'package legacy\n\nimport "testing"\n\nfunc TestAdd(t *testing.T) {\n\tif Add(1, 2) != 3 {\n\t\tt.Fatal("sum")\n\t}\n}\n' > calc_test.go
}
cases() {
  printf 'package legacy\n\nfunc Mul(a, b int) int {\n\treturn a * b \x2f\x2f product\n}\n' > mul.go
  printf 'package legacy\n\nimport "testing"\n\nfunc TestMul(t *testing.T) {\n\tt.Parallel()\n\tif Mul(2, 3) != 6 {\n\t\tt.Fatal("product")\n\t}\n}\n' > mul_test.go
  expect_fail "comment" "comments are forbidden"
  printf 'package legacy\n\nimport "fmt"\n\nfunc Shout(word string) {\n\tfmt.Println(word)\n}\n' > shout.go
  printf 'package legacy\n\nimport "testing"\n\nfunc TestShout(t *testing.T) {\n\tt.Parallel()\n\tShout("a")\n}\n' > shout_test.go
  expect_fail "print in new code" "forbidigo"
  printf 'package legacy\n\nfunc Triple(value int) int {\n\treturn value * 3\n}\n' > triple.go
  expect_fail "untested new code" "every changed line must be covered"
  printf 'package legacy\n\nfunc Quad( value int ) int {\n    return value*4\n}\n' > quad.go
  printf 'package legacy\n\nimport "testing"\n\nfunc TestQuad(t *testing.T) {\n\tt.Parallel()\n\tif Quad(1) != 4 {\n\t\tt.Fatal("quad")\n\t}\n}\n' > quad_test.go
  expect_fail "unformatted new file" "new file is not formatted"
  printf 'package legacy\n\nimport "testing"\n\nfunc TestLater(t *testing.T) {\n\tt.Skip("later")\n}\n' > later_test.go
  expect_fail "skipped test" "check-diff"
  printf 'package legacy\n\nfunc Mul(a, b int) int {\n\treturn a * b\n}\n' > mul.go
  printf 'package legacy_test\n\nimport (\n\t"testing"\n\n\t"example.com/legacy"\n)\n\nfunc TestMul(t *testing.T) {\n\tt.Parallel()\n\n\tif legacy.Mul(2, 3) != 6 {\n\t\tt.Fatal("product")\n\t}\n}\n' > mul_test.go
  expect_pass "clean, tested new code"
}
