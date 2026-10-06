package mbla

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
)

const chatInstructions = `You choose the permissions a delegated agent needs for one task.
You get the delegated request and a numbered list of candidate permissions.
Return "required": the indices the task cannot complete without.
Return "plausible": other indices the task might reasonably need.
Leave out every other index.`

const maxOutputTokens = 1024

const decisionQuestion = "Is this permission required to complete the delegated task? Permission: "

type SystemOne struct {
	Label    string
	Endpoint string
	APIKey   string
	Glossary Glossary
	Client   *http.Client
	lastCall CallReport
}

type DecisionModel struct {
	Label    string
	Endpoint string
	Glossary Glossary
	Client   *http.Client
	lastCall CallReport
}

type ChatModel struct {
	Endpoint  string
	APIKey    string
	Model     string
	Seed      int
	ExtraBody map[string]any
	Glossary  Glossary
	Client    *http.Client
	lastCall  CallReport
}

type CallReport struct {
	Version     string
	InputTokens int
	ParseFailed bool
	RawOutput   string
}

func (systemOne *SystemOne) Name() string    { return systemOne.Label }
func (decision *DecisionModel) Name() string { return decision.Label }
func (chat *ChatModel) Name() string         { return chat.Model }

func (systemOne *SystemOne) LastCall() CallReport    { return systemOne.lastCall }
func (decision *DecisionModel) LastCall() CallReport { return decision.lastCall }
func (chat *ChatModel) LastCall() CallReport         { return chat.lastCall }

type systemOneQuestion struct {
	Type         string `json:"type"`
	Instructions string `json:"instructions"`
}

type systemOneResponse struct {
	Model   string                            `json:"model"`
	Answers map[string]struct{ Noul float64 } `json:"answers"`
	Usage   struct {
		InputTokens int `json:"input_tokens"`
	} `json:"usage"`
	Result *systemOneResponse `json:"result"`
}

func (systemOne *SystemOne) Score(ctx context.Context, request Request, candidates Policy) ([]float64, error) {
	questions := map[string]systemOneQuestion{}
	for index, candidate := range candidates {
		questions[questionKey(index)] = systemOneQuestion{Type: "noul", Instructions: decisionQuestion + DescribePermission(candidate, systemOne.Glossary)}
	}
	body := map[string]any{"state": Describe(request), "questions": questions}
	var response systemOneResponse
	if err := postJSON(ctx, systemOne.Client, systemOne.Endpoint, systemOne.APIKey, body, &response); err != nil {
		return nil, err
	}
	if response.Result != nil {
		response = *response.Result
	}
	systemOne.lastCall = CallReport{Version: response.Model, InputTokens: response.Usage.InputTokens}
	return systemOneScores(response, len(candidates))
}

func systemOneScores(response systemOneResponse, count int) ([]float64, error) {
	scores := make([]float64, count)
	for index := range scores {
		answer, found := response.Answers[questionKey(index)]
		if !found {
			return nil, fmt.Errorf("system one: missing answer %s", questionKey(index))
		}
		scores[index] = answer.Noul
	}
	return scores, nil
}

func questionKey(index int) string {
	return "c" + strconv.Itoa(index)
}

type decisionResponse struct {
	Model  string    `json:"model"`
	Scores []float64 `json:"scores"`
}

func (decision *DecisionModel) Score(ctx context.Context, request Request, candidates Policy) ([]float64, error) {
	body := map[string]any{"state": Describe(request), "candidates": describeAll(candidates, decision.Glossary)}
	var response decisionResponse
	if err := postJSON(ctx, decision.Client, decision.Endpoint+"/score", "", body, &response); err != nil {
		return nil, err
	}
	decision.lastCall = CallReport{Version: response.Model}
	return response.Scores, nil
}

type chatResponse struct {
	Model   string `json:"model"`
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
	Usage struct {
		PromptTokens int `json:"prompt_tokens"`
	} `json:"usage"`
}

type chatSelection struct {
	Required  []int `json:"required"`
	Plausible []int `json:"plausible"`
}

