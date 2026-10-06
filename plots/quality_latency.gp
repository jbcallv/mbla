load "common.gp"
set output "out/quality_latency.pdf"
set title "Unneeded permissions granted vs. time to decide"
set logscale x
set xlabel "time to decide the permissions for one task (milliseconds, log scale)"
set ylabel "share of unneeded permissions granted (lower is better)"
set yrange [0:1]
set offsets graph 0.05, graph 0.15, 0, 0
plot "data/quality_latency.dat" using ($3):(strcol(2) eq "decision" ? $5 : NaN) with points pt 7 ps 0.8 lc rgb decision_color title "yes/no scorers", \
     "" using ($3):(strcol(2) eq "generative" ? $5 : NaN) with points pt 5 ps 0.8 lc rgb generative_color title "LLMs", \
     "" using ($3):5:1 with labels offset 0.6,0.5 left font ",7" notitle
