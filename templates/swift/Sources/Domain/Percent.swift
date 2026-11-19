public struct Percent: Equatable, Sendable {
    public static let whole = Self(trusted: 100)

    public let value: Int

    init(trusted value: Int) {
        self.value = value
    }

    public init?(_ value: Int) {
        guard (0...Self.whole.value).contains(value) else {
            return nil
        }
        self.init(trusted: value)
    }
}
