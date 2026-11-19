public struct Quote: Equatable, Sendable {
    public let subtotal: Money
    public let tier: Tier
    public let total: Money

    public static func of(_ lines: [String]) throws(InvalidAmount) -> Self {
        var subtotal = Money.zero
        for line in lines {
            subtotal = subtotal.plus(try Money.parse(line))
        }
        let tier = Tier.forSubtotal(subtotal)
        return Self(subtotal: subtotal, tier: tier, total: subtotal.lessPercent(tier.percentOff))
    }
}
