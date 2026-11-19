defmodule App.Domain.Money do
  alias App.Domain.InvalidAmount

  @enforce_keys [:cents]
  defstruct [:cents]

  @type t :: %__MODULE__{cents: non_neg_integer()}

  @cents_per_unit 100

  @spec zero() :: t()
  def zero, do: %__MODULE__{cents: 0}

  @spec parse(String.t()) :: {:ok, t()} | {:error, InvalidAmount.t()}
  def parse(raw) when is_binary(raw) do
    trimmed = String.trim(raw)
    canonical = if String.contains?(trimmed, "."), do: trimmed, else: trimmed <> ".00"

    if Regex.match?(canonical_pattern(), canonical) do
      {:ok, %__MODULE__{cents: canonical |> String.replace(".", "") |> String.to_integer()}}
    else
      {:error, %InvalidAmount{raw: raw}}
    end
  end

  @spec plus(t(), t()) :: t()
  def plus(%__MODULE__{cents: left}, %__MODULE__{cents: right}) do
    %__MODULE__{cents: left + right}
  end

  @spec less_percent(t(), 0..100) :: t()
  def less_percent(%__MODULE__{cents: cents}, percent) when percent in 0..100 do
    %__MODULE__{cents: div(cents * (100 - percent), 100)}
  end

  @spec render(t()) :: String.t()
  def render(%__MODULE__{cents: cents}) do
    units = div(cents, @cents_per_unit)
    rest = cents |> rem(@cents_per_unit) |> Integer.to_string() |> String.pad_leading(2, "0")
    "#{units}.#{rest}"
  end

  defp canonical_pattern, do: ~r/\A(?:0|[1-9][0-9]{0,11})\.[0-9]{2}\z/
end
