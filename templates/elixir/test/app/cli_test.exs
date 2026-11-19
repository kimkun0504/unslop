defmodule App.CliTest do
  use ExUnit.Case, async: true

  alias App.Cli

  defp call(arguments) do
    {:ok, out} = StringIO.open("")
    {:ok, err} = StringIO.open("")
    code = Cli.run(arguments, out, err)
    {code, StringIO.flush(out), StringIO.flush(err)}
  end

  test "prints the quote" do
    assert call(["60", "40"]) == {0, "subtotal=100.00 tier=silver total=95.00\n", ""}
  end

  test "rejects missing amounts" do
    assert call([]) == {2, "", "usage: app AMOUNT [AMOUNT ...]\n"}
  end

  test "rejects malformed amounts" do
    assert call(["1.5"]) ==
             {2, "", ~s(expected a non-negative amount like 12 or 12.50, got "1.5"\n)}
  end
end
