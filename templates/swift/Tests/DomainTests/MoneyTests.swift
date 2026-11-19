import Domain
import Testing

struct MoneyTests {
    @Test(arguments: [
        ("0", 0), ("7", 700), ("0.09", 9), (" 12.50 ", 1250), ("999999999999.99", 99_999_999_999_999),
    ])
    func reads(raw: String, cents: Int) throws {
        #expect(try Money.parse(raw).cents == cents)
    }

    @Test(arguments: ["", "-1", "1.5", "1.234", "01", "1.0a", "x1.00", "1.00x", "x", "1000000000000"])
    func rejects(raw: String) {
        #expect(throws: InvalidAmount(raw: raw)) { try Money.parse(raw) }
        #expect(
            InvalidAmount(raw: raw).description
                == "expected a non-negative amount like 12 or 12.50, got \"\(raw)\""
        )
    }

    @Test func refusesNegativeCents() {
        #expect(Money(cents: -1) == nil)
        #expect(Money(cents: 0) == Money.zero)
    }

    @Test func adds() throws {
        let sum = try #require(Money(cents: 125)).plus(try #require(Money(cents: 280)))
        #expect(sum.cents == 405)
    }

    @Test(arguments: [(100, 5, 95), (99, 50, 49), (99, 0, 99), (99, 100, 0)])
    func takesPercentOff(cents: Int, percent: Int, expected: Int) throws {
        #expect(try #require(Money(cents: cents)).lessPercent(percent).cents == expected)
    }

    @Test(arguments: [(0, "0.00"), (5, "0.05"), (1250, "12.50"), (10_000, "100.00")])
    func renders(cents: Int, rendered: String) throws {
        #expect(try #require(Money(cents: cents)).rendered == rendered)
    }
}
