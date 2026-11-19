using App.Domain;

namespace App.Api;

internal static class QuoteEndpoint
{
    internal static IResult Create(QuoteRequest request)
    {
        try
        {
            var quote = Quote.Of(request.Lines);
            return TypedResults.Ok(new QuoteResponse(
                quote.Subtotal.ToString(),
                Quote.NameOf(quote.Tier),
                quote.Total.ToString()));
        }
        catch (InvalidAmountException error)
        {
            return TypedResults.Problem(error.Message, statusCode: StatusCodes.Status400BadRequest, title: "Invalid amount");
        }
    }
}

internal sealed record QuoteRequest(IReadOnlyList<string> Lines);

internal sealed record QuoteResponse(string Subtotal, string Tier, string Total);
