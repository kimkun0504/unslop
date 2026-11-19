public struct Money: Equatable, Sendable {
    public static let zero = Self(validCents: 0)

    private static let centsPerUnit = 100

    public let cents: Int

    public var rendered: String {
        let digits = String(cents % Self.centsPerUnit)
        return "\(cents / Self.centsPerUnit).\(digits.count == 1 ? "0" : "")\(digits)"
    }

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
        let trimmed = String(raw.drop(while: \.isWhitespace).reversed().drop(while: \.isWhitespace).reversed())
        let canonical = trimmed.contains(".") ? trimmed : trimmed + ".00"
        guard canonical.wholeMatch(of: /(?:0|[1-9][0-9]{0,11})\.[0-9]{2}/) != nil,
            let value = Int(canonical.filter { $0 != "." })
        else {
            throw InvalidAmount(raw: raw)
        }
        return Self(validCents: value)
    }

    public func plus(_ other: Self) -> Self {
        Self(validCents: cents + other.cents)
    }

    public func less(_ percent: Percent) -> Self {
        let whole = Percent.whole.value
        return Self(validCents: cents * (whole - percent.value) / whole)
    }
}
