package domain_test

import (
	"errors"
	"strings"
	"testing"

	"example.com/app/internal/domain"
)

func TestNewQuoteAppliesTheTierForTheSubtotal(t *testing.T) {
	t.Parallel()
	cases := []struct {
		want  string
		lines []string
	}{
		{"0.00 standard 0.00", nil},
		{"99.99 standard 99.99", []string{"99.99"}},
		{"100.00 silver 95.00", []string{"60", "40"}},
		{"499.99 silver 474.99", []string{"499.99"}},
		{"500.00 gold 450.00", []string{"500"}},
	}
	for _, tc := range cases {
		t.Run(strings.Join(tc.lines, ","), func(t *testing.T) {
			t.Parallel()
			quote, err := domain.NewQuote(tc.lines)
			got := quote.Subtotal.String() + " " + quote.Tier.String() + " " + quote.Total.String()
			if err != nil || got != tc.want {
				t.Fatalf("NewQuote(%v) = %q, %v; want %q", tc.lines, got, err, tc.want)
			}
		})
	}
}

func TestNewQuoteReportsTheFirstMalformedLine(t *testing.T) {
	t.Parallel()
	_, err := domain.NewQuote([]string{"1", "x", "y"})
	if !errors.Is(err, domain.ErrInvalidAmount) || !strings.HasSuffix(err.Error(), `got "x"`) {
		t.Fatalf("error = %v", err)
	}
}

func TestUnknownTierHasAName(t *testing.T) {
	t.Parallel()
	if got := domain.Tier(99).String(); got != "unknown" {
		t.Fatalf("Tier(99) = %q", got)
	}
}
