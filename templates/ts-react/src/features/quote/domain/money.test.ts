import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { Money } from "./money";

const maxCents = 10 ** 13;

function cents(raw: string): number | string {
  const parsed = Money.parse(raw);
  return parsed.ok ? parsed.value.cents : parsed.error;
}

describe("Money.parse", () => {
  it.each([
    ["0", 0],
    ["12", 1200],
    ["12.50", 1250],
    [" 7.05 ", 705],
  ])("accepts %s", (raw, expected) => {
    expect(cents(raw)).toBe(expected);
  });

  it.each(["", "-1", "1.5", "01", "1.005", "abc", "1,00"])("rejects %j with the input in the message", (raw) => {
    expect(cents(raw)).toBe(`expected a non-negative amount like 12 or 12.50, got "${raw}"`);
  });

  it("round-trips through render", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: maxCents }), (value) => {
        const parsed = Money.fromCents(value);
        expect(parsed.ok && cents(parsed.value.render())).toBe(value);
      }),
    );
  });
});

describe("Money.fromCents", () => {
  it.each([-1, 0.5, Number.MAX_SAFE_INTEGER + 1])("rejects %d", (value) => {
    expect(Money.fromCents(value)).toEqual({
      ok: false,
      error: `expected a non-negative whole number of cents, got ${String(value)}`,
    });
  });
});

describe("Money arithmetic", () => {
  it("never discounts below zero or above the original", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: maxCents }), fc.integer({ min: 0, max: 100 }), (value, percent) => {
        const parsed = Money.fromCents(value);
        const discounted = parsed.ok ? parsed.value.lessPercent(percent).cents : -1;
        expect(discounted >= 0 && discounted <= value).toBe(true);
      }),
    );
  });

  it("compares amounts", () => {
    const one = Money.parse("1");
    const two = Money.parse("2");
    expect(
      one.ok && two.ok && [two.value.atLeast(one.value), one.value.atLeast(two.value), one.value.atLeast(one.value)],
    ).toEqual([true, false, true]);
  });
});
