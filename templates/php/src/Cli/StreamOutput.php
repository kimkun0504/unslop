<?php

declare(strict_types=1);

namespace App\Cli;

use SplFileObject;

final readonly class StreamOutput implements Output
{
    public function __construct(private SplFileObject $file)
    {
    }

    public function line(string $text): void
    {
        $this->file->fwrite($text . PHP_EOL);
    }
}
