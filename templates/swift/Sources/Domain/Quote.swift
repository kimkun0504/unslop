public struct Quote: Equatable, Sendable {
    public let subtotal: Money
    public let tier: Tier
    public let total: Money

    public static func of(_ lines: [String]) throws(InvalidAmount) -> Self {
        var sum = Money.zero
        for line in lines {
            sum = sum.plus(try Money.parse(line))
        }
        let level = Tier.forSubtotal(sum)
        return Self(subtotal: sum, tier: level, total: sum.lessPercent(level.percentOff))
    }
}
