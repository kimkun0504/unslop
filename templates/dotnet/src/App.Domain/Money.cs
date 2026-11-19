using System.Globalization;
using System.Text.RegularExpressions;

namespace App.Domain;

public sealed partial class Money
{
    private const long CentsPerUnit = 100;
    private const long WholePercent = 100;

    private Money(long cents)
    {
        Cents = cents;
    }

    public static Money Zero { get; } = new(0);

    public long Cents { get; }

    public static Money Parse(string raw)
    {
        ArgumentNullException.ThrowIfNull(raw);
        string trimmed = raw.Trim();
        string canonical = trimmed.Contains('.', StringComparison.Ordinal) ? trimmed : trimmed + ".00";
        if (!CanonicalAmount().IsMatch(canonical))
        {
            throw new InvalidAmountException(raw);
        }

        return new Money(long.Parse(canonical.Replace(".", string.Empty, StringComparison.Ordinal), CultureInfo.InvariantCulture));
    }

    public Money Plus(Money other)
    {
        ArgumentNullException.ThrowIfNull(other);
        return new Money(Cents + other.Cents);
    }

    public Money LessPercent(long percent) => new(Cents * (WholePercent - percent) / WholePercent);

    public override string ToString() =>
        string.Create(CultureInfo.InvariantCulture, $"{Cents / CentsPerUnit}.{Cents % CentsPerUnit:00}");

    [GeneratedRegex(@"^(0|[1-9][0-9]{0,11})\.[0-9]{2}$", RegexOptions.CultureInvariant, matchTimeoutMilliseconds: 1000)]
    private static partial Regex CanonicalAmount();
}
