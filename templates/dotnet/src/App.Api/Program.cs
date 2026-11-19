using App.Api;

WebApplicationBuilder builder = WebApplication.CreateSlimBuilder(args);
builder.Services.AddProblemDetails();

WebApplication app = builder.Build();
app.UseExceptionHandler();

app.MapPost("/quotes", QuoteEndpoint.Create);

await app.RunAsync().ConfigureAwait(false);
