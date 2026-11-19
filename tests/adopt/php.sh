build_legacy() {
  mkdir -p src tests
  cat > composer.json <<'JSON'
{
  "name": "example/legacy",
  "autoload": { "psr-4": { "Legacy\\": "src/" } },
  "autoload-dev": { "psr-4": { "Legacy\\Tests\\": "tests/" } },
  "require-dev": { "phpunit/phpunit": "^12.0" }
}
JSON
  printf '<?php\n\nnamespace Legacy;\n\n// legacy\nclass Calc\n{\n    public function add($a, $b) { return $a + $b; }\n}\n' > src/Calc.php
  printf '<?php\n\nnamespace Legacy\\Tests;\n\nuse Legacy\\Calc;\nuse PHPUnit\\Framework\\TestCase;\n\nfinal class CalcTest extends TestCase\n{\n    public function testAdds(): void\n    {\n        self::assertSame(3, (new Calc())->add(1, 2));\n    }\n}\n' > tests/CalcTest.php
  printf 'vendor/\n.phpunit.cache/\n' > .gitignore
  composer update --no-interaction --no-progress --quiet
}
cases() {
  printf '<?php\n\ndeclare(strict_types=1);\n\nnamespace Legacy;\n\nfinal class Mul\n{\n    public static function of(int $a, int $b): int\n    {\n        return $a * $b; // product\n    }\n}\n' > src/Mul.php
  expect_fail "comment" "comments are forbidden"
  printf '<?php\n\ndeclare(strict_types=1);\n\nnamespace Legacy;\n\nfinal class Half\n{\n    public static function of($value)\n    {\n        return $value / 2;\n    }\n}\n' > src/Half.php
  printf '<?php\n\ndeclare(strict_types=1);\n\nnamespace Legacy\\Tests;\n\nuse Legacy\\Half;\nuse PHPUnit\\Framework\\TestCase;\n\nfinal class HalfTest extends TestCase\n{\n    public function testHalves(): void\n    {\n        self::assertSame(2, Half::of(4));\n    }\n}\n' > tests/HalfTest.php
  expect_fail "new PHPStan finding" "missingType"
  printf '<?php\n\ndeclare(strict_types=1);\n\nnamespace Legacy;\n\nfinal class Triple\n{\n    public static function of(int $value): int\n    {\n        return $value * 3;\n    }\n}\n' > src/Triple.php
  expect_fail "untested new code" "every changed line must be covered"
  printf '<?php\n\ndeclare(strict_types=1);\n\nnamespace Legacy\\Tests;\n\nuse PHPUnit\\Framework\\TestCase;\n\nfinal class LaterTest extends TestCase\n{\n    public function testLater(): void\n    {\n        self::markTestSkipped("later");\n    }\n}\n' > tests/LaterTest.php
  expect_fail "skipped test" "check-diff"
  printf '<?php\n\ndeclare(strict_types=1);\n\nnamespace Legacy;\n\nfinal class Twice\n{\n    public static function of(int $value): int\n    {\n        return $value * 2;\n    }\n}\n' > src/Twice.php
  printf '<?php\n\ndeclare(strict_types=1);\n\nnamespace Legacy\\Tests;\n\nuse Legacy\\Twice;\nuse PHPUnit\\Framework\\TestCase;\n\nfinal class TwiceTest extends TestCase\n{\n    public function testDoubles(): void\n    {\n        self::assertSame(4, Twice::of(2));\n    }\n}\n' > tests/TwiceTest.php
  expect_pass "clean, tested new code"
}
