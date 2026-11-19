require "coverage"

Coverage.start(lines: true)

at_exit do
  root = "#{Dir.pwd}/"
  skipped = %r{\A(?:vendor|spec|test|\.unslop|\.bundle)/}
  measured = Coverage.result.filter_map do |path, data|
    next unless path.start_with?(root)

    relative = path.delete_prefix(root)
    next if relative.match?(skipped)

    lines = data.is_a?(Hash) ? data[:lines] : data
    [relative, lines]
  end
  loaded = measured.to_h { |relative, _| [relative, true] }
  Dir.glob("{lib,app}/**/*.rb", base: root).each do |relative|
    next if loaded[relative]

    measured << [relative, Coverage.line_stub(File.join(root, relative))]
  end
  next if measured.empty?

  classes = measured.map do |relative, lines|
    rows = lines.each_with_index.filter_map { |hits, index| hits && %(<line number="#{index + 1}" hits="#{hits}"/>) }
    %(<class name="#{relative}" filename="#{relative}"><lines>#{rows.join}</lines></class>)
  end
  report = %(<?xml version="1.0"?><coverage><sources><source>#{root}</source></sources>) +
           %(<packages><package name="ruby"><classes>#{classes.join}</classes></package></packages></coverage>)
  File.write(File.join(root, ".unslop/out/ruby-coverage-#{Process.pid}.xml"), report)
end
