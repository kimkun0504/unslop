RSpec.describe App::Domain::Tier do
  describe '.for_subtotal' do
    [
      [0, 'standard', 0],
      [9_999, 'standard', 0],
      [10_000, 'silver', 5],
      [10_001, 'silver', 5],
      [49_999, 'silver', 5],
      [50_000, 'gold', 10],
      [50_001, 'gold', 10]
    ].each do |cents, name, percent_off|
      it "puts #{cents} cents in #{name}" do
        tier = described_class.for_subtotal(App::Domain::Money.new(cents))
        expect([tier.name, tier.percent_off]).to eq([name, percent_off])
      end
    end
  end
end
