namespace App.Domain;

public sealed class InvalidAmountException : ArgumentException
{
    public InvalidAmountException()
        : this(string.Empty)
    {
    }

    public InvalidAmountException(string raw)
        : base($"expected a non-negative amount like 12 or 12.50, got \"{raw}\"")
    {
    }

    public InvalidAmountException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}
