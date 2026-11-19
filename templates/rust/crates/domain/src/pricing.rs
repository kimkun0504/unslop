use std::fmt;

use crate::money::{InvalidAmount, Money};

const SILVER_FROM_CENTS: u64 = 10_000;
const GOLD_FROM_CENTS: u64 = 50_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tier {
    Standard,
    Silver,
    Gold,
}

impl Tier {
    #[must_use]
    pub const fn for_subtotal(subtotal: Money) -> Self {
        if subtotal.cents() >= GOLD_FROM_CENTS {
            Self::Gold
        } else if subtotal.cents() >= SILVER_FROM_CENTS {
            Self::Silver
        } else {
            Self::Standard
        }
    }

    #[must_use]
    pub const fn percent_off(self) -> u64 {
        match self {
            Self::Standard => 0,
            Self::Silver => 5,
            Self::Gold => 10,
        }
    }
}

impl fmt::Display for Tier {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::Standard => "standard",
            Self::Silver => "silver",
            Self::Gold => "gold",
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Quote {
    pub subtotal: Money,
    pub tier: Tier,
    pub total: Money,
}

pub fn quote<'a>(lines: impl IntoIterator<Item = &'a str>) -> Result<Quote, InvalidAmount> {
    let subtotal = lines
        .into_iter()
        .map(Money::parse)
        .try_fold(Money::ZERO, |sum, amount| {
            amount.map(|value| sum.saturating_add(value))
        })?;
    let tier = Tier::for_subtotal(subtotal);
    Ok(Quote {
        subtotal,
        tier,
        total: subtotal.less_percent(tier.percent_off()),
    })
}

#[cfg(test)]
mod tests {
    use super::quote;

    fn summary(lines: &[&str]) -> String {
        quote(lines.iter().copied()).map_or_else(
            |error| error.to_string(),
            |result| format!("{} {} {}", result.subtotal, result.tier, result.total),
        )
    }

    #[test]
    fn applies_the_tier_for_the_subtotal() {
        let cases: [(&[&str], &str); 5] = [
            (&[], "0.00 standard 0.00"),
            (&["99.99"], "99.99 standard 99.99"),
            (&["60", "40"], "100.00 silver 95.00"),
            (&["499.99"], "499.99 silver 474.99"),
            (&["500"], "500.00 gold 450.00"),
        ];
        for (lines, expected) in cases {
            assert_eq!(summary(lines), expected);
        }
    }

    #[test]
    fn reports_the_first_malformed_line() {
        assert_eq!(
            summary(&["1", "x", "y"]),
            "expected a non-negative amount like 12 or 12.50, got \"x\""
        );
    }
}
