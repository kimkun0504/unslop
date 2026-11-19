<?php

declare(strict_types=1);

namespace App\Domain;

final readonly class Money
{
    private const int CENTS_PER_UNIT = 100;
    private const int WHOLE_PERCENT = 100;
    private const string CANONICAL = '/^(0|[1-9][0-9]{0,11})\.[0-9]{2}$/D';

    private function __construct(public int $cents) {}

    public static function zero(): self
    {
        return new self(0);
    }

    public static function parse(string $raw): self
    {
        $trimmed = trim($raw);
        $canonical = str_contains($trimmed, '.') ? $trimmed : $trimmed . '.00';
        if (preg_match(self::CANONICAL, $canonical) !== 1) {
            throw InvalidAmount::from($raw);
        }

        return new self((int) str_replace('.', '', $canonical));
    }

    public function plus(self $other): self
    {
        return new self($this->cents + $other->cents);
    }

    public function lessPercent(int $percent): self
    {
        return new self(intdiv($this->cents * (self::WHOLE_PERCENT - $percent), self::WHOLE_PERCENT));
    }

    public function render(): string
    {
        return sprintf('%d.%02d', intdiv($this->cents, self::CENTS_PER_UNIT), $this->cents % self::CENTS_PER_UNIT);
    }
}
