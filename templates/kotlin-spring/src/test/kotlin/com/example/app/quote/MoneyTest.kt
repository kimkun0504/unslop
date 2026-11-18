package com.example.app.quote

import org.junit.jupiter.api.Test
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.CsvSource
import org.junit.jupiter.params.provider.ValueSource
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class MoneyTest {
    @ParameterizedTest
    @CsvSource("0,0", "12,1200", "12.50,1250", "' 7.05 ',705")
    fun `parses canonical amounts`(
        raw: String,
        cents: Long,
    ) {
        assertEquals(cents, Money.parse(raw).cents)
    }

    @ParameterizedTest
    @ValueSource(strings = ["", "-1", "1.5", "01", "1.005", "abc", "1,00"])
    fun `rejects malformed amounts with the input in the message`(raw: String) {
        val error = assertFailsWith<InvalidAmountException> { Money.parse(raw) }
        assertEquals("expected a non-negative amount like 12 or 12.50, got \"$raw\"", error.message)
    }

    @Test
    fun `renders cents with two digits`() {
        assertEquals(listOf("0.05", "10.50", "0.00"), listOf("0.05", "10.5", "0").map { Money.parse(it).toString() })
    }

    @Test
    fun `adds and discounts`() {
        val ten = Money.parse("10")
        assertEquals(
            listOf("15.00", "9.50"),
            listOf((ten + Money.parse("5")).toString(), ten.lessPercent(5).toString()),
        )
    }
}
