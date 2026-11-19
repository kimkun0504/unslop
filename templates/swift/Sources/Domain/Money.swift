public struct Money: Equatable, Sendable {
    public static let zero = Self(validCents: 0)

    private static let centsPerUnit = 100
    private static let wholePercent = 100

    public let cents: Int

    private init(validCents: Int) {
        cents = validCents
    }

    public init?(cents: Int) {
        guard cents >= 0 else {
            return nil
        }
        self.init(validCents: cents)
    }

    public static func parse(_ raw: String) throws(InvalidAmount) -> Self {
        let trimmed = String(raw.drop { $0.isWhitespace }.reversed().drop { $0.isWhitespace }.reversed())
        let canonical = trimmed.contains(".") ? trimmed : trimmed + ".00"
        guard canonical.wholeMatch(of: /(?:0|[1-9][0-9]{0,11})\.[0-9]{2}/) != nil,
            let cents = Int(canonical.filter { $0 != "." })
        else {
            throw InvalidAmount(raw: raw)
        }
        return Self(validCents: cents)
    }

    public func plus(_ other: Self) -> Self {
        Self(validCents: cents + other.cents)
    }

    public func lessPercent(_ percent: Int) -> Self {
        precondition((0...Self.wholePercent).contains(percent), "percent must be between 0 and 100")
        return Self(validCents: cents * (Self.wholePercent - percent) / Self.wholePercent)
    }

    public var rendered: String {
        let rest = cents % Self.centsPerUnit
        return "\(cents / Self.centsPerUnit).\(rest < 10 ? "0" : "")\(rest)"
    }
}
