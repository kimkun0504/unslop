package com.example.app.quote;

public final class InvalidAmountException extends IllegalArgumentException {
  public InvalidAmountException(String raw) {
    super("expected a non-negative amount like 12 or 12.50, got \"%s\"".formatted(raw));
  }
}
