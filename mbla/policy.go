package mbla

import (
	"encoding/json"
	"slices"
)

type Policy []Permission

func ParsePolicy(texts []string) (Policy, error) {
	policy := Policy{}
	for _, text := range texts {
		permission, err := Parse(text)
		if err != nil {
			return nil, err
		}
		policy = policy.Add(permission)
	}
	return policy, nil
}

func MustParsePolicy(texts ...string) Policy {
	policy, err := ParsePolicy(texts)
	if err != nil {
		panic(err)
	}
	return policy
}

func (policy Policy) Covers(requested Permission) bool {
	for _, granted := range policy {
		if granted.Covers(requested) {
			return true
		}
	}
	return false
}

func (policy Policy) Within(bound Policy) bool {
	return len(policy.Uncovered(bound)) == 0
}

func (policy Policy) Uncovered(bound Policy) Policy {
	uncovered := Policy{}
	for _, permission := range policy {
		if !bound.Covers(permission) {
			uncovered = append(uncovered, permission)
		}
	}
	return uncovered
}

func (policy Policy) Intersect(other Policy) Policy {
	shared := Policy{}
	for _, permission := range policy {
		if other.Covers(permission) {
			shared = shared.Add(permission)
		}
	}
	for _, permission := range other {
		if policy.Covers(permission) {
			shared = shared.Add(permission)
		}
	}
	return shared
}

func (policy Policy) Contains(permission Permission) bool {
	return slices.Contains(policy, permission)
}

func (policy Policy) Add(permission Permission) Policy {
	if policy.Contains(permission) {
		return policy
	}
	return append(slices.Clone(policy), permission)
}

func (policy Policy) OfKind(kind Kind) Policy {
	matching := Policy{}
	for _, permission := range policy {
		if permission.Kind() == kind {
			matching = append(matching, permission)
		}
	}
	return matching
}

func (policy Policy) Capability() Policy  { return policy.OfKind(Capability) }
func (policy Policy) Network() Policy     { return policy.OfKind(Network) }
func (policy Policy) Filesystem() Policy  { return policy.OfKind(Filesystem) }
func (policy Policy) Executables() Policy { return policy.OfKind(Executable) }

func (policy Policy) Strings() []string {
	texts := make([]string, 0, len(policy))
	for _, permission := range policy {
		texts = append(texts, permission.String())
	}
	return texts
}

func (policy Policy) MarshalJSON() ([]byte, error) {
	return json.Marshal(policy.Strings())
}
