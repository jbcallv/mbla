package mbla

import (
	"context"
	"strconv"
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
	Receiver:  Receiver{Name: "triage-agent"},
	Text:      "Triage issue 42 in acme/web.",
	Manifest:  MustParsePolicy("github:issue.read:acme/web/issues/42/*"),
	Named:     []string{"github:acme/web/issues/42/"},
}

func TestCandidatesNarrowToNamedResources(t *testing.T) {
	holdings := MustParsePolicy("github:issue.read:acme/*", "github:contents.read:acme/*", "net:connect:attacker.example:443", "fs:rw:/workspace")
	candidates := Candidates(triageRequest, holdings)
	want := []string{
		"github:issue.read:acme/*",
		"github:contents.read:acme/*",
		"net:connect:attacker.example:443",
		"fs:ro:/workspace",
		"fs:rw:/workspace",
		"github:issue.read:acme/web/issues/42/*",
	}
	if strings.Join(candidates.Strings(), ",") != strings.Join(want, ",") {
		t.Fatalf("candidates: %v", candidates.Strings())
	}
	if !candidates.Within(holdings) {
		t.Fatal("candidates escaped holdings")
	}
}

func TestCandidatesOfferReadOnlyVolumes(t *testing.T) {
	holdings := MustParsePolicy("fs:rw:/workspace/src", "fs:ro:/data")
	want := "fs:ro:/workspace/src,fs:rw:/workspace/src,fs:ro:/data"
	if got := strings.Join(Candidates(Request{}, holdings).Strings(), ","); got != want {
		t.Fatalf("candidates: %s", got)
	}
}

func TestCandidatesOmitVolumesForRemoteReceiver(t *testing.T) {
	request := Request{Receiver: Receiver{Name: "deploy-agent", Remote: true}, Named: []string{"storage:acme-staging/web/app.tar.gz/"}}
	holdings := MustParsePolicy("storage:object.put:acme-staging/*", "fs:rw:/workspace")
	want := "storage:object.put:acme-staging/*,storage:object.put:acme-staging/web/app.tar.gz/*"
	if got := strings.Join(Candidates(request, holdings).Strings(), ","); got != want {
		t.Fatalf("candidates: %s", got)
	}
}

func TestResourceFits(t *testing.T) {
	cases := []struct {
		operation, service, resource string
		want                         bool
	}{
		{"issue.read", "github", "acme/web/issues/42/", true},
		{"contents.read", "github", "acme/web/issues/42/", false},
		{"contents.read", "github", "acme/web/contents/~default/README.md/", true},
		{"doc.read", "docs", "doc/roadmap/", true},
		{"folder.list", "docs", "doc/roadmap/", false},
		{"message.post", "slack", "T01/C042/", true},
		{"message.post", "slack", "T01/U042/", false},
		{"user.read", "slack", "T01/U042/", true},
		{"object.get", "storage", "acme-builds/web/app.tar.gz/", true},
	}
	for _, testCase := range cases {
		if got := ResourceFits(testCase.operation, testCase.service, testCase.resource); got != testCase.want {
			t.Errorf("%s on %s: got %v", testCase.operation, testCase.resource, got)
		}
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
	candidates := MustParsePolicy("github:issue.read:acme/web/issues/42/*", "github:issue.comment:acme/web/issues/1/*", "fs:rw:/workspace")
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
	for _, part := range []string{"task: Triage", "manifest: github:issue.read:acme/web/issues/42/*"} {
		if !strings.Contains(text, part) {
			t.Errorf("describe missing %q in:\n%s", part, text)
		}
	}
	for _, part := range []string{"operation:", "receiver:", "history:", "triage-agent"} {
		if strings.Contains(text, part) {
			t.Errorf("describe shows %q, which the adapter does not send:\n%s", part, text)
		}
	}
	if strings.Contains(text, "acme/web/issues/42/\n") {
		t.Error("named resources leaked into the description")
	}
	glossary := Glossary{"github:issue.read": "read one issue"}
	if got := DescribePermission(MustParse("github:issue.read:a/b#1"), glossary); got != "github:issue.read:a/b#1 (read one issue)" {
		t.Errorf("describe permission: %q", got)
	}
}

func TestRandomScorer(t *testing.T) {
	candidates := MustParsePolicy("github:issue.read:acme/web#42", "github:issue.comment:acme/web#1", "fs:w:/workspace")
	ctx := context.Background()
	first, _ := Random{Seed: 1}.Score(ctx, triageRequest, candidates)
	again, _ := Random{Seed: 1}.Score(ctx, triageRequest, candidates)
	other, _ := Random{Seed: 2}.Score(ctx, triageRequest, candidates)
	expectScores(t, "same seed", again, first)
	if first[0] == other[0] && first[1] == other[1] && first[2] == other[2] {
		t.Error("different seeds gave identical scores")
	}
	for _, score := range first {
		if score < 0 || score >= 1 {
			t.Errorf("score %v outside [0, 1)", score)
		}
	}
}

func TestRandomScorerIsUniform(t *testing.T) {
	below := 0
	for index := range 10000 {
		if uniform(strconv.Itoa(index)) < 0.25 {
			below++
		}
	}
	if below < 2350 || below > 2650 {
		t.Errorf("got %d of 10000 below 0.25, want about 2500", below)
	}
}
