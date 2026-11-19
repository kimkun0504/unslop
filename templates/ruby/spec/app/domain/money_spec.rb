RSpec.describe App::Domain::Money do
  describe '.zero' do
    it 'has no cents' do
      expect(described_class.zero.cents).to eq(0)
    end
  end

  describe '.parse' do
    [
      %w[0 0],
      %w[7 700],
      %w[0.09 9],
      [' 12.50 ', '1250'],
      %w[999999999999.99 99999999999999]
    ].each do |raw, cents|
      it "reads #{raw.inspect} as #{cents} cents" do
        expect(described_class.parse(raw).cents).to eq(Integer(cents, 10))
      end
    end

    ['', '-1', '1.5', '1.234', '01', '1.0a', 'x1.00', '1.00x', 'x', '1000000000000'].each do |raw|
      it "rejects #{raw.inspect}" do
        expect { described_class.parse(raw) }
          .to raise_error(App::Domain::InvalidAmount, %(expected a non-negative amount like 12 or 12.50, got "#{raw}"))
      end
    end
  end

  describe '#initialize' do
    [-1, 1.5, '1'].each do |cents|
      it "refuses #{cents.inspect} cents" do
        expect { described_class.new(cents) }
          .to raise_error(ArgumentError, 'cents must be a non-negative Integer')
      end
    end

    it 'freezes the value' do
      expect(described_class.new(0)).to be_frozen
    end
  end

  describe '#plus' do
    it 'adds the cents' do
      expect(described_class.new(125).plus(described_class.new(280)).cents).to eq(405)
    end
  end

  describe '#less_percent' do
    [[100, 5, 95], [99, 50, 49], [99, 0, 99]].each do |cents, percent, expected|
      it "takes #{percent}% off #{cents} cents and rounds down to #{expected}" do
        expect(described_class.new(cents).less_percent(percent).cents).to eq(expected)
      end
    end
  end

  describe '#render' do
    [[0, '0.00'], [5, '0.05'], [1250, '12.50'], [10_000, '100.00']].each do |cents, rendered|
      it "renders #{cents} cents as #{rendered}" do
        expect(described_class.new(cents).render).to eq(rendered)
      end
    end
  end
end
