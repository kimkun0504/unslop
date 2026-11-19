defmodule App.Domain.Tier do
  alias App.Domain.Money

  @enforce_keys [:name, :percent_off]
  defstruct [:name, :percent_off]

  @type t :: %__MODULE__{name: String.t(), percent_off: 0..100}

  @silver_from_cents 10_000
  @gold_from_cents 50_000

  @spec for_subtotal(Money.t()) :: t()
  def for_subtotal(%Money{cents: cents}) when cents >= @gold_from_cents, do: gold()
  def for_subtotal(%Money{cents: cents}) when cents >= @silver_from_cents, do: silver()
  def for_subtotal(%Money{}), do: standard()

  @spec standard() :: t()
  def standard, do: %__MODULE__{name: "standard", percent_off: 0}

  @spec silver() :: t()
  def silver, do: %__MODULE__{name: "silver", percent_off: 5}

  @spec gold() :: t()
  def gold, do: %__MODULE__{name: "gold", percent_off: 10}
end
