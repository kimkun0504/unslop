package com.example.app.quote;

public enum Tier {
  STANDARD(0),
  SILVER(5),
  GOLD(10);

  private static final long SILVER_FROM_CENTS = 10_000;
  private static final long GOLD_FROM_CENTS = 50_000;

  private final long percentOff;

  Tier(long percentOff) {
    this.percentOff = percentOff;
  }

  public long percentOff() {
    return percentOff;
  }

  public static Tier forSubtotal(Money subtotal) {
    if (subtotal.cents() >= GOLD_FROM_CENTS) {
      return GOLD;
    }
    return subtotal.cents() >= SILVER_FROM_CENTS ? SILVER : STANDARD;
  }
}
