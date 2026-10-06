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
	granted  int
}

func (recovery *Recovery) Decide(request RecoveryRequest) Decision {
	requested := request.Permission
	switch {
	case !requested.IsConcrete():
		return NotConcrete
	case recovery.granted >= recovery.Cap:
		return CapReached
	case !recovery.Holdings.Covers(requested):
		return OutsideParent
	case recovery.Mode == Admitted && !recovery.Admit.Covers(requested):
		return NotAdmitted
	}
	recovery.granted++
	return Granted
}

func (recovery *Recovery) Granted() int {
	return recovery.granted
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
