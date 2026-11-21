build_legacy() {
  mkdir -p src/main/java/legacy src/test/java/legacy
  cat > pom.xml <<'XML'
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>example</groupId>
  <artifactId>legacy</artifactId>
  <version>1.0</version>
  <properties>
    <maven.compiler.release>21</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.13.4</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>3.5.4</version>
      </plugin>
    </plugins>
  </build>
</project>
XML
  printf 'package legacy;\n\n/* legacy */\npublic class Calc {\n  public static int add(int a, int b) {\n    int unused = 0;\n    System.out.println("adding");\n    return a + b;\n  }\n}\n' > src/main/java/legacy/Calc.java
  printf 'package legacy;\n\nimport static org.junit.jupiter.api.Assertions.assertEquals;\n\nimport org.junit.jupiter.api.Test;\n\nclass CalcTest {\n  @Test\n  void adds() {\n    assertEquals(3, Calc.add(1, 2));\n  }\n}\n' > src/test/java/legacy/CalcTest.java
  printf 'target/\n' > .gitignore
}
cases() {
  printf 'package legacy;\n\npublic final class Mul {\n  private Mul() {}\n\n  public static int mul(int a, int b) {\n    return a * b; // product\n  }\n}\n' > src/main/java/legacy/Mul.java
  expect_fail "comment" "comments are forbidden"
  printf 'package legacy;\n\npublic final class Waste {\n  private Waste() {}\n\n  public static int value() {\n    System.out.println("value");\n    return 2;\n  }\n}\n' > src/main/java/legacy/Waste.java
  printf 'package legacy;\n\nimport static org.junit.jupiter.api.Assertions.assertEquals;\n\nimport org.junit.jupiter.api.Test;\n\nclass WasteTest {\n  @Test\n  void value() {\n    assertEquals(2, Waste.value());\n  }\n}\n' > src/test/java/legacy/WasteTest.java
  expect_fail "new PMD finding" "SystemPrintln"
  printf 'package legacy;\n\npublic final class Triple {\n  private Triple() {}\n\n  public static int triple(int value) {\n    return value * 3;\n  }\n}\n' > src/main/java/legacy/Triple.java
  expect_fail "untested new code" "of changed lines must be covered"
  printf 'package legacy;\n\nimport org.junit.jupiter.api.Disabled;\nimport org.junit.jupiter.api.Test;\n\nclass LaterTest {\n  @Disabled\n  @Test\n  void later() {}\n}\n' > src/test/java/legacy/LaterTest.java
  expect_fail "disabled test" "new skip or suppression"
  printf 'package legacy;\n\npublic final class Triple {\n  private Triple() {}\n\n  public static int triple(int value) {\n    return value * 3;\n  }\n}\n' > src/main/java/legacy/Triple.java
  printf 'package legacy;\n\nimport static org.junit.jupiter.api.Assertions.assertEquals;\n\nimport org.junit.jupiter.api.Test;\n\nclass TripleTest {\n  @Test\n  void triples() {\n    assertEquals(6, Triple.triple(2));\n  }\n}\n' > src/test/java/legacy/TripleTest.java
  expect_pass "clean, tested new code"
}
