package mbla

type Mode int

const (
	BoundOnly Mode = iota
	Admitted
)

type Decision int

const (
	Granted Decision = iota
	NotConcrete
	CapReached
	OutsideParent
	NotAdmitted
)

type RecoveryRequest struct {
	TaskID     string
	Permission Permission
}

type Recovery struct {
	Holdings Policy
	Admit    Policy
	Mode     Mode
	Cap      int
	asked    int
}

// Decide counts every request against the cap, granted or not, so repeated denied requests cannot probe Admit.
func (recovery *Recovery) Decide(request RecoveryRequest) Decision {
	requested := request.Permission
	if recovery.asked >= recovery.Cap {
		return CapReached
	}
	recovery.asked++
	switch {
	case !requested.IsConcrete():
		return NotConcrete
	case !recovery.Holdings.Covers(requested):
		return OutsideParent
	case recovery.Mode == Admitted && !recovery.Admit.Covers(requested):
		return NotAdmitted
	}
	return Granted
}

func (recovery *Recovery) Asked() int {
	return recovery.asked
}

func (decision Decision) String() string {
	switch decision {
	case Granted:
		return "granted"
	case NotConcrete:
		return "not-concrete"
	case CapReached:
		return "cap-reached"
	case OutsideParent:
		return "outside-parent"
	case NotAdmitted:
		return "not-admitted"
	}
	return "unknown"
}

func NeedsNewSandbox(permission Permission) bool {
	return permission.Kind() != Capability
}
