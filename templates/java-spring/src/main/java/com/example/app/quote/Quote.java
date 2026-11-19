package com.example.app.quote;

import java.util.List;

public record Quote(Money subtotal, Tier tier, Money total) {
  public static Quote of(List<String> lines) {
    Money subtotal = lines.stream().map(Money::parse).reduce(Money.ZERO, Money::plus);
    Tier tier = Tier.forSubtotal(subtotal);
    return new Quote(subtotal, tier, subtotal.lessPercent(tier.percentOff()));
  }
}
