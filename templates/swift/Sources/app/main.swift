import CLI
import Foundation

struct StreamOutput: Output {
    let handle: FileHandle

    func line(_ text: String) {
        handle.write(Data((text + "\n").utf8))
    }
}

let application = Application(
    out: StreamOutput(handle: .standardOutput),
    err: StreamOutput(handle: .standardError)
)

exit(application.run(Array(CommandLine.arguments.dropFirst())))
