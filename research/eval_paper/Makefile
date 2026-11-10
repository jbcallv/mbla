# final evaluation report: data from the result tables, gnuplot figures, then the PDF
GNUPLOT ?= /scratch/jbcall/envs/gnuplot/bin/gnuplot
FIGURES = figures/tradeoff.tex figures/budget.tex figures/reach.tex

main.pdf: main.tex $(FIGURES)
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

data: ../../bench/mbla_bench/paper_data.py
	cd ../../bench && .venv/bin/python -m mbla_bench.paper_data ../research/eval_paper/data

figures/%.tex: figures/%.gp data/*.dat
	$(GNUPLOT) $<

clean:
	latexmk -C main.tex

.PHONY: data clean
