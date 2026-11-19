<?php

declare(strict_types=1);

namespace App\Domain;

final readonly class Quote
{
    private function __construct(
        public Money $subtotal,
        public Tier $tier,
        public Money $total,
    ) {
    }

    public static function of(string ...$lines): self
    {
        $subtotal = Money::zero();
        foreach ($lines as $line) {
            $subtotal = $subtotal->plus(Money::parse($line));
        }

        $tier = Tier::forSubtotal($subtotal);

        return new self($subtotal, $tier, $subtotal->lessPercent($tier->percentOff()));
    }
}
