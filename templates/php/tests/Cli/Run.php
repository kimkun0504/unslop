<?php

declare(strict_types=1);

namespace App\Tests\Cli;

final readonly class Run
{
    public function __construct(public int $code, public string $out, public string $err)
    {
    }
}
