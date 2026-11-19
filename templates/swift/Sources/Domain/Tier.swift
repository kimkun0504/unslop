public enum Tier: String, Sendable, CaseIterable {
    case standard
    case silver
    case gold

    private static let silverFromCents = 10_000
    private static let goldFromCents = 50_000
    private static let standardPercentOff = 0
    private static let silverPercentOff = 5
    private static let goldPercentOff = 10

    public var percentOff: Percent {
        switch self {
        case .standard:
            Percent(trusted: Self.standardPercentOff)

        case .silver:
            Percent(trusted: Self.silverPercentOff)

        case .gold:
            Percent(trusted: Self.goldPercentOff)
        }
    }

    public static func forSubtotal(_ subtotal: Money) -> Self {
        if subtotal.cents >= goldFromCents {
            return .gold
        }
        if subtotal.cents >= silverFromCents {
            return .silver
        }
        return .standard
    }
}
