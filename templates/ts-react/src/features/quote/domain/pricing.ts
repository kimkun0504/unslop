import { Money } from "./money";
import { accept, reject, type Parsed } from "./parsed";

type Tier = "standard" | "silver" | "gold";

export interface Quote {
  readonly subtotal: Money;
  readonly tier: Tier;
  readonly total: Money;
}

const silverFrom = 10_000;
const goldFrom = 50_000;

function percentOff(tier: Tier): number {
  switch (tier) {
    case "standard":
      return 0;
    case "silver":
      return 5;
    case "gold":
      return 10;
  }
}

function tierFor(subtotal: Money): Tier {
  if (subtotal.cents >= goldFrom) {
    return "gold";
  }
  return subtotal.cents >= silverFrom ? "silver" : "standard";
}

export function quote(lines: readonly string[]): Parsed<Quote> {
  let subtotal = Money.zero;
  for (const line of lines) {
    const amount = Money.parse(line);
    if (!amount.ok) {
      return reject(amount.error);
    }
    subtotal = subtotal.plus(amount.value);
  }
  const tier = tierFor(subtotal);
  return accept({ subtotal, tier, total: subtotal.lessPercent(percentOff(tier)) });
}
