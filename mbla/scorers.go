package mbla

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"fmt"
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

type Random struct {
	Seed int
}

func (Random) Name() string { return "random" }

func (random Random) Score(_ context.Context, request Request, candidates Policy) ([]float64, error) {
	scores := make([]float64, len(candidates))
	for index, candidate := range candidates {
		scores[index] = uniform(fmt.Sprintf("%d|%s|%s|%s", random.Seed, request.Operation, request.Text, candidate))
	}
	return scores, nil
}

// uniform maps a key to [0, 1) so a seed reproduces the same coin flips on every run.
func uniform(key string) float64 {
	digest := sha256.Sum256([]byte(key))
	return float64(binary.BigEndian.Uint64(digest[:8])>>11) / float64(1<<53)
}
