load "common.gp"
set output "out/curves.pdf"
set title "Operating curves (E2): sweeping the initial threshold"
set xlabel "excess capability authority (EAC)"
set ylabel "missing capability authority (MAC)"
set xrange [0:1]
set yrange [0:1]
set key top right
plot "data/curve_qwen3-8b.dat" using 2:3 with linespoints pt 5 ps 0.5 lc rgb generative_color title "qwen3-8b", \
     "data/curve_qwen3-32b-awq.dat" using 2:3 with linespoints pt 4 ps 0.5 lc rgb "#4b3f9e" title "qwen3-32b", \
     "data/curve_gpt-oss-120b.dat" using 2:3 with linespoints pt 6 ps 0.5 lc rgb "#a6761d" title "gpt-oss-120b", \
     "data/curve_qwen3-reranker-8b.dat" using 2:3 with linespoints pt 7 ps 0.5 lc rgb decision_color title "qwen3-reranker-8b", \
     "data/curve_clm-zs.dat" using 2:3 with linespoints pt 9 ps 0.5 lc rgb "#e7298a" title "clm", \
     "data/curve_laya.dat" using 2:3 with linespoints pt 11 ps 0.5 lc rgb "#66a61e" title "laya"
