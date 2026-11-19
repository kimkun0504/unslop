use std::io;
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let code = app::run(&args, &mut io::stdout().lock(), &mut io::stderr().lock());
    code.map_or(ExitCode::FAILURE, ExitCode::from)
}
