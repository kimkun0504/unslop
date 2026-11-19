<?php

declare(strict_types=1);

function fail(string $message): never
{
    fwrite(STDERR, 'coverage: ' . $message . PHP_EOL);
    exit(1);
}

$serverArguments = $_SERVER['argv'] ?? [];
$path = is_array($serverArguments) && is_string($serverArguments[1] ?? null) ? $serverArguments[1] : 'build/coverage.xml';

$document = new DOMDocument();
if (!is_file($path) || !$document->load($path)) {
    fail('report not found at ' . $path);
}

$nodes = new DOMXPath($document)->query('/coverage/project/metrics');
$metrics = $nodes === false ? null : $nodes->item(0);
if (!$metrics instanceof DOMElement) {
    fail('report has no project metrics');
}

$pairs = ['statements' => 'coveredstatements', 'methods' => 'coveredmethods', 'conditionals' => 'coveredconditionals'];
foreach ($pairs as $total => $covered) {
    $all = (int) $metrics->getAttribute($total);
    $hit = (int) $metrics->getAttribute($covered);
    if ($hit !== $all) {
        fail(sprintf('%s %d of %d covered; 100%% required', $total, $hit, $all));
    }
}

fwrite(STDOUT, 'coverage: 100% of statements, methods and conditionals' . PHP_EOL);
