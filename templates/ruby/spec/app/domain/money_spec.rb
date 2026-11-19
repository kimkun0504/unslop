RSpec.describe App::Domain::Money do
  describe '.parse' do
    [
      %w[0 0.00],
      %w[7 7.00],
      %w[0.09 0.09],
      [' 12.50 ', '12.50'],
      %w[999999999999.99 999999999999.99]
    ].each do |raw, rendered|
      it "reads #{raw.inspect} as #{rendered}" do
        expect(described_class.parse(raw).render).to eq(rendered)
      end
    end

    ['', '-1', '1.5', '1.234', '01', '1.0a', 'x', '1000000000000'].each do |raw|
      it "rejects #{raw.inspect}" do
        expect { described_class.parse(raw) }
          .to raise_error(App::Domain::InvalidAmount, %(expected a non-negative amount like 12 or 12.50, got "#{raw}"))
      end
    end
  end

  describe '.new' do
    [-1, 1.5, '1'].each do |cents|
      it "refuses #{cents.inspect} cents" do
        expect { described_class.new(cents) }
          .to raise_error(ArgumentError, 'cents must be a non-negative Integer')
      end
    end

    it 'is frozen' do
      expect(described_class.zero).to be_frozen
    end
  end

  it 'adds' do
    expect(described_class.parse('1.25').plus(described_class.parse('2.80')).render).to eq('4.05')
  end

  it 'rounds a percentage off down to the cent' do
    expect(described_class.parse('0.99').less_percent(5).render).to eq('0.94')
  end
end
