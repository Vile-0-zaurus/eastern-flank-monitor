# I1 weekly summary

Window: 2021-01-01 through 2022-02-24. No model calls.

I1 is the daily count of title-relevant, deduplicated stories about Finland, Estonia, Latvia, Lithuania, or Poland, divided by all deduplicated stories from the outlet list. The day is the GKG file day. A story is the article URL, or domain plus title when the URL is empty. The same URL counts once per day. A later blank copy does not erase a relevant title.

Title match uses `config/region_keywords.yaml`. The GDELT location tag is not used. A Kaliningrad-only title does not count. Bare stems Baltic, балтий, and балтик do not count. прибалт counts. The country phrases count. A missing day would be no data, not zero. This window has 420 days and none are missing.

Share below is the week's relevant stories divided by the week's outlet stories, not the average of daily shares. A week with fewer than 7 days in the window is marked partial.

Window total: 24,216 relevant stories, 2,132,016 outlet stories, share 0.0114.

The older series, which counted those Baltic stems, is not this table. The side-by-side is in `docs/reports/2026-10-09-2-i1-phrases.md`.

Daily rows are in `data/indicators/indicators.sqlite`, table `indicators`, indicator `I1`. That file is local and is not committed.

```
week        days  relevant  outlet_stories  share    note
2020-12-28     3        59            6788   0.0087  partial
2021-01-04     7       147           19502   0.0075  
2021-01-11     7       232           33410   0.0069  
2021-01-18     7       210           33642   0.0062  
2021-01-25     7       226           34401   0.0066  
2021-02-01     7       320           34572   0.0093  
2021-02-08     7       316           33916   0.0093  
2021-02-15     7       321           37449   0.0086  
2021-02-22     7       223           31234   0.0071  
2021-03-01     7       314           38362   0.0082  
2021-03-08     7       337           34463   0.0098  
2021-03-15     7       287           38405   0.0075  
2021-03-22     7       273           38994   0.0070  
2021-03-29     7       333           38505   0.0086  
2021-04-05     7       318           38950   0.0082  
2021-04-12     7       448           40017   0.0112  
2021-04-19     7       426           39175   0.0109  
2021-04-26     7       379           38872   0.0097  
2021-05-03     7       354           28064   0.0126  
2021-05-10     7       216           34386   0.0063  
2021-05-17     7       377           39036   0.0097  
2021-05-24     7       810           38731   0.0209  
2021-05-31     7       433           40078   0.0108  
2021-06-07     7       406           37679   0.0108  
2021-06-14     7       397           34946   0.0114  
2021-06-21     7       268           36719   0.0073  
2021-06-28     7       306           34067   0.0090  
2021-07-05     7       436           32748   0.0133  
2021-07-12     7       268           32103   0.0083  
2021-07-19     7       282           31110   0.0091  
2021-07-26     7       236           28633   0.0082  
2021-08-02     7       426           26663   0.0160  
2021-08-09     7       394           25189   0.0156  
2021-08-16     7       259           28230   0.0092  
2021-08-23     7       356           33158   0.0107  
2021-08-30     7       322           34126   0.0094  
2021-09-06     7       339           34583   0.0098  
2021-09-13     7       353           36053   0.0098  
2021-09-20     7       322           35384   0.0091  
2021-09-27     7       250           34701   0.0072  
2021-10-04     7       349           33957   0.0103  
2021-10-11     7       275           34306   0.0080  
2021-10-18     7       456           35308   0.0129  
2021-10-25     7       566           39855   0.0142  
2021-11-01     7       301           33002   0.0091  
2021-11-08     7      1427           39901   0.0358  
2021-11-15     7      1190           40841   0.0291  
2021-11-22     7       695           40343   0.0172  
2021-11-29     7       554           42485   0.0130  
2021-12-06     7       529           42220   0.0125  
2021-12-13     7       504           40714   0.0124  
2021-12-20     7       446           40106   0.0111  
2021-12-27     7       321           33810   0.0095  
2022-01-03     7       238           23258   0.0102  
2022-01-10     7       473           39117   0.0121  
2022-01-17     7       461           40858   0.0113  
2022-01-24     7       414           40434   0.0102  
2022-01-31     7       628           39257   0.0160  
2022-02-07     7       544           39415   0.0138  
2022-02-14     7       529           40718   0.0130  
2022-02-21     4       337           25067   0.0134  partial
```
