import { describe, expect, it } from "vitest";
import { quote } from "./pricing";

function summary(lines: readonly string[]): string {
  const result = quote(lines);
  return result.ok
    ? `${result.value.subtotal.render()} ${result.value.tier} ${result.value.total.render()}`
    : result.error;
}

describe("quote", () => {
  it.each([
    [[], "0.00 standard 0.00"],
    [["99.99"], "99.99 standard 99.99"],
    [["60", "40"], "100.00 silver 95.00"],
    [["499.99"], "499.99 silver 474.99"],
    [["500"], "500.00 gold 450.00"],
  ])("prices %j", (lines, expected) => {
    expect(summary(lines)).toBe(expected);
  });

  it("reports the first malformed line", () => {
    expect(summary(["1", "x", "y"])).toBe('expected a non-negative amount like 12 or 12.50, got "x"');
  });
});
