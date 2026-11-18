package com.example.app.quote

@JvmInline
value class Money private constructor(
    val cents: Long,
) {
    operator fun plus(other: Money): Money = Money(cents + other.cents)

    fun lessPercent(percent: Long): Money = Money(cents * (WHOLE_PERCENT - percent) / WHOLE_PERCENT)

    override fun toString(): String = "${cents / CENTS_PER_UNIT}.${(cents % CENTS_PER_UNIT).toString().padStart(2, '0')}"

    companion object {
        private const val CENTS_PER_UNIT = 100
        private const val WHOLE_PERCENT = 100
        private val canonicalAmount = Regex("""(0|[1-9][0-9]{0,11})\.[0-9]{2}""")

        val ZERO = Money(0)

        fun parse(raw: String): Money {
            val trimmed = raw.trim()
            val canonical = if ('.' in trimmed) trimmed else "$trimmed.00"
            if (!canonicalAmount.matches(canonical)) {
                throw InvalidAmountException(raw)
            }
            return Money(canonical.replace(".", "").toLong())
        }
    }
}

class InvalidAmountException(
    raw: String,
) : IllegalArgumentException("expected a non-negative amount like 12 or 12.50, got \"$raw\"")
