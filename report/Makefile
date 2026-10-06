all: mbla_findings.pdf

mbla_findings.pdf: mbla_findings.tex generated/*.tex ../plots/out/*.pdf
	latexmk -pdf -interaction=nonstopmode -halt-on-error mbla_findings.tex

clean:
	latexmk -C

.PHONY: all clean
