package com.example.app.quote;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class PricingTest {
  @ParameterizedTest
  @CsvSource({
    "'', 0.00 STANDARD 0.00",
    "99.99, 99.99 STANDARD 99.99",
    "60;40, 100.00 SILVER 95.00",
    "499.99, 499.99 SILVER 474.99",
    "500, 500.00 GOLD 450.00"
  })
  void appliesTheTierForTheSubtotal(String lines, String expected) {
    List<String> amounts = Arrays.stream(lines.split(";")).filter(line -> !line.isEmpty()).toList();
    Quote quote = Quote.of(amounts);
    assertThat("%s %s %s".formatted(quote.subtotal(), quote.tier(), quote.total()))
        .isEqualTo(expected);
  }

  @Test
  void reportsTheFirstMalformedLine() {
    assertThatThrownBy(() -> Quote.of(List.of("1", "x", "y")))
        .isInstanceOf(InvalidAmountException.class)
        .hasMessage("expected a non-negative amount like 12 or 12.50, got \"x\"");
  }
}
