public enum Tier: String, Sendable, CaseIterable {
    case standard
    case silver
    case gold

    private static let silverFromCents = 10_000
    private static let goldFromCents = 50_000

    public var percentOff: Int {
        switch self {
        case .standard: 0
        case .silver: 5
        case .gold: 10
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
