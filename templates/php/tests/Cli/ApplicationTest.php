<?php

declare(strict_types=1);

namespace App\Tests\Cli;

use App\Cli\Application;
use App\Cli\StreamOutput;
use PHPUnit\Framework\TestCase;
use SplFileObject;
use SplTempFileObject;

final class ApplicationTest extends TestCase
{
    private static function contents(SplFileObject $file): string
    {
        $file->rewind();
        $text = '';
        while (!$file->eof()) {
            $text .= $file->fgets();
        }

        return $text;
    }

    private function call(string ...$arguments): Run
    {
        $out = new SplTempFileObject();
        $err = new SplTempFileObject();
        $code = new Application(new StreamOutput($out), new StreamOutput($err))->run(...$arguments);

        return new Run($code, self::contents($out), self::contents($err));
    }

    public function testPrintsTheQuote(): void
    {
        self::assertEquals(new Run(Application::EXIT_OK, "subtotal=100.00 tier=silver total=95.00\n", ''), $this->call('60', '40'));
    }

    public function testRejectsMissingAmounts(): void
    {
        self::assertEquals(new Run(Application::EXIT_USAGE, '', "usage: app AMOUNT [AMOUNT ...]\n"), $this->call());
    }

    public function testRejectsMalformedAmounts(): void
    {
        self::assertEquals(
            new Run(Application::EXIT_USAGE, '', "expected a non-negative amount like 12 or 12.50, got \"1.5\"\n"),
            $this->call('1.5'),
        );
    }

    public function testTheBinaryWiresStandardStreams(): void
    {
        $output = [];
        $code = 1;
        exec(sprintf('%s %s 500', escapeshellarg(PHP_BINARY), escapeshellarg(dirname(__DIR__, 2) . '/bin/app')), $output, $code);
        self::assertSame([0, ['subtotal=500.00 tier=gold total=450.00']], [$code, $output]);
    }
}
