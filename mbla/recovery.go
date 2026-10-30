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
	VolumeFinal
	OutsideCeiling
)

type RecoveryRequest struct {
	TaskID     string
	Permission Permission
}

// Recovery decides requests for one delegation. Ceiling is the receiver's ceiling for destinations; nil means the
// receiver is local and its ceiling is the delegator's holdings.
type Recovery struct {
	Holdings Policy
	Admit    Policy
	Ceiling  Policy
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
	case requested.Kind() == Filesystem:
		return VolumeFinal
	case !recovery.Holdings.Covers(requested):
		return OutsideParent
	case recovery.Ceiling != nil && requested.Kind() != Capability && !recovery.Ceiling.Covers(requested):
		return OutsideCeiling
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
	case VolumeFinal:
		return "volume-final"
	case OutsideCeiling:
		return "outside-ceiling"
	}
	return "unknown"
}

func NeedsNewSandbox(permission Permission) bool {
	return permission.Kind() != Capability
}
