package main

import (
	"bufio"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/jbcallv/mbla/mbla"
)

const usage = `usage:
  mbla check   -child child.json -parent parent.json
  mbla check   -pairs pairs.jsonl
  mbla propose -request request.json -holdings holdings.json -scorer NAME [scorer flags]
  mbla bench   -items items.jsonl -out predictions.jsonl -scorer NAME [scorer flags]`

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, usage)
		os.Exit(2)
	}
	commands := map[string]func([]string) error{"check": runCheck, "propose": runPropose, "bench": runBench}
	command, known := commands[os.Args[1]]
	if !known {
		fmt.Fprintln(os.Stderr, usage)
		os.Exit(2)
	}
	if err := command(os.Args[2:]); err != nil {
		fmt.Fprintln(os.Stderr, "mbla:", err)
		os.Exit(1)
	}
}

func runCheck(arguments []string) error {
	flags := flag.NewFlagSet("check", flag.ExitOnError)
	childPath := flags.String("child", "", "child policy json")
	parentPath := flags.String("parent", "", "parent policy json")
	pairsPath := flags.String("pairs", "", "jsonl of {child, parent} pairs")
	flags.Parse(arguments)
	if *pairsPath != "" {
		return checkPairs(*pairsPath)
	}
	var child, parent mbla.Policy
	if err := readJSON(*childPath, &child); err != nil {
		return err
	}
	if err := readJSON(*parentPath, &parent); err != nil {
		return err
	}
	return mbla.CheckAttenuation(child, parent)
}

type policyPair struct {
	Child  mbla.Policy `json:"child"`
	Parent mbla.Policy `json:"parent"`
}

type checkResult struct {
	Accepted  bool   `json:"accepted"`
	Violation string `json:"violation"`
}

func checkPairs(pairsPath string) error {
	file, err := os.Open(pairsPath)
	if err != nil {
		return err
	}
	defer file.Close()
	output := json.NewEncoder(os.Stdout)
	lines := bufio.NewScanner(file)
	lines.Buffer(make([]byte, 1<<20), 1<<24)
	for lines.Scan() {
		var pair policyPair
		if err := json.Unmarshal(lines.Bytes(), &pair); err != nil {
			return err
		}
		output.Encode(checkPair(pair))
	}
	return lines.Err()
}

func checkPair(pair policyPair) checkResult {
	if err := mbla.CheckAttenuation(pair.Child, pair.Parent); err != nil {
		return checkResult{Violation: err.Error()}
	}
	return checkResult{Accepted: true}
}

func runPropose(arguments []string) error {
	flags := flag.NewFlagSet("propose", flag.ExitOnError)
	requestPath := flags.String("request", "", "request json")
	holdingsPath := flags.String("holdings", "", "holdings policy json")
	thresholds := addThresholdFlags(flags)
	scorerConfig := addScorerFlags(flags)
	flags.Parse(arguments)
	scorer, err := newScorer(*scorerConfig)
	if err != nil {
		return err
	}
	var request mbla.Request
	var holdings mbla.Policy
	if err := readJSON(*requestPath, &request); err != nil {
		return err
	}
	if err := readJSON(*holdingsPath, &holdings); err != nil {
		return err
	}
	proposal, err := mbla.Propose(context.Background(), scorer, request, holdings, *thresholds)
	if err != nil {
		return err
	}
	return json.NewEncoder(os.Stdout).Encode(proposal)
}

func addThresholdFlags(flags *flag.FlagSet) *mbla.Thresholds {
	thresholds := &mbla.Thresholds{}
	flags.Float64Var(&thresholds.Initial, "initial", 0.8, "score needed for the initial grant")
	flags.Float64Var(&thresholds.Admit, "admit", 0.2, "score needed for recovery admission")
	return thresholds
}

func readJSON(filePath string, target any) error {
	content, err := os.ReadFile(filePath)
	if err != nil {
		return err
	}
	if err := json.Unmarshal(content, target); err != nil {
		return fmt.Errorf("%s: %w", filePath, err)
	}
	return nil
}
