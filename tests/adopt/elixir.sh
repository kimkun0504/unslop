build_legacy() {
  mkdir -p lib test
  printf 'defmodule Legacy.MixProject do\n  use Mix.Project\n\n  def project do\n    [app: :legacy, version: "0.1.0", elixir: "~> 1.18", deps: []]\n  end\nend\n' > mix.exs
  printf '[inputs: ["{mix,.formatter}.exs", "{lib,test}/**/*.{ex,exs}"]]\n' > .formatter.exs
  printf 'defmodule Legacy do\n  # legacy\n  def add(a, b) do\n    unused = 1\n    a + b\n  end\n\n  def untested, do: :never\nend\n' > lib/legacy.ex
  printf 'ExUnit.start()\n' > test/test_helper.exs
  printf 'defmodule LegacyTest do\n  use ExUnit.Case\n\n  test "adds" do\n    assert Legacy.add(1, 2) == 3\n  end\nend\n' > test/legacy_test.exs
  printf '/_build/\n/deps/\n/cover/\n' > .gitignore
}
cases() {
  printf 'defmodule Legacy.Mul do\n  def of(a, b), do: a * b # product\nend\n' > lib/mul.ex
  expect_fail "comment" "comments are forbidden"
  printf 'defmodule Legacy.Half do\n  def of(value) do\n    unused = 1\n    div(value, 2)\n  end\nend\n' > lib/half.ex
  printf 'defmodule Legacy.HalfTest do\n  use ExUnit.Case\n\n  test "halves" do\n    assert Legacy.Half.of(4) == 2\n  end\nend\n' > test/half_test.exs
  expect_fail "new compiler warning" "is unused"
  printf 'defmodule Legacy.Triple do\n  def of(value), do: value * 3\nend\n' > lib/triple.ex
  expect_fail "untested new code" "every changed line must be covered"
  printf 'defmodule Legacy.Quad do\n  def of( value ),do: value*4\nend\n' > lib/quad.ex
  printf 'defmodule Legacy.QuadTest do\n  use ExUnit.Case\n\n  test "quads" do\n    assert Legacy.Quad.of(1) == 4\n  end\nend\n' > test/quad_test.exs
  expect_fail "unformatted new file" "new file is not formatted"
  printf 'defmodule Legacy.LaterTest do\n  use ExUnit.Case\n\n  @tag :skip\n  test "later" do\n    assert true\n  end\nend\n' > test/later_test.exs
  expect_fail "skipped test" "check-diff"
  printf 'defmodule Legacy.Twice do\n  def of(value), do: value * 2\nend\n' > lib/twice.ex
  printf 'defmodule Legacy.TwiceTest do\n  use ExUnit.Case\n\n  test "doubles" do\n    assert Legacy.Twice.of(2) == 4\n  end\nend\n' > test/twice_test.exs
  expect_pass "clean, tested new code"
}
