package mbla

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func serveJSON(t *testing.T, reply string, inspect func(body map[string]any)) *httptest.Server {
	t.Helper()
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		var body map[string]any
		json.NewDecoder(request.Body).Decode(&body)
		if inspect != nil {
			inspect(body)
		}
		writer.Write([]byte(reply))
	}))
	t.Cleanup(server.Close)
	return server
}

var twoCandidates = MustParsePolicy("github:issue.read:acme/web#42", "net:connect:attacker.example:443")

func TestJevScore(t *testing.T) {
	reply := `{"model":"jev-1.13.0","answers":{"c0":{"noul":0.95},"c1":{"noul":0.02}},"usage":{"input_tokens":120}}`
	server := serveJSON(t, reply, func(body map[string]any) {
		questions := body["questions"].(map[string]any)
		if len(questions) != 2 || body["state"] == "" {
			t.Errorf("jev body: %v", body)
		}
	})
	jev := &SystemOne{Label: "jev", Endpoint: server.URL}
	scores, err := jev.Score(context.Background(), triageRequest, twoCandidates)
	if err != nil || scores[0] != 0.95 || scores[1] != 0.02 {
		t.Fatalf("scores %v err %v", scores, err)
	}
	if jev.LastCall().Version != "jev-1.13.0" || jev.LastCall().InputTokens != 120 {
		t.Fatalf("last call: %+v", jev.LastCall())
	}
}

func TestJevScoreUnwrapsResult(t *testing.T) {
	server := serveJSON(t, `{"result":{"model":"jev","answers":{"c0":{"noul":0.7},"c1":{"noul":0.1}}},"success":true}`, nil)
	scores, err := (&SystemOne{Label: "clm-zs", Endpoint: server.URL}).Score(context.Background(), triageRequest, twoCandidates)
	if err != nil || scores[0] != 0.7 {
		t.Fatalf("scores %v err %v", scores, err)
	}
}

func TestDecisionScore(t *testing.T) {
	server := serveJSON(t, `{"model":"clm-v0.1-8b","scores":[0.8,0.1]}`, nil)
	scores, err := (&DecisionModel{Label: "clm-zs", Endpoint: server.URL}).Score(context.Background(), triageRequest, twoCandidates)
	if err != nil || scores[0] != 0.8 {
		t.Fatalf("scores %v err %v", scores, err)
	}
}

func TestChatModelScore(t *testing.T) {
	reply := `{"model":"qwen3-8b","choices":[{"message":{"content":"{\"required\":[0],\"plausible\":[1,7]}"}}],"usage":{"prompt_tokens":300}}`
	server := serveJSON(t, reply, func(body map[string]any) {
		schema := body["response_format"].(map[string]any)["json_schema"].(map[string]any)["schema"].(map[string]any)
		required := schema["properties"].(map[string]any)["required"].(map[string]any)
		if required["maxItems"] != float64(2) || body["enable_thinking"] != false {
			t.Errorf("chat body: %v", body)
		}
	})
	chat := &ChatModel{Endpoint: server.URL, Model: "qwen3-8b", ExtraBody: map[string]any{"enable_thinking": false}}
	scores, err := chat.Score(context.Background(), triageRequest, twoCandidates)
	if err != nil || scores[0] != 1 || scores[1] != 0.5 {
		t.Fatalf("scores %v err %v", scores, err)
	}
}

func TestChatModelParseFailureScoresZero(t *testing.T) {
	server := serveJSON(t, `{"choices":[{"message":{"content":"not json"}}]}`, nil)
	chat := &ChatModel{Endpoint: server.URL}
	scores, err := chat.Score(context.Background(), triageRequest, twoCandidates)
	if err != nil || scores[0] != 0 || !chat.LastCall().ParseFailed || chat.LastCall().RawOutput != "not json" {
		t.Fatalf("scores %v err %v report %+v", scores, err, chat.LastCall())
	}
}

func TestRemoteErrorStatus(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, _ *http.Request) {
		writer.WriteHeader(http.StatusTooManyRequests)
	}))
	defer server.Close()
	if _, err := (&DecisionModel{Label: "clm-zs", Endpoint: server.URL}).Score(context.Background(), triageRequest, twoCandidates); err == nil {
		t.Fatal("want error on non-200 status")
	}
}
