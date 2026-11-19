package com.example.app.quote;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.boot.test.web.server.LocalServerPort;

@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
class QuoteApiTest {
  @LocalServerPort private int port;

  private HttpResponse<String> post(String body) throws IOException, InterruptedException {
    try (HttpClient client = HttpClient.newHttpClient()) {
      return client.send(
          HttpRequest.newBuilder(URI.create("http://localhost:%d/quotes".formatted(port)))
              .header("Content-Type", "application/json")
              .POST(HttpRequest.BodyPublishers.ofString(body))
              .build(),
          HttpResponse.BodyHandlers.ofString());
    }
  }

  @Test
  void returnsTheQuote() throws IOException, InterruptedException {
    HttpResponse<String> response = post("{\"lines\":[\"60\",\"40\"]}");
    assertThat(response.statusCode()).isEqualTo(200);
    assertThat(response.body())
        .isEqualTo("{\"subtotal\":\"100.00\",\"tier\":\"silver\",\"total\":\"95.00\"}");
  }

  @Test
  void returnsProblemDetailsForAMalformedAmount() throws IOException, InterruptedException {
    HttpResponse<String> response = post("{\"lines\":[\"1.5\"]}");
    assertThat(response.statusCode()).isEqualTo(400);
    assertThat(response.headers().firstValue("Content-Type")).hasValue("application/problem+json");
    assertThat(response.body()).contains("\"title\":\"Invalid amount\"", "got \\\"1.5\\\"");
  }
}
