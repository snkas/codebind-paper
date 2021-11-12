###  Released under the MIT License (MIT) --- see ./MIT_LICENSE
###  Copyright (c) 2020  Simon Kassing
###  Copyright (c) 2014  Ankit Singla, Sangeetha Abdu Jyothi, Chi-Yao Hong,
###                      Lucian Popa, P. Brighten Godfrey, Alexandra Koll

#####################################
### STYLING

# Terminal (gnuplot 4.4+)
set terminal pdfcairo font "Helvetica, 24" linewidth 1.5 rounded dashed

# Line style for axes
set style line 80 lt rgb "#808080"

# Line style for grid
set style line 81 lt 0  # Dashed
set style line 81 lt rgb "#999999"  # Grey grid

# Grey grid and border
set grid back linestyle 81
set border 3 back linestyle 80
set xtics nomirror
set ytics nomirror

# Line styles
set style line 1 lt rgb "#1F77B4" lw 2 pt 0 ps 0 dt 2
set style line 2 lt rgb "#FF7F0E" lw 2 pt 0 ps 0 dt 3
set style line 3 lt rgb "#2CA02C" lw 2 pt 0 ps 0 dt 1
set style line 4 lt rgb "#D62728" lw 2 pt 0 ps 0 dt 4

# Output
set output "[OUTPUT-FILE]"

#####################################
### AXES AND KEY

# Axes labels
set xlabel "Rank" font ",24"
set ylabel "[STATISTIC-Y-LABEL]" font ",24"
set xtics font ",24"
set ytics font ",19"

# Axes ranges
set xrange [100:]
set yrange [0:]
set format x "10^{%L}"
set format y "%.0f%%"

# For logarithmic axes
set log x

# Font of the key (a.k.a. legend)
set key font ",18"
set key reverse
set key top left Left
set key spacing 2

#####################################
### PLOTS
set datafile separator ","
plot    "[DATA-FILE-ALEXA-NEW]" using ($1):($2) title "Alexa\\\_18" w lp ls 1, \
        "[DATA-FILE-UMBRELLA-JOINT]" using ($1):($2) title "Umbrella\\\_JOINT" w lp ls 2, \
        "[DATA-FILE-ALEXA-OLD]" using ($1):($2) title "Alexa\\\_1318" w lp ls 3, \
        "[DATA-FILE-MAJESTIC-JOINT]" using ($1):($2) title "Majestic\\\_JOINT" w lp ls 4, \
