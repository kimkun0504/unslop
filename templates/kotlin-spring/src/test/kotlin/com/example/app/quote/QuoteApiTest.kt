package com.example.app.quote

import org.junit.jupiter.api.Test
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment
import org.springframework.boot.test.web.server.LocalServerPort
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import kotlin.test.assertContains
import kotlin.test.assertEquals

@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
class QuoteApiTest(
    @LocalServerPort private val port: Int,
) {
    private fun post(body: String): HttpResponse<String> =
        HttpClient.newHttpClient().send(
            HttpRequest
                .newBuilder(URI.create("http://localhost:$port/quotes"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build(),
            HttpResponse.BodyHandlers.ofString(),
        )

    @Test
    fun `returns the quote`() {
        val response = post("""{"lines":["60","40"]}""")
        assertEquals(200, response.statusCode())
        assertEquals("""{"subtotal":"100.00","tier":"silver","total":"95.00"}""", response.body())
    }

    @Test
    fun `returns problem details for a malformed amount`() {
        val response = post("""{"lines":["1.5"]}""")
        assertEquals(400, response.statusCode())
        assertEquals("application/problem+json", response.headers().firstValue("Content-Type").orElse(""))
        assertContains(response.body(), """"title":"Invalid amount"""")
        assertContains(response.body(), """got \"1.5\""""")
    }
}
