defmodule App.Domain.MoneyTest do
  use ExUnit.Case, async: true
  use ExUnitProperties

  alias App.Domain.InvalidAmount
  alias App.Domain.Money

  test "zero has no cents" do
    assert Money.zero() == %Money{cents: 0}
  end

  for {raw, cents} <- [
        {"0", 0},
        {"7", 700},
        {"0.09", 9},
        {" 12.50 ", 1250},
        {"999999999999.99", 99_999_999_999_999}
      ] do
    test "reads #{inspect(raw)} as #{cents} cents" do
      assert Money.parse(unquote(raw)) == {:ok, %Money{cents: unquote(cents)}}
    end
  end

  for raw <- ["", "-1", "1.5", "1.234", "01", "1.0a", "x1.00", "1.00x", "x", "1000000000000"] do
    test "rejects #{inspect(raw)}" do
      assert {:error, %InvalidAmount{} = error} = Money.parse(unquote(raw))

      assert Exception.message(error) ==
               ~s(expected a non-negative amount like 12 or 12.50, got "#{unquote(raw)}")
    end
  end

  test "adds" do
    assert Money.plus(%Money{cents: 125}, %Money{cents: 280}) == %Money{cents: 405}
  end

  for {cents, percent, expected} <- [{100, 5, 95}, {99, 50, 49}, {99, 0, 99}, {99, 100, 0}] do
    test "takes #{percent}% off #{cents} cents, rounding down to #{expected}" do
      assert Money.less_percent(%Money{cents: unquote(cents)}, unquote(percent)) ==
               %Money{cents: unquote(expected)}
    end
  end

  for {cents, rendered} <- [{0, "0.00"}, {5, "0.05"}, {1250, "12.50"}, {10_000, "100.00"}] do
    test "renders #{cents} cents as #{rendered}" do
      assert Money.render(%Money{cents: unquote(cents)}) == unquote(rendered)
    end
  end

  property "rendering and parsing round-trip" do
    check all(cents <- integer(0..99_999_999_999_999)) do
      money = %Money{cents: cents}
      assert Money.parse(Money.render(money)) == {:ok, money}
    end
  end
end