func (chat *ChatModel) Score(ctx context.Context, request Request, candidates Policy) ([]float64, error) {
	var response chatResponse
	if err := postJSON(ctx, chat.Client, chat.Endpoint+"/chat/completions", chat.APIKey, chat.requestBody(request, candidates), &response); err != nil {
		return nil, err
	}
	chat.lastCall = CallReport{Version: response.Model, InputTokens: response.Usage.PromptTokens}
	selection, err := parseSelection(response)
	if err != nil {
		chat.lastCall.ParseFailed = true
		chat.lastCall.RawOutput = rawContent(response)
		return make([]float64, len(candidates)), nil
	}
	return selectionScores(selection, len(candidates)), nil
}

func (chat *ChatModel) requestBody(request Request, candidates Policy) map[string]any {
	body := map[string]any{
		"model":       chat.Model,
		"temperature": 0,
		"seed":        chat.Seed,
		"max_tokens":  maxOutputTokens,
		"messages": []map[string]string{
			{"role": "system", "content": chatInstructions},
			{"role": "user", "content": chatPrompt(request, candidates, chat.Glossary)},
		},
		"response_format": selectionSchema(len(candidates)),
	}
	for key, value := range chat.ExtraBody {
		body[key] = value
	}
	return body
}

func chatPrompt(request Request, candidates Policy, glossary Glossary) string {
	prompt := "Delegated request:\n" + Describe(request) + "\nCandidate permissions:\n"
	for index, description := range describeAll(candidates, glossary) {
		prompt += fmt.Sprintf("%d. %s\n", index, description)
	}
	return prompt
}

func selectionSchema(candidateCount int) map[string]any {
	index := map[string]any{"type": "integer", "minimum": 0, "maximum": candidateCount - 1}
	indexList := map[string]any{"type": "array", "items": index, "maxItems": candidateCount}
	return map[string]any{
		"type": "json_schema",
		"json_schema": map[string]any{
			"name":   "permissions",
			"strict": true,
			"schema": map[string]any{
				"type":                 "object",
				"properties":           map[string]any{"required": indexList, "plausible": indexList},
				"required":             []string{"required", "plausible"},
				"additionalProperties": false,
			},
		},
	}
}

func rawContent(response chatResponse) string {
	if len(response.Choices) == 0 {
		return ""
	}
	return response.Choices[0].Message.Content
}

func parseSelection(response chatResponse) (chatSelection, error) {
	var selection chatSelection
	if len(response.Choices) == 0 {
		return selection, fmt.Errorf("no choices")
	}
	err := json.Unmarshal([]byte(response.Choices[0].Message.Content), &selection)
	return selection, err
}

func selectionScores(selection chatSelection, count int) []float64 {
	scores := make([]float64, count)
	for _, index := range selection.Plausible {
		if index >= 0 && index < count {
			scores[index] = 0.5
		}
	}
	for _, index := range selection.Required {
		if index >= 0 && index < count {
			scores[index] = 1
		}
	}
	return scores
}

func describeAll(candidates Policy, glossary Glossary) []string {
	descriptions := make([]string, len(candidates))
	for index, candidate := range candidates {
		descriptions[index] = DescribePermission(candidate, glossary)
	}
	return descriptions
}

func postJSON(ctx context.Context, client *http.Client, url, apiKey string, body any, response any) error {
	payload, err := json.Marshal(body)
	if err != nil {
		return err
	}
	httpRequest, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(payload))
	if err != nil {
		return err
	}
	httpRequest.Header.Set("Content-Type", "application/json")
	if apiKey != "" {
		httpRequest.Header.Set("Authorization", "Bearer "+apiKey)
	}
	return send(clientOrDefault(client), httpRequest, response)
}

func send(client *http.Client, httpRequest *http.Request, response any) error {
	httpResponse, err := client.Do(httpRequest)
	if err != nil {
		return err
	}
	defer httpResponse.Body.Close()
	if httpResponse.StatusCode != http.StatusOK {
		return fmt.Errorf("%s: status %d", httpRequest.URL, httpResponse.StatusCode)
	}
	return json.NewDecoder(httpResponse.Body).Decode(response)
}

func clientOrDefault(client *http.Client) *http.Client {
	if client == nil {
		return http.DefaultClient
	}
	return client
}
