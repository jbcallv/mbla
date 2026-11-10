# attack reach on attacked tasks: backups from the helper's list vs from anything the delegator holds
set terminal cairolatex pdf size 4in,2.1in font ",8"
set output "figures/reach.tex"
set ylabel "Target reachable (\\%)"
set yrange [0:100]
set style data histogram
set style histogram clustered gap 1.4
set style fill solid 0.9 border -1
set boxwidth 0.9
set grid ytics lc rgb "#e5e5e5"
set border 3
set tics nomirror
set xtics scale 0
set key outside top center horizontal samplen 1 width 3 maxrows 1
set lmargin 8
plot "data/reach.dat" using 2:xtic(1) lc rgb "#3b6fb6" title "Backups: helper's list", \
     "" using 3 lc rgb "#bbbbbb" title "Backups: anything held"
