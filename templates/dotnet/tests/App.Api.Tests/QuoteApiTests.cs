using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Mvc.Testing;

namespace App.Api.Tests;

public sealed class QuoteApiTests(WebApplicationFactory<Program> factory) : IClassFixture<WebApplicationFactory<Program>>
{
    private static readonly Uri Quotes = new("/quotes", UriKind.Relative);

    private async Task<HttpResponseMessage> PostAsync(params string[] lines)
    {
        using HttpClient client = factory.CreateClient();
        return await client.PostAsJsonAsync(Quotes, new QuoteRequest(lines), TestContext.Current.CancellationToken);
    }

    [Fact]
    public async Task ReturnsTheQuote()
    {
        using HttpResponseMessage response = await PostAsync("60", "40");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(
            new QuoteResponse("100.00", "silver", "95.00"),
            await response.Content.ReadFromJsonAsync<QuoteResponse>(TestContext.Current.CancellationToken));
    }

    [Fact]
    public async Task ReturnsProblemDetailsForAMalformedAmount()
    {
        using HttpResponseMessage response = await PostAsync("1.5");
        string body = await response.Content.ReadAsStringAsync(TestContext.Current.CancellationToken);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.Contains("Invalid amount", body, StringComparison.Ordinal);
        Assert.Contains("1.5", body, StringComparison.Ordinal);
    }
}
