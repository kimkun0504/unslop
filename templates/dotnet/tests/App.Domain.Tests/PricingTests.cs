namespace App.Domain.Tests;

public sealed class PricingTests
{
    [Theory]
    [InlineData("", "0.00 Standard 0.00")]
    [InlineData("99.99", "99.99 Standard 99.99")]
    [InlineData("60;40", "100.00 Silver 95.00")]
    [InlineData("499.99", "499.99 Silver 474.99")]
    [InlineData("500", "500.00 Gold 450.00")]
    public void AppliesTheTierForTheSubtotal(string lines, string expected)
    {
        var quote = Quote.Of(lines.Split(';', StringSplitOptions.RemoveEmptyEntries));
        Assert.Equal(expected, $"{quote.Subtotal} {quote.Tier} {quote.Total}");
    }

    [Fact]
    public void ReportsTheFirstMalformedLine()
    {
        InvalidAmountException error = Assert.Throws<InvalidAmountException>(() => Quote.Of(["1", "x", "y"]));
        Assert.Equal("expected a non-negative amount like 12 or 12.50, got \"x\"", error.Message);
    }

    [Theory]
    [InlineData(Tier.Standard, "standard", 0)]
    [InlineData(Tier.Silver, "silver", 5)]
    [InlineData(Tier.Gold, "gold", 10)]
    public void NamesAndDiscountsEachTier(Tier tier, string name, long percent) =>
        Assert.Equal((name, percent), (Quote.NameOf(tier), Quote.PercentOff(tier)));

    [Fact]
    public void RejectsUndefinedTiers()
    {
        const Tier undefined = (Tier)99;
        Assert.Equal(
            ["tier", "tier"],
            [Assert.Throws<ArgumentOutOfRangeException>(() => Quote.NameOf(undefined)).ParamName, Assert.Throws<ArgumentOutOfRangeException>(() => Quote.PercentOff(undefined)).ParamName]);
    }

    [Fact]
    public void TierForRejectsNull() => Assert.Throws<ArgumentNullException>(() => Quote.TierFor(null!));
}
