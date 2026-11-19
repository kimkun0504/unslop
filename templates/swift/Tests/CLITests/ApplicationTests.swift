import CLI
import Testing

final class RecordingOutput: Output {
    private(set) var lines: [String] = []

    func line(_ text: String) {
        lines.append(text)
    }
}

struct ApplicationTests {
    private func call(_ arguments: [String]) -> (Int32, [String], [String]) {
        let out = RecordingOutput()
        let err = RecordingOutput()
        let code = Application(out: out, err: err).run(arguments)
        return (code, out.lines, err.lines)
    }

    @Test func printsTheQuote() {
        let (code, out, err) = call(["60", "40"])
        #expect(code == Application.exitOK)
        #expect(out == ["subtotal=100.00 tier=silver total=95.00"])
        #expect(err.isEmpty)
    }

    @Test func rejectsMissingAmounts() {
        let (code, out, err) = call([])
        #expect(code == Application.exitUsage)
        #expect(out.isEmpty)
        #expect(err == ["usage: app AMOUNT [AMOUNT ...]"])
    }

    @Test func rejectsMalformedAmounts() {
        let (code, out, err) = call(["1.5"])
        #expect(code == Application.exitUsage)
        #expect(out.isEmpty)
        #expect(err == ["expected a non-negative amount like 12 or 12.50, got \"1.5\""])
    }
}
