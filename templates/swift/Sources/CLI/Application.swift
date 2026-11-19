internal import Domain

public struct Application {
    public static let exitOK: Int32 = 0
    public static let exitUsage: Int32 = 2

    private static let usage = "usage: app AMOUNT [AMOUNT ...]"

    private let out: any Output
    private let err: any Output

    public init(out: any Output, err: any Output) {
        self.out = out
        self.err = err
    }

    public func run(_ arguments: [String]) -> Int32 {
        guard !arguments.isEmpty else {
            return refuse(Self.usage)
        }
        do throws(InvalidAmount) {
            let quote = try Quote.of(arguments)
            out.line("subtotal=\(quote.subtotal.rendered) tier=\(quote.tier.rawValue) total=\(quote.total.rendered)")
            return Self.exitOK
        } catch {
            return refuse(error.description)
        }
    }

    private func refuse(_ message: String) -> Int32 {
        err.line(message)
        return Self.exitUsage
    }
}
