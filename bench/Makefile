PYTHON := .venv/bin/python
GO ?= go
# set SHARED=--shared to run accuracy experiments next to other users' GPU jobs (latency then comes from e5 only)
SHARED ?=

.PHONY: all mbla data conversion label-sheets label-check label-compare review-sheets review-compare review-final freeze verify download conform dev tune e1 e3 e4 e5 fortis-data fortis judge judge-adjust report significance export figures test

all: mbla data conform dev tune e1 e3 e4 fortis e5 report significance export figures

mbla:
	cd ../mbla && $(GO) test ./... && $(GO) build -o bin/mbla ./cmd/mbla

SPLITS ?= dev
REVIEWERS ?= alvi,joseph

data:
	$(foreach split,$(SPLITS),$(PYTHON) -m mbla_bench.generate --split $(split) &&) true
	$(PYTHON) -m mbla_bench.validate

conversion:
	$(PYTHON) -m mbla_bench.conversion

# answer-key labeling (research/labeling_guide.md): blank sheets per reviewer, then agreement
label-sheets:
	$(PYTHON) -m mbla_bench.labels sheets --items data/tasks/$(SPLIT).jsonl --out-dir data/review/$(SPLIT) --reviewers $(REVIEWERS) $(if $(filter dev,$(SPLIT)),--carry,)

# after the keys are adjudicated: a random 10% of carried tasks for one reviewer to confirm
label-check:
	$(PYTHON) -m mbla_bench.labels carried-check --items data/tasks/$(SPLIT).jsonl --out-dir data/review/$(SPLIT)

label-compare:
	$(PYTHON) -m mbla_bench.labels compare --out-dir data/review/$(SPLIT) --reviewers $(REVIEWERS)

# pilot audit tools (pilot format, data/pilot)

review-sheets: mbla
	$(PYTHON) -m mbla_bench.review sheets --reviewers $(REVIEWERS)

review-compare:
	$(PYTHON) -m mbla_bench.review compare $(foreach name,$(REVIEWERS),data/review/audit_$(name).csv)

review-final:
	$(PYTHON) -m mbla_bench.review final

freeze:
	$(PYTHON) -m mbla_bench.validate --freeze

verify:
	$(PYTHON) -m mbla_bench.validate --verify

download:
	bash serve/download.sh

conform: mbla
	$(PYTHON) -m mbla_bench.conform
	cd ../mbla && $(GO) test -run xxx -bench CheckAttenuation -benchmem . | tee ../bench/results/tables/check_latency.txt

dev: mbla
	$(PYTHON) -m mbla_bench.orchestrate --experiments dev

tune:
	$(PYTHON) -m mbla_bench.tune

e1 e3 e4: mbla verify
	$(PYTHON) -m mbla_bench.orchestrate $(SHARED) --experiments $@

e5: mbla verify
	$(PYTHON) -m mbla_bench.orchestrate --experiments e5

fortis-data:
	$(PYTHON) -m mbla_bench.fortis build
	$(PYTHON) -m mbla_bench.validate --tasks data/external/fortis

fortis: mbla fortis-data
	$(PYTHON) -m mbla_bench.orchestrate $(SHARED) --experiments fortis1,fortis2
	$(PYTHON) -m mbla_bench.fortis report fortis1 data/external/fortis/task1.jsonl
	$(PYTHON) -m mbla_bench.fortis report fortis2 data/external/fortis/task2.jsonl

judge:
	$(PYTHON) -m mbla_bench.judge judge $(SHARED)

judge-adjust:
	$(PYTHON) -m mbla_bench.judge adjust

report:
	$(PYTHON) -m mbla_bench.report dev --items data/tasks/dev.jsonl
	$(PYTHON) -m mbla_bench.report e1
	$(PYTHON) -m mbla_bench.report e3
	$(PYTHON) -m mbla_bench.report e4

significance:
	$(PYTHON) -m mbla_bench.significance

export:
	$(PYTHON) -m mbla_bench.export

figures: export
	$(MAKE) -C ../plots
	$(MAKE) -C ../report

test:
	$(PYTHON) -m pytest -q tests
