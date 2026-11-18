package com.example.app.quote

enum class Tier(
    val percentOff: Long,
) {
    STANDARD(0),
    SILVER(5),
    GOLD(10),
    ;

    companion object {
        private const val SILVER_FROM_CENTS = 10_000L
        private const val GOLD_FROM_CENTS = 50_000L

        fun forSubtotal(subtotal: Money): Tier =
            when {
                subtotal.cents >= GOLD_FROM_CENTS -> GOLD
                subtotal.cents >= SILVER_FROM_CENTS -> SILVER
                else -> STANDARD
            }
    }
}

data class Quote(
    val subtotal: Money,
    val tier: Tier,
    val total: Money,
) {
    companion object {
        fun of(lines: List<String>): Quote {
            val subtotal = lines.map(Money::parse).fold(Money.ZERO, Money::plus)
            val tier = Tier.forSubtotal(subtotal)
            return Quote(subtotal, tier, subtotal.lessPercent(tier.percentOff))
        }
    }
}
