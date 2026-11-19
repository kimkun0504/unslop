use std::io::{self, Write};

pub const EXIT_OK: u8 = 0;
pub const EXIT_USAGE: u8 = 2;

pub fn run(args: &[String], out: &mut impl Write, err: &mut impl Write) -> io::Result<u8> {
    if args.is_empty() {
        writeln!(err, "usage: app AMOUNT [AMOUNT ...]")?;
        return Ok(EXIT_USAGE);
    }
    match domain::quote(args.iter().map(String::as_str)) {
        Ok(result) => {
            let line = format!("subtotal={} tier={}", result.subtotal, result.tier);
            writeln!(out, "{line} total={}", result.total)?;
            Ok(EXIT_OK)
        }
        Err(error) => {
            writeln!(err, "{error}")?;
            Ok(EXIT_USAGE)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{EXIT_OK, EXIT_USAGE, run};

    fn call(args: &[&str]) -> (u8, String, String) {
        let owned: Vec<String> = args.iter().map(|arg| (*arg).to_owned()).collect();
        let mut out = Vec::new();
        let mut err = Vec::new();
        let code = run(&owned, &mut out, &mut err).unwrap_or(u8::MAX);
        (
            code,
            String::from_utf8_lossy(&out).into_owned(),
            String::from_utf8_lossy(&err).into_owned(),
        )
    }

    #[test]
    fn prints_the_quote() {
        assert_eq!(
            call(&["60", "40"]),
            (
                EXIT_OK,
                "subtotal=100.00 tier=silver total=95.00\n".to_owned(),
                String::new()
            )
        );
    }

    #[test]
    fn rejects_missing_amounts() {
        assert_eq!(
            call(&[]),
            (
                EXIT_USAGE,
                String::new(),
                "usage: app AMOUNT [AMOUNT ...]\n".to_owned()
            )
        );
    }

    #[test]
    fn rejects_malformed_amounts() {
        assert_eq!(
            call(&["1.5"]),
            (
                EXIT_USAGE,
                String::new(),
                "expected a non-negative amount like 12 or 12.50, got \"1.5\"\n".to_owned()
            )
        );
    }
}
