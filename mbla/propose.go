package mbla

import (
	"context"
	"fmt"
	"strings"
)

// Request is what the delegator knows about one delegation. A scorer sees only the text and the manifest, as
// BoundClaw's adapter sends; the receiver and named resources only build candidates.
type Request struct {
	Protocol  string   `json:"protocol"`
	Operation string   `json:"operation"`
	Receiver  Receiver `json:"receiver"`
	Text      string   `json:"text"`
	History   []string `json:"history"`
	Manifest  Policy   `json:"manifest,omitempty"`
	Named     []string `json:"named,omitempty"`
}

type Receiver struct {
	Name   string `json:"name"`
	Remote bool   `json:"remote"`
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

// Candidates lists what a scorer chooses from: every holding, a narrower grant for each named resource under a
// granted prefix, and volumes only for a local receiver, a read-write volume also read-only (as BoundClaw's adapter
// offers it). Hosts with a parser are not holdings and never appear.
func Candidates(request Request, holdings Policy) Policy {
	candidates := Policy{}
	for _, holding := range holdings {
		if holding.Kind() == Filesystem && request.Receiver.Remote {
			continue
		}
		if holding.Kind() == Filesystem && holding.Operation == "rw" {
			candidates = candidates.Add(VolumePermission(holding.Resource, false))
		}
		candidates = candidates.Add(holding)
	}
	for _, holding := range holdings.Capability() {
		for _, named := range request.Named {
			if narrower, fits := narrowTo(holding, named); fits {
				candidates = candidates.Add(narrower)
			}
		}
	}
	return candidates
}

func narrowTo(holding Permission, named string) (Permission, bool) {
	service, resource, found := strings.Cut(named, ":")
	if !found || service != holding.Service || !ResourceFits(holding.Operation, service, resource) {
		return Permission{}, false
	}
	narrower := holding
	narrower.Resource = resource + "*"
	return narrower, narrower != holding && holding.Covers(narrower)
}

// ResourceFits keeps an operation on the resource type it acts on in BoundClaw's atom forms, so that
// github:contents.read never narrows to an issue and slack:user.read never narrows to a channel.
func ResourceFits(operation, service, resource string) bool {
	family, _, _ := strings.Cut(operation, ".")
	segments := strings.Split(resource, "/")
	switch service {
	case "github":
		return len(segments) > 2 && segments[2] == githubSegments[family]
	case "docs":
		return segments[0] == docsSegments[operation]
	case "slack":
		return len(segments) > 1 && strings.HasPrefix(segments[1], "U") == (operation == "user.read")
	}
	return true
}

var githubSegments = map[string]string{"issue": "issues", "contents": "contents", "pull": "pulls", "release": "releases", "actions": "actions"}

var docsSegments = map[string]string{
	"doc.read": "doc", "doc.write": "doc", "doc.comment": "doc", "doc.share": "doc", "doc.create": "folder", "folder.list": "folder",
}

func Describe(request Request) string {
	var text strings.Builder
	writeLine(&text, "task", request.Text)
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
