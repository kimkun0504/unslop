defmodule App.Domain.QuoteTest do
  use ExUnit.Case, async: true

  alias App.Domain.InvalidAmount
  alias App.Domain.Money
  alias App.Domain.Quote

  for {lines, expected} <- [
        {[], "0.00 standard 0.00"},
        {["99.99"], "99.99 standard 99.99"},
        {["60", "40"], "100.00 silver 95.00"},
        {["499.99"], "499.99 silver 474.99"},
        {["500"], "500.00 gold 450.00"}
      ] do
    test "quotes #{inspect(lines)} as #{expected}" do
      assert {:ok, quote} = Quote.of(unquote(lines))

      assert "#{Money.render(quote.subtotal)} #{quote.tier.name} #{Money.render(quote.total)}" ==
               unquote(expected)
    end
  end

  test "reports the first malformed line" do
    assert Quote.of(["1", "x", "y"]) == {:error, %InvalidAmount{raw: "x"}}
  end
end
