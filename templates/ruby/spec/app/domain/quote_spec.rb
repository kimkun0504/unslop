RSpec.describe App::Domain::Quote do
  describe '.of' do
    {
      [] => '0.00 standard 0.00',
      ['99.99'] => '99.99 standard 99.99',
      %w[60 40] => '100.00 silver 95.00',
      ['499.99'] => '499.99 silver 474.99',
      ['500'] => '500.00 gold 450.00'
    }.each do |lines, expected|
      it "quotes #{lines.inspect} as #{expected}" do
        quote = described_class.of(*lines)
        expect("#{quote.subtotal.render} #{quote.tier.name} #{quote.total.render}").to eq(expected)
      end
    end

    it 'reports the first malformed line' do
      expect { described_class.of('1', 'x', 'y') }
        .to raise_error(App::Domain::InvalidAmount, 'expected a non-negative amount like 12 or 12.50, got "x"')
    end
  end

  describe '#initialize' do
    let(:subtotal) { App::Domain::Money.new(100) }
    let(:total)    { App::Domain::Money.new(90) }
    let(:quote)    { described_class.new(subtotal, App::Domain::Tier::GOLD, total) }

    it 'keeps its parts' do
      expect([quote.subtotal, quote.tier, quote.total]).to eq([subtotal, App::Domain::Tier::GOLD, total])
    end

    it 'freezes the quote' do
      expect(quote).to be_frozen
    end
  end
end
