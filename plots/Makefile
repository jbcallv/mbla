GNUPLOT ?= gnuplot
FIGURES := quality_latency recovery fortis inputs curves

all: $(FIGURES:%=out/%.pdf)

out/%.pdf: %.gp common.gp data/*.dat
	mkdir -p out
	$(GNUPLOT) $<

clean:
	rm -f out/*.pdf

.PHONY: all clean
