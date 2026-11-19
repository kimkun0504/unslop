namespace App.Domain;

public enum Tier
{
    Standard,
    Silver,
    Gold,
}

public sealed record Quote(Money Subtotal, Tier Tier, Money Total)
{
    private const long SilverFromCents = 10_000;
    private const long GoldFromCents = 50_000;

    public static Quote Of(IEnumerable<string> lines)
    {
        Money subtotal = lines.Select(Money.Parse).Aggregate(Money.Zero, (sum, amount) => sum.Plus(amount));
        Tier tier = TierFor(subtotal);
        return new Quote(subtotal, tier, subtotal.LessPercent(PercentOff(tier)));
    }

    public static Tier TierFor(Money subtotal)
    {
        ArgumentNullException.ThrowIfNull(subtotal);
        return subtotal.Cents >= GoldFromCents ? Tier.Gold
            : subtotal.Cents >= SilverFromCents ? Tier.Silver
            : Tier.Standard;
    }

    public static long PercentOff(Tier tier) => tier switch
    {
        Tier.Standard => 0,
        Tier.Silver => 5,
        Tier.Gold => 10,
        _ => throw new ArgumentOutOfRangeException(nameof(tier)),
    };

    public static string NameOf(Tier tier) => tier switch
    {
        Tier.Standard => "standard",
        Tier.Silver => "silver",
        Tier.Gold => "gold",
        _ => throw new ArgumentOutOfRangeException(nameof(tier)),
    };
}
