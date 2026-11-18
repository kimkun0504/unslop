package domain_test

import (
	"errors"
	"strconv"
	"testing"

	"example.com/app/internal/domain"
)

func TestParseMoneyAcceptsCanonicalAmounts(t *testing.T) {
	t.Parallel()
	cases := []struct {
		raw   string
		cents int64
	}{{"0", 0}, {"12", 1200}, {"12.50", 1250}, {"\t7.05 ", 705}}
	for _, tc := range cases {
		t.Run(tc.raw, func(t *testing.T) {
			t.Parallel()
			money, err := domain.ParseMoney(tc.raw)
			if err != nil || money.Cents() != tc.cents {
				t.Fatalf("ParseMoney(%q) = %d, %v; want %d", tc.raw, money.Cents(), err, tc.cents)
			}
		})
	}
}

func TestParseMoneyRejectsMalformedAmounts(t *testing.T) {
	t.Parallel()
	for _, raw := range []string{"", "-1", "1.5", "01", "1.005", "abc", "1,00", "1.2.3"} {
		t.Run(raw, func(t *testing.T) {
			t.Parallel()
			_, err := domain.ParseMoney(raw)
			want := "expected a non-negative amount like 12 or 12.50, got " + strconv.Quote(raw)
			if !errors.Is(err, domain.ErrInvalidAmount) || err.Error() != want {
				t.Fatalf("ParseMoney(%q) error = %v; want %q", raw, err, want)
			}
		})
	}
}

func TestMoneyArithmetic(t *testing.T) {
	t.Parallel()
	ten, _ := domain.ParseMoney("10")
	five, _ := domain.ParseMoney("5")
	if got := ten.Plus(five).String(); got != "15.00" {
		t.Fatalf("10 + 5 = %s", got)
	}
	if got := ten.LessPercent(5).String(); got != "9.50" {
		t.Fatalf("10 less 5%% = %s", got)
	}
}

func FuzzParseMoneyRoundTrips(f *testing.F) {
	for _, seed := range []string{"0", "1.05", "999999999999.99", "abc", "-1"} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, raw string) {
		money, err := domain.ParseMoney(raw)
		if err != nil {
			return
		}
		again, err := domain.ParseMoney(money.String())
		if err != nil || again != money || money.Cents() < 0 {
			t.Fatalf("round trip of %q gave %v, %v", raw, again, err)
		}
		if discounted := money.LessPercent(10); discounted.Cents() < 0 || discounted.Cents() > money.Cents() {
			t.Fatalf("discount of %v out of range: %v", money, discounted)
		}
	})
}
