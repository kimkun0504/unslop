defmodule App.Domain do
  use Boundary, deps: [], exports: [InvalidAmount, Money, Quote, Tier]
end
