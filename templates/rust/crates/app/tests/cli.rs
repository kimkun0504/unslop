use std::process::Command;

#[test]
fn binary_prints_the_quote_and_exits_cleanly() {
    let output = Command::new(env!("CARGO_BIN_EXE_app"))
        .args(["500"])
        .output();
    let (code, stdout) = output.map_or((None, String::new()), |result| {
        (
            result.status.code(),
            String::from_utf8_lossy(&result.stdout).into_owned(),
        )
    });
    assert_eq!(
        (code, stdout.as_str()),
        (Some(0), "subtotal=500.00 tier=gold total=450.00\n")
    );
}

#[test]
fn binary_reports_usage_errors() {
    let output = Command::new(env!("CARGO_BIN_EXE_app")).output();
    let code = output.map_or(None, |result| result.status.code());
    assert_eq!(code, Some(2));
}
