build_legacy() {
  mkdir -p lib spec
  printf 'source "https://rubygems.org"\n\ngem "rspec", "~> 3.13"\n' > Gemfile
  printf '# legacy\ndef add(a,b)\n  unused = 1\n  a+b\nend\n' > lib/calc.rb
  printf 'require_relative "../lib/calc"\n\nRSpec.describe "add" do\n  it "adds" do\n    expect(add(1, 2)).to eq(3)\n  end\nend\n' > spec/calc_spec.rb
  printf 'vendor/\n.bundle/\n' > .gitignore
  bundle lock --quiet
}
cases() {
  printf '# frozen_string_literal: true\n\ndef mul(a, b)\n  a * b # product\nend\n' > lib/mul.rb
  expect_fail "comment" "comments are forbidden"
  printf 'def half(value)\n  unused = 1\n  value / 2\nend\n' > lib/half.rb
  printf 'require_relative "../lib/half"\n\nRSpec.describe "half" do\n  it "halves" do\n    expect(half(4)).to eq(2)\n  end\nend\n' > spec/half_spec.rb
  expect_fail "new RuboCop finding" "Lint/UselessAssignment"
  printf 'def triple(value)\n  value * 3\nend\n' > lib/triple.rb
  expect_fail "untested new code" "every changed line must be covered"
  printf 'RSpec.describe "later" do\n  it "waits" do\n    skip "later"\n  end\nend\n' > spec/later_spec.rb
  expect_fail "skipped spec" "check-diff"
  printf 'def twice(value)\n  value * 2\nend\n' > lib/twice.rb
  printf 'require_relative "../lib/twice"\n\nRSpec.describe "twice" do\n  it "doubles" do\n    expect(twice(2)).to eq(4)\n  end\nend\n' > spec/twice_spec.rb
  expect_pass "clean, tested new code"
}
