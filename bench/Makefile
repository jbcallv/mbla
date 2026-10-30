PYTHON := .venv/bin/python
GO ?= go
# set SHARED=--shared to run accuracy experiments next to other users' GPU jobs (latency then comes from the latency experiment only)
SHARED ?=

.PHONY: all mbla data conversion label-sheets label-check label-compare attack-data freeze verify download conform dev tune final latency fortis-data fortis report test

all: mbla data conform dev tune final fortis latency report

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

attack-data:
	$(PYTHON) -m mbla_bench.attacks --items data/tasks/dev.jsonl --out data/attacks/dev_manifest.jsonl
	$(PYTHON) -m mbla_bench.attacks --items data/tasks/test.jsonl --out data/attacks/test_manifest.jsonl

# final runs: refused unless the final test set is frozen (make freeze after labeling)
final: mbla verify
	$(PYTHON) -m mbla_bench.orchestrate $(SHARED) --experiments final,final-manifest

latency: mbla verify
	$(PYTHON) -m mbla_bench.orchestrate --experiments latency

fortis-data:
	$(PYTHON) -m mbla_bench.fortis build
	$(PYTHON) -m mbla_bench.validate --tasks data/external/fortis

fortis: mbla fortis-data
	$(PYTHON) -m mbla_bench.orchestrate $(SHARED) --experiments fortis1,fortis2
	$(PYTHON) -m mbla_bench.fortis report fortis1 data/external/fortis/task1.jsonl
	$(PYTHON) -m mbla_bench.fortis report fortis2 data/external/fortis/task2.jsonl

EXPERIMENT ?= dev

report:
	$(PYTHON) -m mbla_bench.report $(EXPERIMENT)
	$(PYTHON) -m mbla_bench.analysis --final $(EXPERIMENT)

test:
	$(PYTHON) -m pytest -q tests
