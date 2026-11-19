import Domain
import Testing

struct TierTests {
    @Test(arguments: [
        (0, Tier.standard), (9_999, .standard), (10_000, .silver), (49_999, .silver), (50_000, .gold),
    ])
    func placesSubtotal(cents: Int, tier: Tier) throws {
        #expect(Tier.forSubtotal(try #require(Money(cents: cents))) == tier)
    }

    @Test(arguments: [(Tier.standard, 0), (.silver, 5), (.gold, 10)])
    func discounts(tier: Tier, percentOff: Int) {
        #expect(tier.percentOff == percentOff)
    }
}
