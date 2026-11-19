defmodule App.Domain.Quote do
  alias App.Domain.InvalidAmount
  alias App.Domain.Money
  alias App.Domain.Tier

  @enforce_keys [:subtotal, :tier, :total]
  defstruct [:subtotal, :tier, :total]

  @type t :: %__MODULE__{subtotal: Money.t(), tier: Tier.t(), total: Money.t()}

  @spec of([String.t()]) :: {:ok, t()} | {:error, InvalidAmount.t()}
  def of(lines) when is_list(lines) do
    with {:ok, subtotal} <- sum(lines, Money.zero()) do
      tier = Tier.for_subtotal(subtotal)
      {:ok, %__MODULE__{subtotal: subtotal, tier: tier, total: Money.less_percent(subtotal, tier.percent_off)}}
    end
  end

  defp sum([], total), do: {:ok, total}

  defp sum([line | rest], total) do
    with {:ok, amount} <- Money.parse(line) do
      sum(rest, Money.plus(total, amount))
    end
  end
end
