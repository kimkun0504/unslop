public enum Tier: String, Sendable, CaseIterable {
    case standard
    case silver
    case gold

    private static let silverFromCents = 10_000
    private static let goldFromCents = 50_000
    private static let standardPercentOff = Percent(trusted: 0)
    private static let silverPercentOff = Percent(trusted: 5)
    private static let goldPercentOff = Percent(trusted: 10)

    public var percentOff: Percent {
        switch self {
        case .standard:
            Self.standardPercentOff

        case .silver:
            Self.silverPercentOff

        case .gold:
            Self.goldPercentOff
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
