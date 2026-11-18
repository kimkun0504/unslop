package com.example.app.quote

import org.junit.jupiter.api.Test
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.CsvSource
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class PricingTest {
    @ParameterizedTest
    @CsvSource(
        "'', 0.00 STANDARD 0.00",
        "99.99, 99.99 STANDARD 99.99",
        "60;40, 100.00 SILVER 95.00",
        "499.99, 499.99 SILVER 474.99",
        "500, 500.00 GOLD 450.00",
    )
    fun `applies the tier for the subtotal`(
        lines: String,
        expected: String,
    ) {
        val quote = Quote.of(lines.split(';').filter(String::isNotEmpty))
        assertEquals(expected, "${quote.subtotal} ${quote.tier} ${quote.total}")
    }

    @Test
    fun `reports the first malformed line`() {
        val error = assertFailsWith<InvalidAmountException> { Quote.of(listOf("1", "x", "y")) }
        assertEquals("expected a non-negative amount like 12 or 12.50, got \"x\"", error.message)
    }
}
