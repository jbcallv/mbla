load "common.gp"
set output "out/inputs.pdf"
set title "Effect of what the model is shown"
set ylabel "share of unneeded permissions granted"
set xrange [-0.3:3.3]
set yrange [0:1]
set xtics ("task text" 0, "+ arguments" 1, "+ handoff history" 2, "+ operator list" 3)
set key top right
plot "data/inputs.dat" using 1:3 with linespoints pt 5 lc rgb generative_color title "qwen3-8b", \
     "" using 1:4 with linespoints pt 7 lc rgb decision_color title "qwen3-reranker-8b", \
     "" using 1:5 with linespoints pt 9 lc rgb "#e7298a" title "clm", \
     "" using 1:6 with linespoints pt 11 lc rgb "#66a61e" title "laya"
