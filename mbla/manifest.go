package mbla

import (
	"crypto/ed25519"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"
)

var ErrBadSignature = errors.New("manifest signature does not verify")

type Manifest struct {
	Receiver   string              `json:"receiver"`
	Version    int                 `json:"version"`
	Operations map[string][]string `json:"operations"`
}

func LoadManifest(manifestPath string, publicKey ed25519.PublicKey) (Manifest, error) {
	content, err := os.ReadFile(manifestPath)
	if err != nil {
		return Manifest{}, err
	}
	signature, err := os.ReadFile(manifestPath + ".sig")
	if err != nil {
		return Manifest{}, err
	}
	if !ed25519.Verify(publicKey, content, signature) {
		return Manifest{}, ErrBadSignature
	}
	var manifest Manifest
	err = json.Unmarshal(content, &manifest)
	return manifest, err
}

func (manifest Manifest) For(request Request) (Policy, error) {
	templates, found := manifest.Operations[request.Operation]
	if !found {
		return Policy{}, nil
	}
	filled := []string{}
	for _, template := range templates {
		text := fillPlaceholders(template, request.Arguments)
		if strings.Contains(text, "{") {
			return nil, fmt.Errorf("manifest %q: missing argument for %q", manifest.Receiver, template)
		}
		filled = append(filled, text)
	}
	return ParsePolicy(filled)
}

func fillPlaceholders(template string, arguments map[string]string) string {
	for key, value := range arguments {
		template = strings.ReplaceAll(template, "{"+key+"}", value)
	}
	return template
}
