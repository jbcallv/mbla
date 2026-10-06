package mbla

import (
	"encoding/json"
	"math/rand"
	"testing"
)

func TestWithinAndUncovered(t *testing.T) {
	parent := MustParsePolicy("github:issue.read:acme/*", "fs:w:/workspace")
	child := MustParsePolicy("github:issue.read:acme/web#1", "fs:w:/workspace/tmp")
	if !child.Within(parent) {
		t.Fatal("child should be within parent")
	}
	wider := child.Add(MustParse("net:connect:attacker.example:443"))
	uncovered := wider.Uncovered(parent)
	if len(uncovered) != 1 || uncovered[0].String() != "net:connect:attacker.example:443" {
		t.Fatalf("uncovered: %v", uncovered.Strings())
	}
}

func TestIntersectKeepsNarrowerSide(t *testing.T) {
	proposal := MustParsePolicy("github:issue.read:acme/*", "net:connect:attacker.example:443")
	ceiling := MustParsePolicy("github:issue.read:acme/web", "net:connect:api.github.com:443")
	shared := proposal.Intersect(ceiling)
	if len(shared) != 1 || shared[0].String() != "github:issue.read:acme/web" {
		t.Fatalf("intersect: %v", shared.Strings())
	}
}

func TestIntersectIsSound(t *testing.T) {
	random := rand.New(rand.NewSource(2))
	pool := MustParsePolicy("s:o:a", "s:o:a/*", "s:o:a/b", "s:o:a/b#1", "s:o:*", "s:p:a", "s:o:c", "t:o:a")
	randomPolicy := func() Policy {
		policy := Policy{}
		for _, permission := range pool {
			if random.Intn(2) == 0 {
				policy = policy.Add(permission)
			}
		}
		return policy
	}
	for range 5000 {
		first, second := randomPolicy(), randomPolicy()
		shared := first.Intersect(second)
		if !shared.Within(first) || !shared.Within(second) {
			t.Fatalf("intersect of %v and %v escaped: %v", first.Strings(), second.Strings(), shared.Strings())
		}
	}
}

func TestAddDoesNotAlias(t *testing.T) {
	base := make(Policy, 1, 4)
	base[0] = MustParse("fs:r:/a")
	first := base.Add(MustParse("fs:r:/b"))
	second := base.Add(MustParse("fs:r:/c"))
	if first[1].Resource != "/b" || second[1].Resource != "/c" {
		t.Fatalf("aliased: %v %v", first.Strings(), second.Strings())
	}
	if len(base.Add(MustParse("fs:r:/a"))) != 1 {
		t.Fatal("duplicate added")
	}
}

func TestKindViews(t *testing.T) {
	policy := MustParsePolicy("github:issue.read:a/b#1", "net:connect:x:443", "fs:r:/a", "exec:run:/bin/sh", "fs:w:/b")
	if len(policy.Capability()) != 1 || len(policy.Network()) != 1 || len(policy.Filesystem()) != 2 || len(policy.Executables()) != 1 {
		t.Fatalf("kind views wrong for %v", policy.Strings())
	}
}

func TestPolicyJSON(t *testing.T) {
	encoded, _ := json.Marshal(Policy{})
	if string(encoded) != "[]" {
		t.Fatalf("empty policy marshals as %s", encoded)
	}
	var decoded Policy
	if err := json.Unmarshal([]byte(`["fs:r:/a","exec:run:/bin/sh"]`), &decoded); err != nil || len(decoded) != 2 {
		t.Fatalf("unmarshal: %v %v", decoded, err)
	}
}
