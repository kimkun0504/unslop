defmodule App.Domain.InvalidAmount do
  defexception [:raw]

  @type t :: %__MODULE__{raw: String.t()}

  @impl Exception
  def message(%__MODULE__{raw: raw}) do
    ~s(expected a non-negative amount like 12 or 12.50, got "#{raw}")
  end
end
