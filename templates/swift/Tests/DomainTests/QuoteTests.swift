import Domain
import Testing

struct QuoteTests {
    @Test(arguments: [
        ([String](), "0.00 standard 0.00"),
        (["99.99"], "99.99 standard 99.99"),
        (["60", "40"], "100.00 silver 95.00"),
        (["499.99"], "499.99 silver 474.99"),
        (["500"], "500.00 gold 450.00"),
    ])
    func quotes(lines: [String], expected: String) throws {
        let quote = try Quote.of(lines)
        #expect("\(quote.subtotal.rendered) \(quote.tier.rawValue) \(quote.total.rendered)" == expected)
    }

    @Test func reportsTheFirstMalformedLine() {
        #expect(throws: InvalidAmount(raw: "x")) { try Quote.of(["1", "x", "y"]) }
    }
}
