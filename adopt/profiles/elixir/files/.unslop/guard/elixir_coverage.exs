[data, output] = System.argv()
root = File.cwd!() <> "/"
{:ok, _pid} = :cover.start()
:ok = :cover.import(String.to_charlist(data))

classes =
  for module <- :cover.imported_modules(),
      source = module.module_info(:compile)[:source],
      source != nil,
      path = List.to_string(source),
      String.starts_with?(path, root),
      {:ok, rows} = :cover.analyse(module, :calls, :line) do
    relative = String.replace_prefix(path, root, "")

    lines =
      for {{^module, line}, calls} <- rows, line > 0 do
        ~s(<line number="#{line}" hits="#{calls}"/>)
      end

    ~s(<class name="#{inspect(module)}" filename="#{relative}"><lines>#{Enum.join(lines)}</lines></class>)
  end

report =
  ~s(<?xml version="1.0"?><coverage><sources><source>#{root}</source></sources>) <>
    ~s(<packages><package name="elixir"><classes>#{Enum.join(classes)}</classes></package></packages></coverage>)

File.write!(output, report)
