load "common.gp"
set output "out/fortis.pdf"
set terminal pdfcairo enhanced font "Helvetica,9" size 6in,3.2in
set title "FORTIS (an outside benchmark): how often the choice was exactly right"
set ylabel "share of tasks exactly right"
set yrange [0:0.6]
set style fill solid 0.85 border -1
set boxwidth 0.38
set xtics rotate by -40 left font ",8"
set key outside top center horizontal
plot "data/fortis.dat" using ($0-0.2):2:xtic(1) with boxes lc rgb generative_color title "choosing one skill", \
     "" using ($0+0.2):4 with boxes lc rgb decision_color title "choosing a set of tools"
