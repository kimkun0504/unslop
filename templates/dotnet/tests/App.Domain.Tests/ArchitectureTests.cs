namespace App.Domain.Tests;

public sealed class ArchitectureTests
{
    private static readonly string[] Allowed = ["System.Runtime", "System.Linq", "System.Text.RegularExpressions", "System.Collections"];

    [Fact]
    public void DomainReferencesOnlyPureFrameworkAssemblies()
    {
        IEnumerable<string> referenced = typeof(Money).Assembly.GetReferencedAssemblies()
            .Select(name => name.Name ?? string.Empty)
            .Where(name => !Allowed.Contains(name, StringComparer.Ordinal));
        Assert.Empty(referenced);
    }
}
