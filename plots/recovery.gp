load "common.gp"
set output "out/recovery.pdf"
set size ratio 0.45
set terminal pdfcairo enhanced font "Helvetica,9" size 6in,3.2in
set title "Attacks a compromised agent can still carry out by asking for more permissions"
set ylabel "share of planted attacks that succeed"
set yrange [0:1.1]
set style fill solid 0.85 border -1
set boxwidth 0.38
set xtics rotate by -40 left font ",8"
set key outside top center horizontal
plot "data/recovery.dat" using ($0-0.2):2:xtic(1) with boxes lc rgb paper_rule_color title "paper's rule: grant anything the parent holds", \
     "" using ($0+0.2):3 with boxes lc rgb our_rule_color title "our rule: grant only what the model rated plausible", \
     "" using ($0+0.2):3:4:5 with yerrorbars lc rgb "black" pt -1 notitle
