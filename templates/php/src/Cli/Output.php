<?php

declare(strict_types=1);

namespace App\Cli;

interface Output
{
    public function line(string $text): void;
}
