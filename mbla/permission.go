package mbla

import (
	"encoding/json"
	"fmt"
	"path"
	"strconv"
	"strings"
)

type Kind int

const (
	Capability Kind = iota
	Network
	Filesystem
	Executable
)

type Permission struct {
	Service   string
	Operation string
	Resource  string
	Qualifier string
}

func Parse(text string) (Permission, error) {
	parts := strings.SplitN(text, ":", 3)
	if len(parts) != 3 || parts[0] == "" || parts[1] == "" || parts[2] == "" {
		return Permission{}, fmt.Errorf("permission %q: want service:operation:resource", text)
	}
	resource, qualifier, _ := strings.Cut(parts[2], "?")
	if strings.Contains(strings.TrimSuffix(resource, "*"), "*") {
		return Permission{}, fmt.Errorf("permission %q: wildcard only allowed at the end", text)
	}
	return Permission{Service: parts[0], Operation: parts[1], Resource: resource, Qualifier: qualifier}, nil
}

func MustParse(text string) Permission {
	permission, err := Parse(text)
	if err != nil {
		panic(err)
	}
	return permission
}

func (permission Permission) String() string {
	text := permission.Service + ":" + permission.Operation + ":" + permission.Resource
	if permission.Qualifier != "" {
		text += "?" + permission.Qualifier
	}
	return text
}

func (permission Permission) Kind() Kind {
	switch permission.Service {
	case "net":
		return Network
	case "fs":
		return Filesystem
	case "exec":
		return Executable
	}
	return Capability
}

func (permission Permission) IsConcrete() bool {
	return !strings.Contains(permission.Operation, "*") && !strings.Contains(permission.Resource, "*")
}

func (permission Permission) Covers(requested Permission) bool {
	return permission.Service == requested.Service &&
		operationCovers(permission.Operation, requested.Operation) &&
		resourceCovers(permission.Resource, requested.Resource) &&
		qualifierCovers(permission.Qualifier, requested.Qualifier)
}

func operationCovers(granted, requested string) bool {
	return granted == "*" || granted == requested
}

func resourceCovers(granted, requested string) bool {
	if granted == requested {
		return true
	}
	if prefix, isWildcard := strings.CutSuffix(granted, "*"); isWildcard {
		return strings.HasPrefix(requested, prefix)
	}
	return strings.HasPrefix(requested, granted+"/") || strings.HasPrefix(requested, granted+"#")
}

func qualifierCovers(granted, requested string) bool {
	return granted == "" || granted == requested
}

func (permission Permission) MarshalJSON() ([]byte, error) {
	return json.Marshal(permission.String())
}

func (permission *Permission) UnmarshalJSON(data []byte) error {
	var text string
	if err := json.Unmarshal(data, &text); err != nil {
		return err
	}
	parsed, err := Parse(text)
	if err != nil {
		return err
	}
	*permission = parsed
	return nil
}

func NetworkPermission(host string, port int) Permission {
	return Permission{Service: "net", Operation: "connect", Resource: strings.ToLower(host) + ":" + strconv.Itoa(port)}
}

func FilePermission(operation, filePath string) Permission {
	return Permission{Service: "fs", Operation: operation, Resource: path.Clean("/" + filePath)}
}

func ExecPermission(binaryPath string) Permission {
	return Permission{Service: "exec", Operation: "run", Resource: path.Clean("/" + binaryPath)}
}
