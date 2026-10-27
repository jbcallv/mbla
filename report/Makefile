all: mbla_findings.pdf methodology.pdf methodology_ml.pdf

mbla_findings.pdf: mbla_findings.tex generated/*.tex ../plots/out/*.pdf
	latexmk -pdf -interaction=nonstopmode -halt-on-error mbla_findings.tex

methodology.pdf: methodology.tex
	latexmk -pdf -interaction=nonstopmode -halt-on-error methodology.tex

methodology_ml.pdf: methodology_ml.tex
	latexmk -pdf -interaction=nonstopmode -halt-on-error methodology_ml.tex

clean:
	latexmk -C

.PHONY: all clean
