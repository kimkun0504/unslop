build_legacy() {
  dotnet new sln -n Legacy --format slnx > /dev/null
  dotnet new classlib -n Legacy -o src/Legacy --framework net10.0 > /dev/null
  dotnet new xunit -n Legacy.Tests -o tests/Legacy.Tests --framework net10.0 > /dev/null
  dotnet sln Legacy.slnx add src/Legacy/Legacy.csproj tests/Legacy.Tests/Legacy.Tests.csproj > /dev/null
  dotnet add tests/Legacy.Tests/Legacy.Tests.csproj reference src/Legacy/Legacy.csproj > /dev/null
  rm -f src/Legacy/Class1.cs tests/Legacy.Tests/UnitTest1.cs
  printf 'namespace Legacy;\n\n// legacy\npublic class Calc\n{\n    public int Add(int a, int b) { var unused = 1; return a + b; }\n}\n' > src/Legacy/Calc.cs
  printf 'namespace Legacy.Tests;\n\npublic class CalcTests\n{\n    [Fact]\n    public void Adds() => Assert.Equal(3, new Calc().Add(1, 2));\n}\n' > tests/Legacy.Tests/CalcTests.cs
  printf 'bin/\nobj/\n' > .gitignore
}
cases() {
  printf 'namespace Legacy;\n\npublic static class Mul\n{\n    public static int Of(int a, int b) => a * b; // product\n}\n' > src/Legacy/Mul.cs
  expect_fail "comment" "comments are forbidden"
  printf 'namespace Legacy;\n\npublic class Waste\n{\n    public int Value() => 2;\n}\n' > src/Legacy/Waste.cs
  printf 'namespace Legacy.Tests;\n\npublic class WasteTests\n{\n    [Fact]\n    public void Values() => Assert.Equal(2, new Waste().Value());\n}\n' > tests/Legacy.Tests/WasteTests.cs
  expect_fail "new analyzer finding" "CA1822"
  printf 'namespace Legacy;\n\npublic static class Triple\n{\n    public static int Of(int value) => value * 3;\n}\n' > src/Legacy/Triple.cs
  expect_fail "untested new code" "every changed line must be covered"
  printf 'namespace Legacy.Tests;\n\npublic class LaterTests\n{\n    [Fact(Skip = "later")]\n    public void Later() { }\n}\n' > tests/Legacy.Tests/LaterTests.cs
  expect_fail "skipped test" "new skip or suppression"
  printf 'namespace Legacy;\n\npublic static class Twice\n{\n    public static int Of(int value) => value * 2;\n}\n' > src/Legacy/Twice.cs
  printf 'namespace Legacy.Tests;\n\npublic class TwiceTests\n{\n    [Fact]\n    public void Doubles() => Assert.Equal(4, Twice.Of(2));\n}\n' > tests/Legacy.Tests/TwiceTests.cs
  expect_pass "clean, tested new code"
}
