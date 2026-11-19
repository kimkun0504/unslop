RSpec.describe App::Domain::Tier do
  it "is frozen" do
    expect(described_class::GOLD).to be_frozen
  end
end
