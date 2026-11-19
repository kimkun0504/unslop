require "open3"
require "stringio"

RSpec.describe App::Cli::Application do
  def call(*arguments)
    out = StringIO.new
    err = StringIO.new
    code = described_class.new(out, err).run(arguments)
    [code, out.string, err.string]
  end

  it "prints the quote" do
    expect(call("60", "40")).to eq([0, "subtotal=100.00 tier=silver total=95.00\n", ""])
  end

  it "rejects missing amounts" do
    expect(call).to eq([2, "", "usage: app AMOUNT [AMOUNT ...]\n"])
  end

  it "rejects malformed amounts" do
    expect(call("1.5")).to eq([2, "", %(expected a non-negative amount like 12 or 12.50, got "1.5"\n)])
  end

  it "is frozen" do
    expect(described_class.new(StringIO.new, StringIO.new)).to be_frozen
  end

  it "wires the standard streams in bin/app" do
    out, err, status = Open3.capture3(RbConfig.ruby, File.expand_path("../../../bin/app", __dir__), "500")
    expect([status.exitstatus, out, err]).to eq([0, "subtotal=500.00 tier=gold total=450.00\n", ""])
  end
end
