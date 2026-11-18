package cli

import (
	"fmt"
	"io"

	"example.com/app/internal/domain"
)

const (
	ExitOK    = 0
	ExitUsage = 2
)

func Run(args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		_, _ = fmt.Fprintln(stderr, "usage: app AMOUNT [AMOUNT ...]")
		return ExitUsage
	}
	quote, err := domain.NewQuote(args)
	if err != nil {
		_, _ = fmt.Fprintln(stderr, err)
		return ExitUsage
	}
	_, _ = fmt.Fprintf(stdout, "subtotal=%s tier=%s total=%s\n", quote.Subtotal, quote.Tier, quote.Total)
	return ExitOK
}
