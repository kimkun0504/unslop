using App.Domain;

WebApplicationBuilder builder = WebApplication.CreateSlimBuilder(args);
builder.Services.AddProblemDetails();

WebApplication app = builder.Build();
app.UseExceptionHandler();

app.MapPost("/quotes", QuoteEndpoint.Create);

await app.RunAsync().ConfigureAwait(false);

internal static class QuoteEndpoint
{
    internal static IResult Create(QuoteRequest request)
    {
        try
        {
            Quote quote = Quote.Of(request.Lines);
            return TypedResults.Ok(new QuoteResponse(
                quote.Subtotal.ToString(),
                TierName(quote.Tier),
                quote.Total.ToString()));
        }
        catch (InvalidAmountException error)
        {
            return TypedResults.Problem(error.Message, statusCode: StatusCodes.Status400BadRequest, title: "Invalid amount");
        }
    }

    private static string TierName(Tier tier) => tier switch
    {
        Tier.Silver => "silver",
        Tier.Gold => "gold",
        _ => "standard",
    };
}

internal sealed record QuoteRequest(IReadOnlyList<string> Lines);

internal sealed record QuoteResponse(string Subtotal, string Tier, string Total);

internal sealed partial class Program;
