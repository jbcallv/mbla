package mbla

import (
	"crypto/ed25519"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

const triageManifest = `{"receiver":"triage-agent","version":1,"operations":{"github.triage":["github:issue.read:{issue}","net:connect:api.github.com:443"]}}`

func writeSignedManifest(t *testing.T, signingKey ed25519.PrivateKey) string {
	t.Helper()
	manifestPath := filepath.Join(t.TempDir(), "manifest.json")
	os.WriteFile(manifestPath, []byte(triageManifest), 0o644)
	os.WriteFile(manifestPath+".sig", ed25519.Sign(signingKey, []byte(triageManifest)), 0o644)
	return manifestPath
}

func TestLoadManifestAndFill(t *testing.T) {
	publicKey, signingKey, _ := ed25519.GenerateKey(nil)
	manifest, err := LoadManifest(writeSignedManifest(t, signingKey), publicKey)
	if err != nil {
		t.Fatal(err)
	}
	policy, err := manifest.For(triageRequest)
	if err != nil || len(policy) != 2 || policy[0].String() != "github:issue.read:acme/web#42" {
		t.Fatalf("for: %v %v", policy.Strings(), err)
	}
}

func TestLoadManifestRejectsWrongKey(t *testing.T) {
	_, signingKey, _ := ed25519.GenerateKey(nil)
	otherKey, _, _ := ed25519.GenerateKey(nil)
	if _, err := LoadManifest(writeSignedManifest(t, signingKey), otherKey); !errors.Is(err, ErrBadSignature) {
		t.Fatalf("want bad signature, got %v", err)
	}
}

func TestManifestMissingArgument(t *testing.T) {
	manifest := Manifest{Operations: map[string][]string{"op": {"github:issue.read:{issue}"}}}
	if _, err := manifest.For(Request{Operation: "op"}); err == nil {
		t.Fatal("want error for missing argument")
	}
	if policy, err := manifest.For(Request{Operation: "other"}); err != nil || len(policy) != 0 {
		t.Fatalf("unknown operation: %v %v", policy, err)
	}
}
