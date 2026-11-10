# share of tasks where the attack's target permission is reachable, by search budget
set terminal cairolatex pdf size 4in,2.1in font ",8"
set output "figures/budget.tex"
set xlabel "Attack text (search attempts)"
set ylabel "Target reachable (\\%)"
set yrange [0:100]
set xrange [-0.4:6.4]
set grid ytics lc rgb "#e5e5e5"
set border 3
set lmargin 8
set tics nomirror
set key bottom right samplen 2
plot "data/budget.dat" using 1:4:xtic(2) with linespoints pt 7 ps 0.7 lw 2 lc rgb "#d4572a" title "Final test", \
     "" using 1:3 with linespoints pt 6 ps 0.7 lw 1.5 dt 2 lc rgb "#555555" title "Practice set"
