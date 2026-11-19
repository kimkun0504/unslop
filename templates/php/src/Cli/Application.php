<?php

declare(strict_types=1);

namespace App\Cli;

use App\Domain\InvalidAmount;
use App\Domain\Quote;

final readonly class Application
{
    public const int EXIT_OK = 0;
    public const int EXIT_USAGE = 2;

    public function __construct(private Output $out, private Output $err)
    {
    }

    public function run(string ...$arguments): int
    {
        if ($arguments === []) {
            $this->err->line('usage: app AMOUNT [AMOUNT ...]');

            return self::EXIT_USAGE;
        }

        try {
            $quote = Quote::of(...$arguments);
        } catch (InvalidAmount $error) {
            $this->err->line($error->getMessage());

            return self::EXIT_USAGE;
        }

        $this->out->line(sprintf(
            'subtotal=%s tier=%s total=%s',
            $quote->subtotal->render(),
            $quote->tier->value,
            $quote->total->render(),
        ));

        return self::EXIT_OK;
    }
}
