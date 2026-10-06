package mbla

import (
	"encoding/json"
	"math/rand"
	"testing"
)

func TestParseRoundTrip(t *testing.T) {
	texts := []string{
		"github:issue.read:acme/web#42",
		"net:connect:api.github.com:443",
		"fs:w:/workspace",
		"exec:run:/usr/bin/make",
		"github:issue.label:acme/web#42?label=bug",
		"storage:object.put:acme-staging/builds/*",
	}
	for _, text := range texts {
		if got := MustParse(text).String(); got != text {
			t.Errorf("round trip %q: got %q", text, got)
		}
	}
}

func TestParseRejectsMalformed(t *testing.T) {
	for _, text := range []string{"", "github", "github:issue.read", "github::acme", "fs:r:/a*/b"} {
		if _, err := Parse(text); err == nil {
			t.Errorf("parse %q: want error", text)
		}
	}
}

func TestKind(t *testing.T) {
	cases := map[string]Kind{
		"github:issue.read:acme/web#1": Capability,
		"net:connect:slack.com:443":    Network,
		"fs:r:/artifacts":              Filesystem,
		"exec:run:/usr/bin/curl":       Executable,
	}
	for text, want := range cases {
		if got := MustParse(text).Kind(); got != want {
			t.Errorf("kind %q: got %v want %v", text, got, want)
		}
	}
}

func TestCovers(t *testing.T) {
	cases := []struct {
		granted, requested string
		want               bool
	}{
		{"github:issue.read:acme/web#42", "github:issue.read:acme/web#42", true},
		{"github:issue.read:acme/web", "github:issue.read:acme/web#42", true},
		{"github:issue.read:acme/*", "github:issue.read:acme/web#42", true},
		{"github:issue.read:acme/web#4", "github:issue.read:acme/web#42", false},
		{"github:issue.read:acme/web", "github:issue.read:acme/webhooks", false},
		{"github:issue.read:acme/web#42", "github:issue.label:acme/web#42", false},
		{"github:*:acme/web", "github:issue.label:acme/web#42", true},
		{"github:issue.read:acme/web", "gitlab:issue.read:acme/web", false},
		{"fs:w:/workspace", "fs:w:/workspace/src", true},
		{"fs:w:/workspace", "fs:r:/workspace", false},
		{"fs:r:/work", "fs:r:/workspace", false},
		{"net:connect:api.github.com:443", "net:connect:api.github.com:4430", false},
		{"net:connect:*", "net:connect:attacker.example:443", true},
		{"github:issue.label:acme/web#1", "github:issue.label:acme/web#1?label=bug", true},
		{"github:issue.label:acme/web#1?label=bug", "github:issue.label:acme/web#1?label=wontfix", false},
		{"github:issue.label:acme/web#1?label=bug", "github:issue.label:acme/web#1", false},
		{"storage:object.put:acme-staging/builds/app.tar", "storage:object.put:acme-staging/builds/*", false},
	}
	for _, testCase := range cases {
		got := MustParse(testCase.granted).Covers(MustParse(testCase.requested))
		if got != testCase.want {
			t.Errorf("%q covers %q: got %v want %v", testCase.granted, testCase.requested, got, testCase.want)
		}
	}
}

func TestIsConcrete(t *testing.T) {
	if !MustParse("github:issue.read:acme/web#1").IsConcrete() {
		t.Error("concrete permission reported as pattern")
	}
	for _, text := range []string{"github:issue.read:acme/*", "github:*:acme/web"} {
		if MustParse(text).IsConcrete() {
			t.Errorf("%q reported as concrete", text)
		}
	}
}

func TestCoversIsReflexiveAndTransitive(t *testing.T) {
	random := rand.New(rand.NewSource(1))
	resources := []string{"a", "a/*", "a/b", "a/b*", "a/b#1", "a/bc", "a/b/c", "*", "a#1", "ab"}
	pick := func() Permission {
		return Permission{Service: "s", Operation: "o", Resource: resources[random.Intn(len(resources))]}
	}
	for range 20000 {
		first, second, third := pick(), pick(), pick()
		if !first.Covers(first) {
			t.Fatalf("not reflexive: %s", first)
		}
		if first.Covers(second) && second.Covers(third) && !first.Covers(third) {
			t.Fatalf("not transitive: %s, %s, %s", first, second, third)
		}
	}
}

func TestPermissionJSON(t *testing.T) {
	encoded, err := json.Marshal(MustParse("fs:r:/artifacts"))
	if err != nil || string(encoded) != `"fs:r:/artifacts"` {
		t.Fatalf("marshal: %s %v", encoded, err)
	}
	var decoded Permission
	if err := json.Unmarshal(encoded, &decoded); err != nil || decoded != MustParse("fs:r:/artifacts") {
		t.Fatalf("unmarshal: %v %v", decoded, err)
	}
}

func TestPermissionHelpers(t *testing.T) {
	if got := NetworkPermission("API.GitHub.com", 443).String(); got != "net:connect:api.github.com:443" {
		t.Errorf("network: %s", got)
	}
	if got := FilePermission("r", "/workspace/../secrets").String(); got != "fs:r:/secrets" {
		t.Errorf("file: %s", got)
	}
	if got := ExecPermission("/usr/bin/curl").String(); got != "exec:run:/usr/bin/curl" {
		t.Errorf("exec: %s", got)
	}
}
