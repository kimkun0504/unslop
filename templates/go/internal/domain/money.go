package domain

import (
	"errors"
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

const (
	centsPerUnit = 100
	wholePercent = 100
	parseBase    = 10
	parseBitSize = 64
)

var (
	canonicalAmount  = regexp.MustCompile(`^(0|[1-9][0-9]{0,11})\.[0-9]{2}$`)
	ErrInvalidAmount = errors.New("expected a non-negative amount like 12 or 12.50")
)

type Money struct {
	cents int64
}

func ParseMoney(raw string) (Money, error) {
	trimmed := strings.TrimSpace(raw)
	canonical := trimmed
	if !strings.Contains(trimmed, ".") {
		canonical = trimmed + ".00"
	}
	if !canonicalAmount.MatchString(canonical) {
		return Money{}, fmt.Errorf("%w, got %q", ErrInvalidAmount, raw)
	}
	cents, _ := strconv.ParseInt(strings.Replace(canonical, ".", "", 1), parseBase, parseBitSize)
	return Money{cents: cents}, nil
}

func (m Money) Cents() int64 {
	return m.cents
}

func (m Money) Plus(other Money) Money {
	return Money{cents: m.cents + other.cents}
}

func (m Money) LessPercent(percent int64) Money {
	return Money{cents: m.cents * (wholePercent - percent) / wholePercent}
}

func (m Money) String() string {
	return fmt.Sprintf("%d.%02d", m.cents/centsPerUnit, m.cents%centsPerUnit)
}
