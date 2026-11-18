package cli_test

import (
	"bytes"
	"testing"

	"example.com/app/internal/cli"
)

func run(args ...string) (int, string, string) {
	var stdout, stderr bytes.Buffer
	code := cli.Run(args, &stdout, &stderr)
	return code, stdout.String(), stderr.String()
}

func TestRunPrintsTheQuote(t *testing.T) {
	t.Parallel()
	code, out, errOut := run("60", "40")
	if code != cli.ExitOK || out != "subtotal=100.00 tier=silver total=95.00\n" || errOut != "" {
		t.Fatalf("run = %d %q %q", code, out, errOut)
	}
}

func TestRunRejectsMissingAmounts(t *testing.T) {
	t.Parallel()
	code, out, errOut := run()
	if code != cli.ExitUsage || out != "" || errOut != "usage: app AMOUNT [AMOUNT ...]\n" {
		t.Fatalf("run = %d %q %q", code, out, errOut)
	}
}

func TestRunRejectsMalformedAmounts(t *testing.T) {
	t.Parallel()
	code, out, errOut := run("1.5")
	if code != cli.ExitUsage || out != "" || errOut != "expected a non-negative amount like 12 or 12.50, got \"1.5\"\n" {
		t.Fatalf("run = %d %q %q", code, out, errOut)
	}
}
