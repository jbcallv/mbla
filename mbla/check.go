package mbla

import (
	"errors"
	"fmt"
)

var ErrExceedsParent = errors.New("exceeds parent")

func CheckAttenuation(child, parent Policy) error {
	uncovered := child.Uncovered(parent)
	if len(uncovered) == 0 {
		return nil
	}
	return fmt.Errorf("%w: %s", ErrExceedsParent, uncovered[0])
}

func ApplyCeiling(proposal, ceiling Policy) (installed, dropped Policy) {
	return proposal.Intersect(ceiling), proposal.Uncovered(ceiling)
}

func Bound(parent, ceiling Policy) Policy {
	return parent.Intersect(ceiling)
}

// WithinCeiling reports whether the sandbox part of a proposal (destinations and volumes) is within the receiver's
// ceiling. C is bounded by the parent only; a proposal outside the ceiling is rejected whole.
func WithinCeiling(proposal, ceiling Policy) bool {
	for _, permission := range proposal {
		if permission.Kind() != Capability && !ceiling.Covers(permission) {
			return false
		}
	}
	return true
}
