<?php

declare(strict_types=1);

namespace App\Tests\Domain;

use App\Domain\InvalidAmount;
use App\Domain\Money;
use PHPUnit\Framework\Attributes\TestWith;
use PHPUnit\Framework\TestCase;

final class MoneyTest extends TestCase
{
    #[TestWith(['0', 0])]
    #[TestWith(['12', 1200])]
    #[TestWith(['12.50', 1250])]
    #[TestWith([' 7.05 ', 705])]
    public function testParsesCanonicalAmounts(string $raw, int $cents): void
    {
        self::assertSame($cents, Money::parse($raw)->cents);
    }

    #[TestWith([''])]
    #[TestWith(['-1'])]
    #[TestWith(['1.5'])]
    #[TestWith(['01'])]
    #[TestWith(['1.005'])]
    #[TestWith(['abc'])]
    #[TestWith(['1,00'])]
    #[TestWith(['1.0a'])]
    public function testRejectsMalformedAmountsWithTheInputInTheMessage(string $raw): void
    {
        $this->expectException(InvalidAmount::class);
        $this->expectExceptionMessage(sprintf('expected a non-negative amount like 12 or 12.50, got "%s"', $raw));
        Money::parse($raw);
    }

    public function testRendersCentsWithTwoDigits(): void
    {
        self::assertSame(
            ['0.05', '10.50', '0.00'],
            array_map(static fn(string $raw): string => Money::parse($raw)->render(), ['0.05', '10.50', '0']),
        );
    }

    public function testAddsAndDiscounts(): void
    {
        $ten = Money::parse('10');
        self::assertSame(['15.00', '9.50'], [$ten->plus(Money::parse('5'))->render(), $ten->lessPercent(5)->render()]);
    }
}
