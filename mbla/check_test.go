package mbla

import (
	"errors"
	"testing"
)

func TestCheckAttenuation(t *testing.T) {
	parent := MustParsePolicy("github:issue.read:acme/*", "net:connect:api.github.com:443")
	if err := CheckAttenuation(MustParsePolicy("github:issue.read:acme/web#1"), parent); err != nil {
		t.Fatalf("valid child rejected: %v", err)
	}
	err := CheckAttenuation(MustParsePolicy("github:contents.read:acme/secrets"), parent)
	if !errors.Is(err, ErrExceedsParent) {
		t.Fatalf("widened child accepted: %v", err)
	}
}

func TestApplyCeiling(t *testing.T) {
	proposal := MustParsePolicy("github:issue.read:acme/web#1", "fs:r:/secrets", "net:connect:api.github.com:443")
	ceiling := MustParsePolicy("github:*:acme/*", "net:connect:api.github.com:443", "fs:w:/workspace")
	installed, dropped := ApplyCeiling(proposal, ceiling)
	if !installed.Within(ceiling) || !installed.Within(proposal) {
		t.Fatalf("installed escaped a bound: %v", installed.Strings())
	}
	if len(installed) != 2 || len(dropped) != 1 || dropped[0].String() != "fs:r:/secrets" {
		t.Fatalf("installed %v dropped %v", installed.Strings(), dropped.Strings())
	}
}

func TestBoundIsWithinBothSides(t *testing.T) {
	parent := MustParsePolicy("storage:object.put:acme-staging/*", "storage:object.put:acme-prod/*", "fs:r:/artifacts")
	ceiling := MustParsePolicy("storage:object.put:acme-staging/builds/*", "fs:r:/artifacts", "fs:r:/secrets")
	bound := Bound(parent, ceiling)
	if !bound.Within(parent) || !bound.Within(ceiling) {
		t.Fatalf("bound escaped: %v", bound.Strings())
	}
	if bound.Covers(MustParse("storage:object.put:acme-prod/app.tar")) {
		t.Fatal("bound covers production")
	}
}
