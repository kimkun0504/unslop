<?php

declare(strict_types=1);

namespace App\Tests\Domain;

use App\Domain\InvalidAmount;
use App\Domain\Quote;
use PHPUnit\Framework\Attributes\TestWith;
use PHPUnit\Framework\TestCase;

final class QuoteTest extends TestCase
{
    #[TestWith(['', '0.00 standard 0.00'])]
    #[TestWith(['99.99', '99.99 standard 99.99'])]
    #[TestWith(['60;40', '100.00 silver 95.00'])]
    #[TestWith(['499.99', '499.99 silver 474.99'])]
    #[TestWith(['500', '500.00 gold 450.00'])]
    public function testAppliesTheTierForTheSubtotal(string $lines, string $expected): void
    {
        $quote = Quote::of(...array_values(array_filter(explode(';', $lines), static fn(string $line): bool => $line !== '')));
        self::assertSame($expected, sprintf('%s %s %s', $quote->subtotal->render(), $quote->tier->value, $quote->total->render()));
    }

    public function testReportsTheFirstMalformedLine(): void
    {
        $this->expectException(InvalidAmount::class);
        $this->expectExceptionMessage('expected a non-negative amount like 12 or 12.50, got "x"');
        Quote::of('1', 'x', 'y');
    }
}
