defmodule App.Domain.TierTest do
  use ExUnit.Case, async: true

  alias App.Domain.Money
  alias App.Domain.Tier

  for {cents, name, percent_off} <- [
        {0, "standard", 0},
        {9_999, "standard", 0},
        {10_000, "silver", 5},
        {49_999, "silver", 5},
        {50_000, "gold", 10}
      ] do
    test "puts #{cents} cents in #{name}" do
      assert Tier.for_subtotal(%Money{cents: unquote(cents)}) ==
               %Tier{name: unquote(name), percent_off: unquote(percent_off)}
    end
  end
end
