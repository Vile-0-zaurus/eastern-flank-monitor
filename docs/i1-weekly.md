# I1 weekly summary

Window: 2021-01-01 through 2022-02-24. No model calls.

I1 is the daily count of title-relevant, deduplicated stories about Finland, Estonia, Latvia, Lithuania, or Poland, divided by all deduplicated stories from the outlet list. The day is the GKG file day. A story is the article URL, or domain plus title when the URL is empty. The same URL counts once per day. A later blank copy does not erase a relevant title.

Title match uses `config/region_keywords.yaml`. The GDELT location tag is not used. A Kaliningrad-only title does not count. A missing day would be no data, not zero. This window has 420 days and none are missing.

Share below is the week's relevant stories divided by the week's outlet stories, not the average of daily shares. A week with fewer than 7 days in the window is marked partial.

Window total: 25,422 relevant stories, 2,132,016 outlet stories, share 0.0119.

Daily rows are in `data/indicators/indicators.sqlite`, table `indicators`, indicator `I1`. That file is local and is not committed.

```
week        days  relevant  outlet_stories  share    note
2020-12-28     3        59            6788   0.0087  partial
2021-01-04     7       152           19502   0.0078
2021-01-11     7       239           33410   0.0072
2021-01-18     7       218           33642   0.0065
2021-01-25     7       243           34401   0.0071
2021-02-01     7       341           34572   0.0099
2021-02-08     7       329           33916   0.0097
2021-02-15     7       351           37449   0.0094
2021-02-22     7       235           31234   0.0075
2021-03-01     7       343           38362   0.0089
2021-03-08     7       354           34463   0.0103
2021-03-15     7       298           38405   0.0078
2021-03-22     7       307           38994   0.0079
2021-03-29     7       350           38505   0.0091
2021-04-05     7       336           38950   0.0086
2021-04-12     7       455           40017   0.0114
2021-04-19     7       460           39175   0.0117
2021-04-26     7       393           38872   0.0101
2021-05-03     7       365           28064   0.0130
2021-05-10     7       236           34386   0.0069
2021-05-17     7       413           39036   0.0106
2021-05-24     7       821           38731   0.0212
2021-05-31     7       487           40078   0.0122
2021-06-07     7       443           37679   0.0118
2021-06-14     7       430           34946   0.0123
2021-06-21     7       285           36719   0.0078
2021-06-28     7       319           34067   0.0094
2021-07-05     7       471           32748   0.0144
2021-07-12     7       295           32103   0.0092
2021-07-19     7       324           31110   0.0104
2021-07-26     7       268           28633   0.0094
2021-08-02     7       440           26663   0.0165
2021-08-09     7       407           25189   0.0162
2021-08-16     7       270           28230   0.0096
2021-08-23     7       380           33158   0.0115
2021-08-30     7       339           34126   0.0099
2021-09-06     7       360           34583   0.0104
2021-09-13     7       370           36053   0.0103
2021-09-20     7       341           35384   0.0096
2021-09-27     7       264           34701   0.0076
2021-10-04     7       364           33957   0.0107
2021-10-11     7       290           34306   0.0085
2021-10-18     7       466           35308   0.0132
2021-10-25     7       650           39855   0.0163
2021-11-01     7       310           33002   0.0094
2021-11-08     7      1439           39901   0.0361
2021-11-15     7      1206           40841   0.0295
2021-11-22     7       708           40343   0.0175
2021-11-29     7       564           42485   0.0133
2021-12-06     7       537           42220   0.0127
2021-12-13     7       529           40714   0.0130
2021-12-20     7       459           40106   0.0114
2021-12-27     7       341           33810   0.0101
2022-01-03     7       244           23258   0.0105
2022-01-10     7       487           39117   0.0124
2022-01-17     7       487           40858   0.0119
2022-01-24     7       462           40434   0.0114
2022-01-31     7       644           39257   0.0164
2022-02-07     7       552           39415   0.0140
2022-02-14     7       547           40718   0.0134
2022-02-21     4       345           25067   0.0138  partial
```
