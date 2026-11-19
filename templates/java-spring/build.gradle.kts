import net.ltgt.gradle.errorprone.CheckSeverity
import net.ltgt.gradle.errorprone.errorprone
import org.springframework.boot.gradle.plugin.SpringBootPlugin

plugins {
    java
    jacoco
    alias(libs.plugins.spring.boot)
    alias(libs.plugins.errorprone)
    alias(libs.plugins.spotless)
    alias(libs.plugins.pitest)
}

group = "com.example"
version = "0.1.0"

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(25))
    }
}

dependencies {
    implementation(platform(SpringBootPlugin.BOM_COORDINATES))
    implementation(platform(libs.spring.modulith.bom))
    implementation(libs.spring.boot.starter.webmvc)
    implementation(libs.jspecify)
    errorprone(libs.errorprone.core)
    errorprone(libs.nullaway)
    testImplementation(platform(SpringBootPlugin.BOM_COORDINATES))
    testImplementation(platform(libs.spring.modulith.bom))
    testImplementation(libs.spring.boot.starter.test)
    testImplementation(libs.spring.modulith.starter.test)
    testRuntimeOnly(libs.junit.platform.launcher)
}

tasks.withType<JavaCompile>().configureEach {
    options.compilerArgs.addAll(listOf("-Xlint:all,-processing,-serial", "-Werror", "-parameters"))
    options.errorprone {
        disableWarningsInGeneratedCode.set(true)
        error("NullAway")
        error("SystemOut")
        option("NullAway:OnlyNullMarked", "true")
        option("NullAway:JSpecifyMode", "true")
    }
}

tasks.named<JavaCompile>("compileTestJava") {
    options.errorprone {
        check("NullAway", CheckSeverity.OFF)
    }
}

spotless {
    java {
        googleJavaFormat(
            libs.versions.google.java.format
                .get(),
        )
        removeUnusedImports()
        forbidWildcardImports()
    }
    kotlinGradle {
        ktlint()
    }
}

jacoco {
    toolVersion = libs.versions.jacoco.get()
}

tasks.test {
    useJUnitPlatform()
    finalizedBy(tasks.jacocoTestReport)
}

val coverageExclusions = listOf("com/example/app/Application.class")

tasks.jacocoTestReport {
    dependsOn(tasks.test)
    classDirectories.setFrom(files(classDirectories.files.map { fileTree(it) { exclude(coverageExclusions) } }))
}

tasks.jacocoTestCoverageVerification {
    dependsOn(tasks.test)
    classDirectories.setFrom(files(classDirectories.files.map { fileTree(it) { exclude(coverageExclusions) } }))
    violationRules {
        rule {
            limit {
                counter = "LINE"
                minimum = "1.0".toBigDecimal()
            }
            limit {
                counter = "BRANCH"
                minimum = "1.0".toBigDecimal()
            }
        }
    }
}

tasks.check {
    dependsOn(tasks.jacocoTestCoverageVerification)
}

pitest {
    pitestVersion.set(libs.versions.pitest.core)
    junit5PluginVersion.set(libs.versions.pitest.junit5)
    targetClasses.set(listOf("com.example.app.quote.*"))
    excludedTestClasses.set(listOf("com.example.app.ModularityTest"))
    mutators.set(listOf("STRONGER"))
    mutationThreshold.set(100)
    timestampedReports.set(false)
    outputFormats.set(listOf("CSV", "HTML"))
}
