# coverage against unneeded authority, final test; arrows from each plain helper to its fine-tuned version
set terminal cairolatex pdf size 7in,3.1in font ",8"
set output "figures/tradeoff.tex"
set xlabel "Unneeded authority granted (0 = none, 1 = everything the delegator holds)"
set ylabel "Tasks completed (\\%)" offset 1,0
set xrange [-0.14:1.1]
set xtics 0,0.2,1
set yrange [45:104]
set grid lc rgb "#e5e5e5"
set border 3
set lmargin 9
set tics nomirror
set key bottom right Left reverse samplen 1 spacing 1.2
plain = "#3b6fb6"; tuned = "#d4572a"; other = "#555555"
lx(c) = column(2) + 0.012 * column(4)
ly(c) = column(3) + 1.6 * column(5)
left(x) = strcol(6) eq "left" ? x : NaN
right(x) = strcol(6) eq "right" ? x : NaN
plot "data/tradeoff_arrows.dat" using 1:2:3:4 with vectors head size 0.012,20 filled lc rgb "#b0b0b0" lw 1 notitle, \
     "data/tradeoff_plain.dat" using 2:3 with points pt 7 ps 0.9 lc rgb plain title "Plain helper", \
     "data/tradeoff_tuned.dat" using 2:3 with points pt 7 ps 0.9 lc rgb tuned title "Same helper, fine-tuned", \
     "data/tradeoff_other.dat" using 2:3 with points pt 5 ps 0.8 lc rgb other title "Other methods", \
     for [f in "plain tuned other"] "data/tradeoff_".f.".dat" using (left(lx(0))):(ly(0)):1 with labels left font ",7" notitle, \
     for [f in "plain tuned other"] "data/tradeoff_".f.".dat" using (right(lx(0))):(ly(0)):1 with labels right font ",7" notitle
