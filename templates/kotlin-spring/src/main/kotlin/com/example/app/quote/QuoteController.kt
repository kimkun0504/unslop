package com.example.app.quote

import org.springframework.http.HttpStatus
import org.springframework.http.ProblemDetail
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RestController

data class QuoteRequest(
    val lines: List<String>,
)

data class QuoteResponse(
    val subtotal: String,
    val tier: String,
    val total: String,
)

@RestController
class QuoteController {
    @PostMapping("/quotes")
    fun create(
        @RequestBody request: QuoteRequest,
    ): QuoteResponse {
        val quote = Quote.of(request.lines)
        return QuoteResponse(quote.subtotal.toString(), quote.tier.name.lowercase(), quote.total.toString())
    }

    @ExceptionHandler(InvalidAmountException::class)
    fun invalidAmount(error: InvalidAmountException): ProblemDetail =
        ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, error.message).apply {
            title = "Invalid amount"
        }
}
