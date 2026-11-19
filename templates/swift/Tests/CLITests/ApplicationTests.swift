import CLI
import Testing

final class RecordingOutput: Output {
    private(set) var lines: [String] = []

    func line(_ text: String) {
        lines.append(text)
    }
}

struct Outcome: Equatable {
    let code: Int32
    let out: [String]
    let err: [String]
}

struct ApplicationTests {
    private func call(_ arguments: [String]) -> Outcome {
        let out = RecordingOutput()
        let err = RecordingOutput()
        let code = Application(out: out, err: err).run(arguments)
        return Outcome(code: code, out: out.lines, err: err.lines)
    }

    @Test
    func printsTheQuote() {
        #expect(call(["60", "40"]) == Outcome(code: 0, out: ["subtotal=100.00 tier=silver total=95.00"], err: []))
    }

    @Test
    func rejectsMissingAmounts() {
        #expect(call([]) == Outcome(code: 2, out: [], err: ["usage: app AMOUNT [AMOUNT ...]"]))
    }

    @Test
    func rejectsMalformedAmounts() {
        let message = "expected a non-negative amount like 12 or 12.50, got \"1.5\""
        #expect(call(["1.5"]) == Outcome(code: 2, out: [], err: [message]))
    }
}
