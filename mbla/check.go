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
