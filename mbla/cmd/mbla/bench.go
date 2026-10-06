package main

import (
	"bufio"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"time"

	"github.com/jbcallv/mbla/mbla"
)

type benchItem struct {
	ID      string       `json:"id"`
	Request mbla.Request `json:"request"`
	Parent  mbla.Policy  `json:"parent"`
}

type benchRow struct {
	Item         string      `json:"item"`
	Method       string      `json:"method"`
	Input        string      `json:"input"`
	Seed         int         `json:"seed"`
	Candidates   mbla.Policy `json:"candidates"`
	Scores       []float64   `json:"scores"`
	Initial      mbla.Policy `json:"initial"`
	Admit        mbla.Policy `json:"admit"`
	Thresholds   [2]float64  `json:"thresholds"`
	LatencyMS    float64     `json:"latency_ms"`
	InputTokens  int         `json:"input_tokens"`
	ModelVersion string      `json:"model_version"`
	ParseFailed  bool        `json:"parse_failed"`
	RawOutput    string      `json:"raw_output,omitempty"`
	Error        string      `json:"error"`
	Hardware     string      `json:"hardware"`
}

type benchConfig struct {
	itemsPath  string
	outputPath string
	method     string
	input      string
	warmup     int
	hardware   string
	thresholds *mbla.Thresholds
	scorer     *scorerConfig
}

type callReporter interface {
	LastCall() mbla.CallReport
}

func runBench(arguments []string) error {
	flags := flag.NewFlagSet("bench", flag.ExitOnError)
	config := benchConfig{thresholds: addThresholdFlags(flags), scorer: addScorerFlags(flags)}
	flags.StringVar(&config.itemsPath, "items", "", "benchmark items jsonl")
	flags.StringVar(&config.outputPath, "out", "", "predictions jsonl to write")
	flags.StringVar(&config.method, "method", "", "method label (defaults to scorer name)")
	flags.StringVar(&config.input, "input", "full", "text | args | history | full")
	flags.IntVar(&config.warmup, "warmup", 5, "untimed calls before measuring")
	flags.StringVar(&config.hardware, "hardware", "", "hardware label recorded with each row")
	flags.Parse(arguments)
	return bench(config)
}

func bench(config benchConfig) error {
	scorer, err := newScorer(*config.scorer)
	if err != nil {
		return err
	}
	items, err := readItems(config.itemsPath)
	if err != nil {
		return err
	}
	output, err := os.Create(config.outputPath)
	if err != nil {
		return err
	}
	defer output.Close()
	warmUp(scorer, items, config)
	encoder := json.NewEncoder(output)
	for _, item := range items {
		if err := encoder.Encode(benchOne(scorer, item, config)); err != nil {
			return err
		}
	}
	return nil
}

func warmUp(scorer mbla.Scorer, items []benchItem, config benchConfig) {
	if len(items) == 0 {
		return
	}
	for range config.warmup {
		benchOne(scorer, items[0], config)
	}
}

func benchOne(scorer mbla.Scorer, item benchItem, config benchConfig) benchRow {
	candidates := mbla.Candidates(item.Request, item.Parent)
	row := newRow(scorer, item, candidates, config)
	started := time.Now()
	proposal, err := mbla.ProposeAmong(context.Background(), scorer, forInput(item.Request, config.input), candidates, *config.thresholds)
	row.LatencyMS = float64(time.Since(started).Microseconds()) / 1000
	if err != nil {
		row.Error = err.Error()
		return row
	}
	row.Scores, row.Initial, row.Admit = proposal.Scores, proposal.Initial, proposal.Admit
	recordCall(&row, scorer)
	return row
}

func newRow(scorer mbla.Scorer, item benchItem, candidates mbla.Policy, config benchConfig) benchRow {
	method := config.method
	if method == "" {
		method = scorer.Name()
	}
	return benchRow{
		Item:       item.ID,
		Method:     method,
		Input:      config.input,
		Seed:       config.scorer.seed,
		Candidates: candidates,
		Scores:     make([]float64, len(candidates)),
		Initial:    mbla.Policy{},
		Admit:      mbla.Policy{},
		Thresholds: [2]float64{config.thresholds.Initial, config.thresholds.Admit},
		Hardware:   config.hardware,
	}
}

func recordCall(row *benchRow, scorer mbla.Scorer) {
	reporter, reports := scorer.(callReporter)
	if !reports {
		return
	}
	call := reporter.LastCall()
	row.ModelVersion, row.InputTokens, row.ParseFailed, row.RawOutput = call.Version, call.InputTokens, call.ParseFailed, call.RawOutput
}

func forInput(request mbla.Request, input string) mbla.Request {
	scored := request
	switch input {
	case "text":
		scored.Arguments, scored.History, scored.Manifest = nil, nil, nil
	case "args":
		scored.History, scored.Manifest = nil, nil
	case "history":
		scored.Manifest = nil
	}
	return scored
}

func readItems(itemsPath string) ([]benchItem, error) {
	file, err := os.Open(itemsPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	items := []benchItem{}
	lines := bufio.NewScanner(file)
	lines.Buffer(make([]byte, 1<<20), 1<<24)
	for lines.Scan() {
		var item benchItem
		if err := json.Unmarshal(lines.Bytes(), &item); err != nil {
			return nil, fmt.Errorf("%s: %w", itemsPath, err)
		}
		items = append(items, item)
	}
	return items, lines.Err()
}
