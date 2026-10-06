package mbla

import (
	"context"
	"fmt"
	"sort"
	"strings"
)

type Request struct {
	Protocol  string            `json:"protocol"`
	Operation string            `json:"operation"`
	Arguments map[string]string `json:"arguments"`
	Text      string            `json:"text"`
	History   []string          `json:"history"`
	Manifest  Policy            `json:"manifest,omitempty"`
}

type Scorer interface {
	Name() string
	Score(ctx context.Context, request Request, candidates Policy) ([]float64, error)
}

type Thresholds struct {
	Initial float64
	Admit   float64
}

type Proposal struct {
	Candidates Policy
	Scores     []float64
	Initial    Policy
	Admit      Policy
}

type Glossary map[string]string

func Propose(ctx context.Context, scorer Scorer, request Request, holdings Policy, thresholds Thresholds) (Proposal, error) {
	return ProposeAmong(ctx, scorer, request, Candidates(request, holdings), thresholds)
}

func ProposeAmong(ctx context.Context, scorer Scorer, request Request, candidates Policy, thresholds Thresholds) (Proposal, error) {
	scores, err := scorer.Score(ctx, request, candidates)
	if err != nil {
		return Proposal{}, fmt.Errorf("%s: %w", scorer.Name(), err)
	}
	if len(scores) != len(candidates) {
		return Proposal{}, fmt.Errorf("%s: got %d scores for %d candidates", scorer.Name(), len(scores), len(candidates))
	}
	return Proposal{
		Candidates: candidates,
		Scores:     scores,
		Initial:    selectAtLeast(candidates, scores, thresholds.Initial),
		Admit:      selectAtLeast(candidates, scores, thresholds.Admit),
	}, nil
}

func selectAtLeast(candidates Policy, scores []float64, threshold float64) Policy {
	selected := Policy{}
	for index, candidate := range candidates {
		if scores[index] >= threshold {
			selected = append(selected, candidate)
		}
	}
	return selected
}

func Candidates(request Request, holdings Policy) Policy {
	candidates := holdings
	for _, holding := range holdings.Capability() {
		for _, value := range argumentValues(request) {
			concrete := holding
			concrete.Resource = value
			if holding.Covers(concrete) {
				candidates = candidates.Add(concrete)
			}
		}
	}
	return candidates
}

func argumentValues(request Request) []string {
	values := []string{}
	for _, key := range sortedKeys(request.Arguments) {
		values = append(values, request.Arguments[key])
	}
	return values
}

func sortedKeys(arguments map[string]string) []string {
	keys := make([]string, 0, len(arguments))
	for key := range arguments {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func Describe(request Request) string {
	var text strings.Builder
	writeLine(&text, "operation", request.Operation)
	for _, key := range sortedKeys(request.Arguments) {
		writeLine(&text, "argument "+key, request.Arguments[key])
	}
	writeLine(&text, "task", request.Text)
	for _, step := range request.History {
		writeLine(&text, "history", step)
	}
	for _, permission := range request.Manifest {
		writeLine(&text, "manifest", permission.String())
	}
	return text.String()
}

func writeLine(text *strings.Builder, label, value string) {
	if value != "" {
		fmt.Fprintf(text, "%s: %s\n", label, value)
	}
}

func DescribePermission(permission Permission, glossary Glossary) string {
	meaning, known := glossary[permission.Service+":"+permission.Operation]
	if !known {
		return permission.String()
	}
	return permission.String() + " (" + meaning + ")"
}
