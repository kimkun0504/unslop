defmodule App.Guard.DomainPurity do
  use Credo.Check,
    base_priority: :high,
    category: :warning,
    explanations: [check: "App.Domain is pure: no I/O, clock, randomness, processes or App.Cli."]

  @forbidden_aliases [
    :IO,
    :File,
    :Path,
    :System,
    :Port,
    :Process,
    :Node,
    :Task,
    :Agent,
    :GenServer,
    :Logger,
    :Application,
    :DateTime,
    :NaiveDateTime,
    :Code
  ]
  @forbidden_erlang [
    :os,
    :file,
    :io,
    :rand,
    :crypto,
    :timer,
    :net,
    :gen_tcp,
    :httpc,
    :persistent_term,
    :ets
  ]

  @impl Credo.Check
  def run(%SourceFile{} = source_file, params) do
    issue_meta = IssueMeta.for(source_file, params)
    Credo.Code.prewalk(source_file, &traverse(&1, &2, issue_meta))
  end

  defp traverse({:__aliases__, meta, [:App, :Cli | _]} = ast, issues, issue_meta) do
    {ast, [issue(issue_meta, meta, "App.Domain must not depend on App.Cli") | issues]}
  end

  defp traverse({:__aliases__, meta, [name | _]} = ast, issues, issue_meta)
       when name in @forbidden_aliases do
    {ast, [io_issue(issue_meta, meta, inspect(name)) | issues]}
  end

  defp traverse({:., meta, [module, _]} = ast, issues, issue_meta)
       when module in @forbidden_erlang do
    {ast, [io_issue(issue_meta, meta, inspect(module)) | issues]}
  end

  defp traverse(ast, issues, _issue_meta), do: {ast, issues}

  defp io_issue(issue_meta, meta, name) do
    issue(issue_meta, meta, "the domain does no I/O: move #{name} behind a port in App.Cli")
  end

  defp issue(issue_meta, meta, message) do
    format_issue(issue_meta, message: message, line_no: meta[:line])
  end
end

defmodule App.Guard.InjectedDevice do
  use Credo.Check,
    base_priority: :high,
    category: :warning,
    explanations: [check: "Output goes to an injected device so it can be tested."]

  @writers [:puts, :write, :binwrite, :warn]

  @impl Credo.Check
  def run(%SourceFile{} = source_file, params) do
    issue_meta = IssueMeta.for(source_file, params)
    Credo.Code.prewalk(source_file, &traverse(&1, &2, issue_meta))
  end

  defp traverse({{:., meta, [{:__aliases__, _, [:IO]}, fun]}, _, args} = ast, issues, issue_meta)
       when (fun in @writers and length(args) == 1) or fun == :inspect do
    message = "write through an injected device, not IO.#{fun} to the process streams"
    {ast, [format_issue(issue_meta, message: message, line_no: meta[:line]) | issues]}
  end

  defp traverse(ast, issues, _issue_meta), do: {ast, issues}
end
