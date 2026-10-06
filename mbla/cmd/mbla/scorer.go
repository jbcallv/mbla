package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/jbcallv/mbla/mbla"
)

type scorerConfig struct {
	name         string
	endpoint     string
	model        string
	seed         int
	glossaryPath string
	extraBody    string
	timeout      time.Duration
}

func addScorerFlags(flags *flag.FlagSet) *scorerConfig {
	config := &scorerConfig{}
	flags.StringVar(&config.name, "scorer", "set-only", "set-only | manifest-only | lexical | systemone | decision | chat")
	flags.StringVar(&config.endpoint, "endpoint", "", "model endpoint url")
	flags.StringVar(&config.model, "model", "", "model name (chat) or label (systemone, decision)")
	flags.IntVar(&config.seed, "seed", 0, "sampling seed for chat scorers")
	flags.StringVar(&config.glossaryPath, "glossary", "", "universe.json with permission descriptions")
	flags.StringVar(&config.extraBody, "extra", "", "json object merged into chat request bodies")
	flags.DurationVar(&config.timeout, "timeout", 120*time.Second, "per-request timeout")
	return config
}

func newScorer(config scorerConfig) (mbla.Scorer, error) {
	glossary, err := loadGlossary(config.glossaryPath)
	if err != nil {
		return nil, err
	}
	client := &http.Client{Timeout: config.timeout}
	apiKey := os.Getenv("MBLA_API_KEY")
	switch config.name {
	case "set-only":
		return mbla.SetOnly{}, nil
	case "manifest-only":
		return mbla.ManifestOnly{}, nil
	case "lexical":
		return mbla.Lexical{}, nil
	case "systemone":
		return &mbla.SystemOne{Label: config.model, Endpoint: config.endpoint, APIKey: apiKey, Glossary: glossary, Client: client}, nil
	case "decision":
		return &mbla.DecisionModel{Label: config.model, Endpoint: config.endpoint, Glossary: glossary, Client: client}, nil
	case "chat":
		return newChatModel(config, apiKey, glossary, client)
	}
	return nil, fmt.Errorf("unknown scorer %q", config.name)
}

func newChatModel(config scorerConfig, apiKey string, glossary mbla.Glossary, client *http.Client) (mbla.Scorer, error) {
	extraBody := map[string]any{}
	if config.extraBody != "" {
		if err := json.Unmarshal([]byte(config.extraBody), &extraBody); err != nil {
			return nil, fmt.Errorf("-extra: %w", err)
		}
	}
	return &mbla.ChatModel{
		Endpoint:  config.endpoint,
		APIKey:    apiKey,
		Model:     config.model,
		Seed:      config.seed,
		ExtraBody: extraBody,
		Glossary:  glossary,
		Client:    client,
	}, nil
}

type universeFile struct {
	Operations []struct {
		Service     string `json:"service"`
		Operation   string `json:"operation"`
		Description string `json:"description"`
	} `json:"operations"`
}

func loadGlossary(universePath string) (mbla.Glossary, error) {
	glossary := mbla.Glossary{}
	if universePath == "" {
		return glossary, nil
	}
	var universe universeFile
	if err := readJSON(universePath, &universe); err != nil {
		return nil, err
	}
	for _, entry := range universe.Operations {
		glossary[entry.Service+":"+entry.Operation] = entry.Description
	}
	return glossary, nil
}
