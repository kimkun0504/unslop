package com.example.app.quote;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

class MoneyTest {
  @ParameterizedTest
  @CsvSource({"0,0", "12,1200", "12.50,1250", "' 7.05 ',705"})
  void parsesCanonicalAmounts(String raw, long cents) {
    assertThat(Money.parse(raw).cents()).isEqualTo(cents);
  }

  @ParameterizedTest
  @ValueSource(strings = {"", "-1", "1.5", "01", "1.005", "abc", "1,00"})
  void rejectsMalformedAmountsWithTheInputInTheMessage(String raw) {
    assertThatThrownBy(() -> Money.parse(raw))
        .isInstanceOf(InvalidAmountException.class)
        .hasMessage("expected a non-negative amount like 12 or 12.50, got \"%s\"", raw);
  }

  @Test
  void rendersCentsWithTwoDigits() {
    assertThat(List.of("0.05", "10.50", "0").stream().map(raw -> Money.parse(raw).toString()))
        .containsExactly("0.05", "10.50", "0.00");
  }

  @Test
  void addsAndDiscounts() {
    Money ten = Money.parse("10");
    assertThat(List.of(ten.plus(Money.parse("5")).toString(), ten.lessPercent(5).toString()))
        .containsExactly("15.00", "9.50");
  }
}
