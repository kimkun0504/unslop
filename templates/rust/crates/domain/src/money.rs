use std::fmt;

const CENTS_PER_UNIT: u64 = 100;
const WHOLE_PERCENT: u64 = 100;
const MAX_UNIT_DIGITS: usize = 12;
const CENT_DIGITS: usize = 2;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct Money {
    cents: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InvalidAmount {
    raw: String,
}

impl fmt::Display for InvalidAmount {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "expected a non-negative amount like 12 or 12.50, got \"{}\"",
            self.raw
        )
    }
}

impl std::error::Error for InvalidAmount {}

fn is_canonical_units(units: &str) -> bool {
    let digits_only = !units.is_empty() && units.bytes().all(|byte| byte.is_ascii_digit());
    let no_leading_zero = units == "0" || !units.starts_with('0');
    digits_only && no_leading_zero && units.len() <= MAX_UNIT_DIGITS
}

fn is_canonical_cents(cents: &str) -> bool {
    cents.len() == CENT_DIGITS && cents.bytes().all(|byte| byte.is_ascii_digit())
}

impl Money {
    pub const ZERO: Self = Self { cents: 0 };

    pub fn parse(raw: &str) -> Result<Self, InvalidAmount> {
        let trimmed = raw.trim();
        let (units, cents) = trimmed.split_once('.').unwrap_or((trimmed, "00"));
        if !is_canonical_units(units) || !is_canonical_cents(cents) {
            return Err(InvalidAmount {
                raw: raw.to_owned(),
            });
        }
        let whole: u64 = units.parse().unwrap_or_default();
        let fraction: u64 = cents.parse().unwrap_or_default();
        Ok(Self {
            cents: whole
                .saturating_mul(CENTS_PER_UNIT)
                .saturating_add(fraction),
        })
    }

    #[must_use]
    pub const fn cents(self) -> u64 {
        self.cents
    }

    #[must_use]
    pub const fn saturating_add(self, other: Self) -> Self {
        Self {
            cents: self.cents.saturating_add(other.cents),
        }
    }

    #[must_use]
    pub const fn less_percent(self, percent: u64) -> Self {
        let kept = WHOLE_PERCENT.saturating_sub(percent);
        Self {
            cents: self.cents.saturating_mul(kept) / WHOLE_PERCENT,
        }
    }
}

impl fmt::Display for Money {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{}.{:02}",
            self.cents / CENTS_PER_UNIT,
            self.cents % CENTS_PER_UNIT
        )
    }
}

#[cfg(test)]
mod tests {
    use super::{InvalidAmount, Money};
    use proptest::prelude::{ProptestConfig, prop_assert, prop_assert_eq, proptest};

    const MAX_CENTS: u64 = 99_999_999_999_999;

    #[test]
    fn parses_canonical_amounts() {
        let parsed: Vec<_> = ["0", "12", "12.50", " 7.05 "]
            .into_iter()
            .map(|raw| Money::parse(raw).map(Money::cents))
            .collect();
        assert_eq!(parsed, vec![Ok(0), Ok(1200), Ok(1250), Ok(705)]);
    }

    #[test]
    fn rejects_malformed_amounts_with_the_input_in_the_message() {
        for raw in [
            "",
            "-1",
            "1.5",
            "01",
            "1.005",
            "abc",
            "1,00",
            ".50",
            "1.",
            "1234567890123",
        ] {
            let message = Money::parse(raw).map_err(|error| error.to_string());
            assert_eq!(
                message,
                Err(format!(
                    "expected a non-negative amount like 12 or 12.50, got \"{raw}\""
                )),
                "{raw}"
            );
        }
    }

    #[test]
    fn errors_are_comparable() {
        assert_eq!(
            Money::parse("x"),
            Err(InvalidAmount {
                raw: "x".to_owned()
            })
        );
    }

    #[test]
    fn adds_discounts_and_saturates() {
        let ten = Money::parse("10").unwrap_or(Money::ZERO);
        let five = Money::parse("5").unwrap_or(Money::ZERO);
        assert_eq!(ten.saturating_add(five).to_string(), "15.00");
        assert_eq!(ten.less_percent(5).to_string(), "9.50");
        assert_eq!(ten.less_percent(150).to_string(), "0.00");
        let max = Money { cents: u64::MAX };
        assert_eq!(max.saturating_add(ten).cents(), u64::MAX);
    }

    proptest! {
        #![proptest_config(ProptestConfig::with_cases(512))]

        #[test]
        fn render_then_parse_round_trips(cents in 0..=MAX_CENTS) {
            let money = Money { cents };
            prop_assert_eq!(Money::parse(&money.to_string()), Ok(money));
        }

        #[test]
        fn discounts_stay_in_range(cents in 0..=MAX_CENTS, percent in 0..=100_u64) {
            let discounted = Money { cents }.less_percent(percent).cents();
            prop_assert!(discounted <= cents);
        }
    }
}
