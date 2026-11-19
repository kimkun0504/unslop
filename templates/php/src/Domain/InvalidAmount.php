<?php

declare(strict_types=1);

namespace App\Domain;

use InvalidArgumentException;

final class InvalidAmount extends InvalidArgumentException
{
    public static function from(string $raw): self
    {
        return new self(sprintf('expected a non-negative amount like 12 or 12.50, got "%s"', $raw));
    }
}
