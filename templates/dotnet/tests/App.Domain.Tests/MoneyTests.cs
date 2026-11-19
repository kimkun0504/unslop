namespace App.Domain.Tests;

public sealed class MoneyTests
{
    private static readonly string[] RenderInputs = ["0.05", "10.50", "0"];

    [Theory]
    [InlineData("0", 0)]
    [InlineData("12", 1200)]
    [InlineData("12.50", 1250)]
    [InlineData(" 7.05 ", 705)]
    public void ParsesCanonicalAmounts(string raw, long cents) => Assert.Equal(cents, Money.Parse(raw).Cents);

    [Theory]
    [InlineData("")]
    [InlineData("-1")]
    [InlineData("1.5")]
    [InlineData("01")]
    [InlineData("1.005")]
    [InlineData("abc")]
    [InlineData("1,00")]
    public void RejectsMalformedAmountsWithTheInputInTheMessage(string raw)
    {
        InvalidAmountException error = Assert.Throws<InvalidAmountException>(() => Money.Parse(raw));
        Assert.Equal($"expected a non-negative amount like 12 or 12.50, got \"{raw}\"", error.Message);
    }

    [Fact]
    public void RejectsNull() =>
        Assert.Equal(
            ["raw", "other"],
            [Assert.Throws<ArgumentNullException>(() => Money.Parse(null!)).ParamName, Assert.Throws<ArgumentNullException>(() => Money.Zero.Plus(null!)).ParamName]);

    [Fact]
    public void RendersCentsWithTwoDigits() =>
        Assert.Equal(["0.05", "10.50", "0.00"], RenderInputs.Select(raw => Money.Parse(raw).ToString()));

    [Fact]
    public void AddsAndDiscounts()
    {
        var ten = Money.Parse("10");
        Assert.Equal(["15.00", "9.50"], [ten.Plus(Money.Parse("5")).ToString(), ten.LessPercent(5).ToString()]);
    }

    [Fact]
    public void ExceptionConstructorsKeepTheirMessage()
    {
        InvalidOperationException inner = new("inner");
        Assert.Equal(
            ["expected a non-negative amount like 12 or 12.50, got \"\"", "outer"],
            [new InvalidAmountException().Message, new InvalidAmountException("outer", inner).Message]);
    }
}
