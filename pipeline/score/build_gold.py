#!/usr/bin/env python3
"""Write the 50-headline gold file. Labels stay empty. No model is called."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATCHES = ROOT / "data" / "validation" / "region_matches.sqlite"
OUT = ROOT / "data" / "validation" / "gold.csv"

# Hand-picked from the 2021-06-15 match set. First 25 are pretext-suggested.
EN = {
    118: "Estonian authorities will cut funding for Russian-language schools",
    148: "Estonia will stop funding Russian-language schools and kindergartens",
    142: "Estonia will stop funding education in Russian-language schools from 2035",
    171: "Estonia will stop funding education in Russian from 2035",
    255: "Kirkorov's lawyer wants to go to the ECHR over the ban on the singer entering Lithuania",
    128: "Kirkorov will appeal a Vilnius court ruling that upheld the ban on entering Lithuania",
    11: "'Racist' songs and alleged sexual abuse: four German soldiers recalled from the NATO mission in Lithuania over misconduct",
    180: "NATO fighters escorted Russian Tu-160s flying over the Baltic",
    9: "Foreign fighters escort Russian Tu-160 bombers over the Baltic Sea",
    234: "Nationalism, corruption, the war in Donbas: why they do not want to admit Ukraine to NATO",
    21: "A former Ukrainian minister saw a threat in Russia's repatriation law",
    138: "The State Duma approved on second reading a ban on displaying images of Nazis",
    39: "Poland marked the National Day of Remembrance of the victims of Nazi concentration camps",
    129: "Lithuania's Seimas adopted a resolution demanding Russia pay compensation for the 'Soviet occupation'",
    149: "Lithuania's Seimas approved a demand that Russia pay compensation for the 'Soviet occupation'",
    76: "Poland's foreign minister: Russia's absorption of Belarus continues",
    166: "Kuleba accused Russia of being the reason Ukraine is not accepted into NATO",
    4: "Ukraine gaining access to NATO's waiting room 'remains to be seen', Biden says, after Zelensky claimed it was confirmed",
    111: "NATO summit in Brussels: Lithuania outplayed Poland",
    102: "Estonia marked the 80th anniversary of the Soviet deportation",
    133: "Lithuania believes Minsk is using illegal migration as a means of pressure on Vilnius",
    175: "Latvians' first European Parliament election: a triumph of the nationalists",
    174: "Estonia gave up oil shale in order to cut down its forests — an opinion",
    90: "Protasevich said he was followed in Warsaw and Vilnius",
    96: "A 19-year-old Kaliningrad woman became the victim of a foreign rapist",
    27: "More than 35,000 homes left without electricity in Finland because of a storm",
    40: "160 kg of drugs found in a shop in central Warsaw",
    51: "Russia's sports minister called the match against Finland decisive for the national team",
    6: "U.K. and Western Europe have the least engaged employees globally",
    80: "Estonia is restarting ferries from Tallinn to Stockholm under special conditions",
    92: "A Dutch referee, Makkelie, will officiate the Finland–Russia match",
    99: "Another 78 people in Kaliningrad region have caught the coronavirus",
    144: "Scientists have created a vaccine against Alzheimer's disease",
    140: "Prices of consumer goods and services rose in Poland",
    152: "Every fourth driver in Estonia is a dangerous traffic offender",
    162: "Poland will send a delegation to the Czech Republic to settle the Turów mine dispute",
    170: "Latvia allowed two types of mass events",
    173: "Kaliningrad region will receive 547 million rubles to clean up landfill sites",
    177: "Every fifth adult in Latvia is fully vaccinated",
    178: "Police: drinking alcohol in public in Tallinn risks a huge fine",
    204: "Darknet drug dealers will stand trial in Kaliningrad",
    207: "Rospotrebnadzor proposed cancelling City Day and closing the fan zone in Kaliningrad",
    211: "Kaliningrad residents were asked to name Russia's largest piece of amber; it weighs almost 4.5 kg",
    213: "Rescuers in Kaliningrad failed to pull a dead catfish out of the river",
    215: "The first deputy prime minister has resigned from the Kaliningrad regional government",
    217: "A thief of ceramic toys has appeared in Kaliningrad",
    232: "Ahead is the most important battle of UEFA Euro 2020 — Russia vs Finland",
    245: "Eriksen, who survived cardiac arrest, watched the last 10 minutes of the match against Finland",
    249: "The unfinished House of Soviets will be dismantled in Kaliningrad",
    296: "Finland is interested in a high-speed railway between Helsinki and Moscow",
}


def main() -> None:
    con = sqlite3.connect(f"file:{MATCHES}?mode=ro", uri=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "bucket", "domain", "title", "title_en", "url", "relevant", "f1", "f2", "f3", "f4", "f5", "f6", "notes"]
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fields)
        w.writeheader()
        for n, (mid, en) in enumerate(EN.items(), start=1):
            row = con.execute(
                "SELECT domain, page_title, article_url FROM matches WHERE id=?", (mid,)
            ).fetchone()
            if not row:
                raise SystemExit(f"missing match id {mid}")
            w.writerow(
                {
                    "id": mid,
                    "bucket": "pretext" if n <= 25 else "neutral",
                    "domain": row[0],
                    "title": row[1],
                    "title_en": en,
                    "url": row[2],
                    "relevant": "",
                    "f1": "",
                    "f2": "",
                    "f3": "",
                    "f4": "",
                    "f5": "",
                    "f6": "",
                    "notes": "",
                }
            )
    con.close()
    print(f"wrote {len(EN)} rows to {OUT}")


if __name__ == "__main__":
    main()
