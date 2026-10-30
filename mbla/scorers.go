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

// Lexical selects a candidate when every name in its resource appears in the task text.
func (Lexical) Score(_ context.Context, request Request, candidates Policy) ([]float64, error) {
	text := strings.ToLower(request.Text)
	return scoreEach(candidates, func(candidate Permission) bool {
		names := resourceNames(candidate)
		for _, name := range names {
			if !strings.Contains(text, name) {
				return false
			}
		}
		return len(names) > 0
	}), nil
}

var structuralSegments = map[string]bool{"": true, "*": true, "issues": true, "contents": true, "pulls": true, "releases": true, "actions": true, "doc": true, "folder": true, "~default": true}

var boundClawServices = map[string]bool{"github": true, "storage": true, "docs": true, "slack": true}

// resourceNames lists what a permission is about: resource names in BoundClaw's forms, the host or volume otherwise,
// and the operation for catalogs that name a tool or skill there (FORTIS).
func resourceNames(candidate Permission) []string {
	resource := strings.ToLower(candidate.Resource)
	if candidate.Kind() == Capability && !boundClawServices[candidate.Service] {
		return strings.FieldsFunc(strings.ToLower(candidate.Operation), func(r rune) bool { return r == '_' || r == '-' || r == '.' })
	}
	if candidate.Kind() != Capability {
		return []string{strings.TrimSuffix(resource, ":443")}
	}
	segments := strings.Split(resource, "/")
	if candidate.Service == "slack" {
		segments = segments[1:]
	}
	names := []string{}
	for _, segment := range segments {
		if !structuralSegments[segment] {
			names = append(names, segment)
		}
	}
	return names
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
