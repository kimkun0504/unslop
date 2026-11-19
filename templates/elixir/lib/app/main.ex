defmodule App.Main do
  use Boundary, deps: [App.Cli], exports: []

  @spec main([String.t()]) :: no_return()
  def main(arguments) do
    arguments |> App.Cli.run(:stdio, :standard_error) |> System.halt()
  end
end
