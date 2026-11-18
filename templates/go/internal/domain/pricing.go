package domain

type Tier int

const (
	Standard Tier = iota
	Silver
	Gold
)

const (
	silverFromCents  = 10_000
	goldFromCents    = 50_000
	silverPercentOff = 5
	goldPercentOff   = 10
)

type Quote struct {
	Subtotal Money
	Tier     Tier
	Total    Money
}

func (t Tier) String() string {
	switch t {
	case Standard:
		return "standard"
	case Silver:
		return "silver"
	case Gold:
		return "gold"
	}
	return "unknown"
}

func (t Tier) percentOff() int64 {
	switch t {
	case Standard:
		return 0
	case Silver:
		return silverPercentOff
	case Gold:
		return goldPercentOff
	}
	return 0
}

func tierFor(subtotal Money) Tier {
	switch {
	case subtotal.cents >= goldFromCents:
		return Gold
	case subtotal.cents >= silverFromCents:
		return Silver
	default:
		return Standard
	}
}

func NewQuote(lines []string) (Quote, error) {
	subtotal := Money{cents: 0}
	for _, line := range lines {
		amount, err := ParseMoney(line)
		if err != nil {
			return Quote{Subtotal: Money{cents: 0}, Tier: Standard, Total: Money{cents: 0}}, err
		}
		subtotal = subtotal.Plus(amount)
	}
	tier := tierFor(subtotal)
	return Quote{Subtotal: subtotal, Tier: tier, Total: subtotal.LessPercent(tier.percentOff())}, nil
}
