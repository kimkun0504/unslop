package com.example.app;

import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;

class ModularityTest {
  @Test
  void modulesRespectTheirBoundaries() {
    ApplicationModules.of(Application.class).verify();
  }
}
