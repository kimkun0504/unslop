package com.example.app.quote;

import java.util.regex.Pattern;

public final class Money {
  public static final Money ZERO = new Money(0);

  private static final Pattern CANONICAL = Pattern.compile("(0|[1-9][0-9]{0,11})\\.[0-9]{2}");
  private static final int CENTS_PER_UNIT = 100;
  private static final int WHOLE_PERCENT = 100;

  private final long cents;

  private Money(long cents) {
    this.cents = cents;
  }

  public static Money parse(String raw) {
    String trimmed = raw.strip();
    String canonical = trimmed.contains(".") ? trimmed : trimmed + ".00";
    if (!CANONICAL.matcher(canonical).matches()) {
      throw new InvalidAmountException(raw);
    }
    return new Money(Long.parseLong(canonical.replace(".", "")));
  }

  public long cents() {
    return cents;
  }

  public Money plus(Money other) {
    return new Money(cents + other.cents);
  }

  public Money lessPercent(long percent) {
    return new Money(cents * (WHOLE_PERCENT - percent) / WHOLE_PERCENT);
  }

  @Override
  public String toString() {
    return "%d.%02d".formatted(cents / CENTS_PER_UNIT, cents % CENTS_PER_UNIT);
  }
}
