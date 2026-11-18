package com.example.app

import org.junit.jupiter.api.Test
import org.springframework.modulith.core.ApplicationModules

class ModularityTest {
    @Test
    fun `modules respect their boundaries`() {
        ApplicationModules.of(Application::class.java).verify()
    }
}
