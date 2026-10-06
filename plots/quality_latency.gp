load "common.gp"
set output "out/quality_latency.pdf"
set title "Excess API permissions vs latency (E1 test quality, E5 exclusive-GPU latency)"
set logscale x
set xlabel "median latency per delegation (ms, log scale)"
set ylabel "excess capability authority (EAC, lower is better)"
set yrange [0:1]
set offsets graph 0.05, graph 0.15, 0, 0
plot "data/quality_latency.dat" using ($3):(strcol(2) eq "decision" ? $5 : NaN) with points pt 7 ps 0.8 lc rgb decision_color title "decision models", \
     "" using ($3):(strcol(2) eq "generative" ? $5 : NaN) with points pt 5 ps 0.8 lc rgb generative_color title "generative LLMs", \
     "" using ($3):5:1 with labels offset 0.6,0.5 left font ",7" notitle
