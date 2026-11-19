build_legacy() {
  mkdir -p src/main/kotlin/legacy src/test/kotlin/legacy
  printf 'rootProject.name = "legacy"\n' > settings.gradle.kts
  cat > build.gradle.kts <<'KTS'
plugins {
    kotlin("jvm") version "2.4.21"
}

repositories {
    mavenCentral()
}

dependencies {
    testImplementation(kotlin("test"))
}

kotlin {
    jvmToolchain(21)
}

tasks.test {
    useJUnitPlatform()
}
KTS
  printf 'package legacy\n\n// legacy\nfun add(a: Int, b: Int): Int {\n    println("adding")\n    return a + b\n}\n' > src/main/kotlin/legacy/Calc.kt
  printf 'package legacy\n\nimport kotlin.test.Test\nimport kotlin.test.assertEquals\n\nclass CalcTest {\n    @Test\n    fun adds() {\n        assertEquals(3, add(1, 2))\n    }\n}\n' > src/test/kotlin/legacy/CalcTest.kt
  printf 'build/\n.gradle/\n.kotlin/\n' > .gitignore
}
cases() {
  printf 'package legacy\n\nfun mul(a: Int, b: Int): Int = a * b // product\n' > src/main/kotlin/legacy/Mul.kt
  expect_fail "comment" "comments are forbidden"
  printf 'package legacy\n\nfun shout(word: String) {\n    println(word)\n}\n' > src/main/kotlin/legacy/Shout.kt
  printf 'package legacy\n\nimport kotlin.test.Test\n\nclass ShoutTest {\n    @Test\n    fun shouts() {\n        shout("a")\n    }\n}\n' > src/test/kotlin/legacy/ShoutTest.kt
  expect_fail "println in new code" "println() is forbidden"
  printf 'package legacy\n\nfun area(): Int = 42 * 7\n' > src/main/kotlin/legacy/Area.kt
  printf 'package legacy\n\nimport kotlin.test.Test\nimport kotlin.test.assertEquals\n\nclass AreaTest {\n    @Test\n    fun area() {\n        assertEquals(294, area())\n    }\n}\n' > src/test/kotlin/legacy/AreaTest.kt
  expect_fail "new detekt finding" "MagicNumber"
  printf 'package legacy\n\nfun twice(value: Int): Int = value * 2\n' > src/main/kotlin/legacy/Twice.kt
  expect_fail "untested new code" "every changed line must be covered"
  printf 'package legacy\n\nimport kotlin.test.Ignore\nimport kotlin.test.Test\n\nclass LaterTest {\n    @Ignore\n    @Test\n    fun later() {\n    }\n}\n' > src/test/kotlin/legacy/LaterTest.kt
  expect_fail "ignored test" "check-diff"
  printf 'package legacy\n\nfun twice(value: Int): Int = value * 2\n' > src/main/kotlin/legacy/Twice.kt
  printf 'package legacy\n\nimport kotlin.test.Test\nimport kotlin.test.assertEquals\n\nclass TwiceTest {\n    @Test\n    fun doubles() {\n        assertEquals(4, twice(2))\n    }\n}\n' > src/test/kotlin/legacy/TwiceTest.kt
  expect_pass "clean, tested new code"
}
