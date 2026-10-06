package mbla

import "testing"

func recoveryFor(mode Mode, cap int) *Recovery {
	return &Recovery{
		Holdings: MustParsePolicy("github:issue.read:acme/*", "github:contents.read:acme/*", "net:connect:api.github.com:443"),
		Admit:    MustParsePolicy("github:issue.read:acme/web#42", "net:connect:api.github.com:443"),
		Mode:     mode,
		Cap:      cap,
	}
}

func ask(recovery *Recovery, text string) Decision {
	return recovery.Decide(RecoveryRequest{TaskID: "task", Permission: MustParse(text)})
}

func TestDecideBoundOnlyGrantsAttackInsideHoldings(t *testing.T) {
	recovery := recoveryFor(BoundOnly, 5)
	if got := ask(recovery, "github:contents.read:acme/secrets"); got != Granted {
		t.Fatalf("bound-only: got %v", got)
	}
}

func TestDecideAdmittedRefusesAttackInsideHoldings(t *testing.T) {
	recovery := recoveryFor(Admitted, 5)
	if got := ask(recovery, "github:contents.read:acme/secrets"); got != NotAdmitted {
		t.Fatalf("admitted: got %v", got)
	}
	if got := ask(recovery, "github:issue.read:acme/web#42"); got != Granted {
		t.Fatalf("admitted legitimate: got %v", got)
	}
}

func TestDecideRefusals(t *testing.T) {
	cases := []struct {
		text string
		want Decision
	}{
		{"github:issue.read:acme/*", NotConcrete},
		{"github:issue.read:globex/site#1", OutsideParent},
		{"net:connect:attacker.example:443", OutsideParent},
	}
	for _, testCase := range cases {
		if got := ask(recoveryFor(BoundOnly, 5), testCase.text); got != testCase.want {
			t.Errorf("%s: got %v want %v", testCase.text, got, testCase.want)
		}
	}
}

func TestDecideCap(t *testing.T) {
	recovery := recoveryFor(BoundOnly, 1)
	if got := ask(recovery, "github:issue.read:acme/web#1"); got != Granted {
		t.Fatalf("first: got %v", got)
	}
	if got := ask(recovery, "github:issue.read:acme/web#2"); got != CapReached {
		t.Fatalf("second: got %v", got)
	}
	if recovery.Granted() != 1 {
		t.Fatalf("granted count %d", recovery.Granted())
	}
}

func TestZeroRecoveryFailsClosed(t *testing.T) {
	var recovery Recovery
	if got := ask(&recovery, "github:issue.read:acme/web#1"); got == Granted {
		t.Fatal("zero-value recovery granted a request")
	}
}

func TestNeedsNewSandbox(t *testing.T) {
	if NeedsNewSandbox(MustParse("github:issue.read:a/b#1")) {
		t.Error("capability should not need a new sandbox")
	}
	for _, text := range []string{"net:connect:x:443", "fs:r:/a", "exec:run:/bin/sh"} {
		if !NeedsNewSandbox(MustParse(text)) {
			t.Errorf("%s should need a new sandbox", text)
		}
	}
}
