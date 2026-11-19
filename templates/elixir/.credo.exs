%{
  configs: [
    %{
      name: "default",
      strict: true,
      color: false,
      files: %{included: ["lib/", "test/", "tools/"], excluded: [~r"/_build/", ~r"/deps/"]},
      requires: ["tools/guard/credo_guards.ex"],
      checks: %{
        extra: [
          {App.Guard.DomainPurity, files: %{included: ["lib/app/domain.ex", "lib/app/domain/"]}},
          {App.Guard.InjectedDevice, files: %{included: ["lib/"]}},
          {Credo.Check.Readability.Specs, []},
          {Credo.Check.Readability.StrictModuleLayout, []},
          {Credo.Check.Readability.AliasAs, []},
          {Credo.Check.Readability.ImplTrue, []},
          {Credo.Check.Readability.SeparateAliasRequire, []},
          {Credo.Check.Refactor.ABCSize, max_size: 25},
          {Credo.Check.Refactor.AppendSingleItem, []},
          {Credo.Check.Refactor.DoubleBooleanNegation, []},
          {Credo.Check.Refactor.FilterReject, []},
          {Credo.Check.Refactor.MapMap, []},
          {Credo.Check.Refactor.NegatedIsNil, []},
          {Credo.Check.Refactor.RejectReject, []},
          {Credo.Check.Warning.LeakyEnvironment, []},
          {Credo.Check.Warning.MapGetUnsafePass, []},
          {Credo.Check.Warning.MixEnv, []},
          {Credo.Check.Warning.UnsafeToAtom, []}
        ],
        disabled: [
          {Credo.Check.Readability.ModuleDoc, []}
        ]
      }
    }
  ]
}
