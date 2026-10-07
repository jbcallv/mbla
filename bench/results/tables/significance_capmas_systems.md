| comparison                                                        | metric       |   difference |     low |    high |      p |   p_holm |
|:------------------------------------------------------------------|:-------------|-------------:|--------:|--------:|-------:|---------:|
| mbla (qwen3-8b, admitted) - capmas as published (no recovery)     | ras_recovery |      -0.5594 | -0.7214 | -0.3929 | 0.0000 |   0.0000 |
| mbla (qwen3-8b, admitted) - capmas as published (no recovery)     | success      |       0.4653 |  0.2326 |  0.6771 | 0.0000 |   0.0000 |
| mbla (qwen3-8b, admitted) - capmas as published (no recovery)     | eac_C        |      -0.6551 | -0.8066 | -0.4944 | 0.0000 |   0.0000 |
| mbla (qwen3-8b, admitted) - capmas as published (no recovery)     | mac_C        |       0.0262 |  0.0000 |  0.0633 | 0.2008 |   0.4350 |
| mbla (qwen3-8b, admitted) - capmas as published (no recovery)     | exact_match  |       0.3299 |  0.1701 |  0.4931 | 0.0000 |   0.0000 |
| mbla (qwen3-8b, admitted) - capmas scorer + mbla recovery         | ras_recovery |      -0.7365 | -0.7956 | -0.6611 | 0.0000 |   0.0000 |
| mbla (qwen3-8b, admitted) - capmas scorer + mbla recovery         | success      |       0.0660 | -0.0451 |  0.1979 | 0.2852 |   0.2852 |
| mbla (qwen3-8b, admitted) - capmas scorer + mbla recovery         | eac_C        |      -0.6205 | -0.7607 | -0.4905 | 0.0000 |   0.0000 |
| mbla (qwen3-8b, admitted) - capmas scorer + mbla recovery         | mac_C        |       0.0262 | -0.0046 |  0.0633 | 0.1450 |   0.4350 |
| mbla (qwen3-8b, admitted) - capmas scorer + mbla recovery         | exact_match  |       0.3160 |  0.1435 |  0.4873 | 0.0004 |   0.0008 |
| capmas scorer + mbla recovery - capmas as published (no recovery) | ras_recovery |       0.1771 |  0.0204 |  0.3252 | 0.0282 |   0.0282 |
| capmas scorer + mbla recovery - capmas as published (no recovery) | success      |       0.3993 |  0.2396 |  0.5556 | 0.0000 |   0.0000 |
| capmas scorer + mbla recovery - capmas as published (no recovery) | eac_C        |      -0.0345 | -0.1486 |  0.0886 | 0.5482 |   0.5482 |
| capmas scorer + mbla recovery - capmas as published (no recovery) | mac_C        |       0.0000 | -0.0139 |  0.0139 | 1.0000 |   1.0000 |
| capmas scorer + mbla recovery - capmas as published (no recovery) | exact_match  |       0.0139 |  0.0000 |  0.0382 | 0.2130 |   0.2130 |
