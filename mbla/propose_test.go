package mbla

import (
	"context"
	"strings"
	"testing"
)

type fixedScorer struct{ scores []float64 }

func (fixedScorer) Name() string { return "fixed" }

func (scorer fixedScorer) Score(context.Context, Request, Policy) ([]float64, error) {
	return scorer.scores, nil
}

var triageRequest = Request{
	Operation: "github.triage",
	Arguments: map[string]string{"issue": "acme/web#42"},
	Text:      "Triage issue 42 in acme/web.",
	Manifest:  MustParsePolicy("github:issue.read:acme/web#42"),
}

func TestCandidatesConcretizeFromArguments(t *testing.T) {
	holdings := MustParsePolicy("github:issue.read:acme/*", "github:issue.comment:acme/*", "net:connect:api.github.com:443", "net:connect:*")
	candidates := Candidates(triageRequest, holdings)
	want := []string{
		"github:issue.read:acme/*",
		"github:issue.comment:acme/*",
		"net:connect:api.github.com:443",
		"net:connect:*",
		"github:issue.read:acme/web#42",
		"github:issue.comment:acme/web#42",
	}
	if strings.Join(candidates.Strings(), ",") != strings.Join(want, ",") {
		t.Fatalf("candidates: %v", candidates.Strings())
	}
	if !candidates.Within(holdings) {
		t.Fatal("candidates escaped holdings")
	}
}

func TestProposeAppliesThresholds(t *testing.T) {
	holdings := MustParsePolicy("fs:r:/a", "fs:r:/b", "fs:r:/c")
	proposal, err := Propose(context.Background(), fixedScorer{[]float64{0.9, 0.5, 0.1}}, Request{}, holdings, Thresholds{Initial: 0.8, Admit: 0.3})
	if err != nil {
		t.Fatal(err)
	}
	if len(proposal.Initial) != 1 || len(proposal.Admit) != 2 {
		t.Fatalf("initial %v admit %v", proposal.Initial.Strings(), proposal.Admit.Strings())
	}
}

func TestProposeRejectsWrongScoreCount(t *testing.T) {
	holdings := MustParsePolicy("fs:r:/a", "fs:r:/b")
	if _, err := Propose(context.Background(), fixedScorer{[]float64{1}}, Request{}, holdings, Thresholds{}); err == nil {
		t.Fatal("want error for missing score")
	}
}

func TestBaselineScorers(t *testing.T) {
	candidates := MustParsePolicy("github:issue.read:acme/web#42", "github:issue.comment:acme/web#1", "fs:w:/workspace")
	ctx := context.Background()
	setOnly, _ := SetOnly{}.Score(ctx, triageRequest, candidates)
	manifestOnly, _ := ManifestOnly{}.Score(ctx, triageRequest, candidates)
	lexical, _ := Lexical{}.Score(ctx, triageRequest, candidates)
	expectScores(t, "set-only", setOnly, []float64{1, 1, 1})
	expectScores(t, "manifest-only", manifestOnly, []float64{1, 0, 0})
	expectScores(t, "lexical", lexical, []float64{1, 0, 0})
}

func expectScores(t *testing.T, name string, got, want []float64) {
	t.Helper()
	for index := range want {
		if got[index] != want[index] {
			t.Errorf("%s: got %v want %v", name, got, want)
			return
		}
	}
}

func TestDescribe(t *testing.T) {
	text := Describe(triageRequest)
	for _, part := range []string{"operation: github.triage", "argument issue: acme/web#42", "task: Triage", "manifest: github:issue.read:acme/web#42"} {
		if !strings.Contains(text, part) {
			t.Errorf("describe missing %q in:\n%s", part, text)
		}
	}
	glossary := Glossary{"github:issue.read": "read one issue"}
	if got := DescribePermission(MustParse("github:issue.read:a/b#1"), glossary); got != "github:issue.read:a/b#1 (read one issue)" {
		t.Errorf("describe permission: %q", got)
	}
}
