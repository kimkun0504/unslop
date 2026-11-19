<?php

declare(strict_types=1);

namespace App\Domain;

enum Tier: string
{
    case Standard = 'standard';
    case Silver = 'silver';
    case Gold = 'gold';

    private const int SILVER_FROM_CENTS = 10_000;
    private const int GOLD_FROM_CENTS = 50_000;

    public static function forSubtotal(Money $subtotal): self
    {
        return match (true) {
            $subtotal->cents >= self::GOLD_FROM_CENTS => self::Gold,
            $subtotal->cents >= self::SILVER_FROM_CENTS => self::Silver,
            default => self::Standard,
        };
    }

    public function percentOff(): int
    {
        return match ($this) {
            self::Standard => 0,
            self::Silver => 5,
            self::Gold => 10,
        };
    }
}
