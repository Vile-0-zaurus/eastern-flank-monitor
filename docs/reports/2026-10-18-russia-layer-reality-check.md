# Russia layer, step 1 — data reality check

Checked 2026-10-18 from this machine. No pipeline was built. No VPN, no DNS change, and no user-agent spoofing. A timeout means this network could not reach the host. It does not mean the source does not exist.

This is a reading of public pages and of Council Decision 2014/512/CFSP. It is not legal advice.

## Table

| Source | Works / partly / fails | 2021–22 history | Legal note | What a normal user would see |
|---|---|---|---|---|
| Stocks: Moscow Exchange, plus a free mirror, and the ruble | Partly | Yes for the samples that answered. Not a full download. | EU rules restrict dealing in certain Russian securities and transactions that manage Central Bank of Russia reserves. Reading a published price or rate is not that dealing. Do not trade these shares or connect to a Russian exchange or payment system. | KAMAZ's daily share price, and how many rubles bought one dollar. |
| Economy: GDP and reserves, including gold | Works, through the World Bank mirror | Yes, as yearly totals for 2021 and 2022. Not weekly. | The same reserve rule covers managing Central Bank reserves. A published World Bank total is not that transaction. | Russia's yearly GDP, and its total reserves including gold, for 2021 and 2022. |
| Conscription decrees | Fails from this network | Not measured. The hosts did not answer. | Reading a public decree is not a sanctions transaction. | The spring and autumn 2021 call-up numbers, if the decree site had answered. |
| Military talk in stored headlines | Works | Yes. All 60 weeks in the window. | Already stored. No new fetch. | How many stored headlines that week named the defence ministry or Shoigu. |
| Defense plants in stored headlines | Works | Yes. All 60 weeks in the window. | Already stored. No new fetch. | How many stored headlines that week named a defense plant, extra shifts, hiring, or a contract. |

## What was measured

Stocks. Moscow Exchange robots.txt asks for a 10-second pause. One history request returned daily JSON for KAMAZ (KMAZ) from 4 January 2021 through 8 January 2021, with a trade date, open, and close. UAC was not requested after that pause was read. The Central Bank rate file returned XML for 1 January 2021, one dollar at 73.8757 rubles. Stooq returned a browser-check page and no prices. It was not retried.

Economy. The World Bank returned yearly JSON. GDP (current US dollars) is present for 2021 and 2022. Total reserves including gold are present for 2021 and 2022. The IMF data page opened. A series was not retrieved from it. The Central Bank home page opened.

Conscription. publication.pravo.gov.ru and kremlin.ru both timed out. No decree text was collected.

Military talk. One read-only pass over stored titles, keywords only, no model. 5,105 titles named Shoigu or the defence ministry. Every week from 4 January 2021 through 21 February 2022 had at least one. The weekly count ran from 17 to 180.

Defense plants. The same pass, different keywords (KAMAZ, UAC, a defense plant, extra shifts, a contract). 1,300 titles. Every week had at least one. The weekly count ran from 5 to 50. A keyword hit is not proof the story is about a plant.

## Legal note

Lithuania applies the EU Russia regulations, including Regulation 833/2014 and Regulation 269/2014. Council Decision 2014/512/CFSP prohibits dealings in certain Russian transferable securities, and transactions related to the management of Central Bank of Russia reserves. A public statistics page is not those transactions. Buying the shares, or using a Russian trading or payment system, is a different act and should be treated as restricted unless a current exemption says otherwise.

## Biggest risk

The decree sites did not answer from this network, so call-up numbers cannot be shown yet. The cheapest path that did answer for 2021–22 is the stored headline counts, the World Bank yearly totals, the Central Bank rate file, and the Moscow Exchange history file for a named share.
