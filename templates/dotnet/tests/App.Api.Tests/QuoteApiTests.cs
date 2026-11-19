using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Mvc.Testing;

namespace App.Api.Tests;

public sealed class QuoteApiTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> factory;

    public QuoteApiTests(WebApplicationFactory<Program> factory)
    {
        this.factory = factory;
    }

    [Fact]
    public async Task ReturnsTheQuote()
    {
        using HttpClient client = factory.CreateClient();
        using HttpResponseMessage response = await client.PostAsJsonAsync(new Uri("/quotes", UriKind.Relative), new { lines = new[] { "60", "40" } }, TestContext.Current.CancellationToken);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("{\"subtotal\":\"100.00\",\"tier\":\"silver\",\"total\":\"95.00\"}", await response.Content.ReadAsStringAsync(TestContext.Current.CancellationToken));
    }

    [Theory]
    [InlineData("500", "gold")]
    [InlineData("1", "standard")]
    public async Task NamesTiersInLowerCase(string amount, string tier)
    {
        using HttpClient client = factory.CreateClient();
        using HttpResponseMessage response = await client.PostAsJsonAsync(new Uri("/quotes", UriKind.Relative), new { lines = new[] { amount } }, TestContext.Current.CancellationToken);
        Assert.Contains($"\"tier\":\"{tier}\"", await response.Content.ReadAsStringAsync(TestContext.Current.CancellationToken), StringComparison.Ordinal);
    }

    [Fact]
    public async Task ReturnsProblemDetailsForAMalformedAmount()
    {
        using HttpClient client = factory.CreateClient();
        using HttpResponseMessage response = await client.PostAsJsonAsync(new Uri("/quotes", UriKind.Relative), new { lines = new[] { "1.5" } }, TestContext.Current.CancellationToken);
        string body = await response.Content.ReadAsStringAsync(TestContext.Current.CancellationToken);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.Contains("\"title\":\"Invalid amount\"", body, StringComparison.Ordinal);
        Assert.Contains("got \\u00221.5\\u0022", body, StringComparison.Ordinal);
    }
}
