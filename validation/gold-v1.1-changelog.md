# Gold v1.1 relevance changelog

Copied from tagged gold-v1. Hostile and ordinary labels, frame scores, and notes were not changed.
Corrections use the headline text and rules 1–3 only. No model output was consulted.
Rule 1: about Finland, Estonia, Latvia, Lithuania, or Poland, on any topic.
Rule 2: Kaliningrad local or domestic news stays not relevant. None of those rows needed a flip.
Rule 3: Ukraine-only or Russia-only news is not relevant, even if NATO is named.
Id 175 is still unlabeled.

| id | old relevance | new relevance | rule | headline |
|---|---|---|---|---|
| 234 | yes | no | 3 | Nationalism, corruption, the war in Donbas: why they do not want to admit Ukraine to NATO |
| 21 | yes | no | 3 | A former Ukrainian minister saw a threat in Russia's repatriation law |
| 138 | yes | no | 3 | The State Duma approved on second reading a ban on displaying images of Nazis |
| 166 | yes | no | 3 | Kuleba accused Russia of being the reason Ukraine is not accepted into NATO |
| 4 | yes | no | 3 | Ukraine gaining access to NATO's waiting room 'remains to be seen', Biden says, after Zelensky claimed it was confirmed |
| 174 | no | yes | 1 | Estonia gave up oil shale in order to cut down its forests — an opinion |
| 90 | no | yes | 1 | Protasevich said he was followed in Warsaw and Vilnius |
| 27 | no | yes | 1 | More than 35,000 homes left without electricity in Finland because of a storm |
| 40 | no | yes | 1 | 160 kg of drugs found in a shop in central Warsaw |
| 92 | no | yes | 1 | A Dutch referee, Makkelie, will officiate the Finland–Russia match |
| 140 | no | yes | 1 | Prices of consumer goods and services rose in Poland |
| 152 | no | yes | 1 | Every fourth driver in Estonia is a dangerous traffic offender |
| 162 | no | yes | 1 | Poland will send a delegation to the Czech Republic to settle the Turów mine dispute |
| 170 | no | yes | 1 | Latvia allowed two types of mass events |
| 177 | no | yes | 1 | Every fifth adult in Latvia is fully vaccinated |
| 178 | no | yes | 1 | Police: drinking alcohol in public in Tallinn risks a huge fine |
| 232 | no | yes | 1 | Ahead is the most important battle of UEFA Euro 2020 — Russia vs Finland |
| 245 | no | yes | 1 | Eriksen, who survived cardiac arrest, watched the last 10 minutes of the match against Finland |

Changes: 18. Rows left as labeled: 31. Unlabeled: 1.

Near-duplicate groups, scored once in the diagnostic:

- ee-ru-schools: 118, 148, 142, 171
- kirkorov-lt: 255, 128
- tu160-baltic: 180, 9
- ua-nato-summit: 4, 166, 234
- lt-occupation: 129, 149. Human framing conflicts (hostile vs ordinary). Excluded from the hostile metric.
- fi-euro-match: 51, 92, 232, 245. Representative is 51, the only row in the group with a framing label.
