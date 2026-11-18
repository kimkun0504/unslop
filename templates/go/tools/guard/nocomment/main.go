package main

import (
	"bufio"
	"fmt"
	"go/parser"
	"go/token"
	"io"
	"os"
	"regexp"
	"strings"
)

const exitParseError = 2

var generatedHeader = regexp.MustCompile(`^// Code generated .* DO NOT EDIT\.$`)

func allowed(text string) bool {
	return generatedHeader.MatchString(text) ||
		strings.HasPrefix(text, "//go:") ||
		strings.HasPrefix(text, "//line ") ||
		strings.HasPrefix(text, "//export ")
}

func violations(fset *token.FileSet, path string) ([]string, error) {
	file, err := parser.ParseFile(fset, path, nil, parser.ParseComments)
	if err != nil {
		return nil, fmt.Errorf("parse %s: %w", path, err)
	}
	var found []string
	for _, group := range file.Comments {
		for _, comment := range group.List {
			if !allowed(comment.Text) {
				found = append(found, fmt.Sprintf("%s: comments are forbidden (ADR-0001)", fset.Position(comment.Pos())))
			}
		}
	}
	return found, nil
}

func check(paths io.Reader, out io.Writer) (int, error) {
	fset := token.NewFileSet()
	count := 0
	scanner := bufio.NewScanner(paths)
	for scanner.Scan() {
		path := strings.TrimSpace(scanner.Text())
		if !strings.HasSuffix(path, ".go") {
			continue
		}
		found, err := violations(fset, path)
		if err != nil {
			return count, err
		}
		for _, line := range found {
			_, _ = fmt.Fprintln(out, line)
		}
		count += len(found)
	}
	err := scanner.Err()
	if err != nil {
		return count, fmt.Errorf("read paths: %w", err)
	}
	return count, nil
}

func main() {
	count, err := check(os.Stdin, os.Stdout)
	if err != nil {
		_, _ = fmt.Fprintln(os.Stderr, err)
		os.Exit(exitParseError)
	}
	if count > 0 {
		os.Exit(1)
	}
}
