public struct InvalidAmount: Error, Equatable, Sendable, CustomStringConvertible {
    public let raw: String

    public var description: String {
        "expected a non-negative amount like 12 or 12.50, got \"\(raw)\""
    }

    public init(raw: String) {
        self.raw = raw
    }
}
