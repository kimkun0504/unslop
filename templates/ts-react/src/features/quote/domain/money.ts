import { accept, reject, type Parsed } from "./parsed";

const canonicalAmount = /^(0|[1-9]\d{0,11})\.\d{2}$/;
const centsPerUnit = 100;

export class Money {
  static readonly zero = new Money(0);

  private constructor(readonly cents: number) {}

  static fromCents(cents: number): Parsed<Money> {
    return Number.isSafeInteger(cents) && cents >= 0
      ? accept(new Money(cents))
      : reject(`expected a non-negative whole number of cents, got ${String(cents)}`);
  }

  static parse(raw: string): Parsed<Money> {
    const trimmed = raw.trim();
    const canonical = trimmed.includes(".") ? trimmed : `${trimmed}.00`;
    return canonicalAmount.test(canonical)
      ? Money.fromCents(Number(canonical.replace(".", "")))
      : reject(`expected a non-negative amount like 12 or 12.50, got "${raw}"`);
  }

  plus(other: Money): Money {
    return new Money(this.cents + other.cents);
  }

  lessPercent(percent: number): Money {
    return new Money(Math.floor((this.cents * (100 - percent)) / 100));
  }

  atLeast(other: Money): boolean {
    return this.cents >= other.cents;
  }

  render(): string {
    const units = Math.floor(this.cents / centsPerUnit);
    const cents = this.cents % centsPerUnit;
    return `${String(units)}.${String(cents).padStart(2, "0")}`;
  }
}
