defmodule App.Cli do
  use Boundary, deps: [App.Domain], exports: []

  alias App.Domain.InvalidAmount
  alias App.Domain.Money
  alias App.Domain.Quote

  @exit_ok 0
  @exit_usage 2

  @spec run([String.t()], IO.device(), IO.device()) :: 0 | 2
  def run([], _out, err) do
    IO.puts(err, "usage: app AMOUNT [AMOUNT ...]")
    @exit_usage
  end

  def run(arguments, out, err) do
    case Quote.of(arguments) do
      {:ok, quote} ->
        IO.puts(out, render(quote))
        @exit_ok

      {:error, %InvalidAmount{} = error} ->
        IO.puts(err, Exception.message(error))
        @exit_usage
    end
  end

  defp render(%Quote{subtotal: subtotal, tier: tier, total: total}) do
    "subtotal=#{Money.render(subtotal)} tier=#{tier.name} total=#{Money.render(total)}"
  end
end
