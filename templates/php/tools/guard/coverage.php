<?php

declare(strict_types=1);

$report = simplexml_load_file($argv[1] ?? 'build/coverage.xml');
if ($report === false) {
    fwrite(STDERR, "coverage: report not found\n");
    exit(1);
}

$metrics = $report->project->metrics;
$pairs = ['statements' => 'coveredstatements', 'methods' => 'coveredmethods', 'conditionals' => 'coveredconditionals'];
foreach ($pairs as $total => $covered) {
    $all = (int) $metrics[$total];
    $hit = (int) $metrics[$covered];
    if ($hit !== $all) {
        fwrite(STDERR, sprintf("coverage: %s %d of %d covered; 100%% required\n", $total, $hit, $all));
        exit(1);
    }
}

fwrite(STDOUT, "coverage: 100% of statements, methods and conditionals\n");
