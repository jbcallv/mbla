package mbla

import (
	"context"
	"strings"
)

type SetOnly struct{}

type ManifestOnly struct{}

type Lexical struct{}

func (SetOnly) Name() string      { return "set-only" }
func (ManifestOnly) Name() string { return "manifest-only" }
func (Lexical) Name() string      { return "lexical" }

func (SetOnly) Score(_ context.Context, _ Request, candidates Policy) ([]float64, error) {
	return scoreEach(candidates, func(Permission) bool { return true }), nil
}

func (ManifestOnly) Score(_ context.Context, request Request, candidates Policy) ([]float64, error) {
	return scoreEach(candidates, request.Manifest.Covers), nil
}

func (Lexical) Score(_ context.Context, request Request, candidates Policy) ([]float64, error) {
	mentioned := request.Text + " " + strings.Join(argumentValues(request), " ")
	return scoreEach(candidates, func(candidate Permission) bool {
		return strings.Contains(mentioned, candidate.Resource)
	}), nil
}

func scoreEach(candidates Policy, isSelected func(Permission) bool) []float64 {
	scores := make([]float64, len(candidates))
	for index, candidate := range candidates {
		if isSelected(candidate) {
			scores[index] = 1
		}
	}
	return scores
}
