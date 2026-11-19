package com.example.app.quote;

import java.util.List;
import java.util.Locale;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class QuoteController {
  public record QuoteRequest(List<String> lines) {}

  public record QuoteResponse(String subtotal, String tier, String total) {}

  @PostMapping("/quotes")
  public QuoteResponse create(@RequestBody QuoteRequest request) {
    Quote quote = Quote.of(request.lines());
    return new QuoteResponse(
        quote.subtotal().toString(),
        quote.tier().name().toLowerCase(Locale.ROOT),
        quote.total().toString());
  }

  @ExceptionHandler(InvalidAmountException.class)
  public ProblemDetail invalidAmount(InvalidAmountException error) {
    ProblemDetail problem =
        ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, error.getMessage());
    problem.setTitle("Invalid amount");
    return problem;
  }
}
