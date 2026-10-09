#!/usr/bin/env python3
"""Write gold-b2-candidates.csv. English is written here, not by a paid model."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PICK = ROOT / "validation" / "gold-b2-pick.json"
OUT = ROOT / "validation" / "gold-b2-candidates.csv"
FIELDS = ["id", "bucket", "domain", "date", "title", "title_en", "url"]

EN = {
    "681100": "Belarus did not send troops to the Polish border, but seeks to counter aggression — Lukashenko",
    "319100": "The State Duma condemned discrimination against Russians in Latvia",
    "498876": "A tourist from the Netherlands was fined in Poland for a Nazi salute at the gates of Auschwitz",
    "598105": "A soldier who fled to Belarus called Poland's migration policy genocide",
    "123254": "Putin spoke about Poland's aggressive actions against migrants at the border",
    "263389": "In the Urals, a criminal case was dropped against a woman who ordered antidepressants from Poland",
    "410955": "Lukashenko is ready to call the era of Polish rule an occupation and ethnocide",
    "674890": "Poland's Sejm adopted a resolution condemning \"Russia's aggression against Ukraine\"",
    "210953": "\"The Nazis took their revenge there\" — social media on a Red Army monument in Latvia",
    "31908": "Russia's State Duma condemns discrimination against Russian compatriots in Latvia — statement",
    "480182": "Zelensky will discuss \"Russian aggression\" in Poland",
    "554074": "Ukraine thanked Poland for its support \"in the face of Russian aggression\"",
    "114446": "Latvia banned the St. George ribbon, seeking to forget its own fascist past",
    "357235": "A complaint accusing Lukashenko of genocide was filed with the Polish prosecutor's office",
    "421559": "Lithuania and Latvia refused to help Minsk with a case about the genocide of Belarusians",
    "675348": "8% of people in Poland aged 60–69 face discrimination at work — poll",
    "161699": "Lukashenko compared Polish security forces' measures to fascist actions",
    "331834": "Belarus's Foreign Ministry called Lithuania's transit ban an act of hostility and aggression",
    "421591": "Minsk was outraged that Latvia and Lithuania refused to help investigate a genocide",
    "561555": "In Lithuania, Belarusian aggression was called predictable",
    "131905": "Belarusian state television calls Polish border guards \"punishers\"",
    "353806": "Social media: \"The main Russophobes\" — Gazprom left Poland without gas",
    "477140": "Estonia's prime minister accused Russia of military aggression against Ukraine",
    "649106": "Documentary \"War of the Worlds\": the fascist secrets of White Finland",
    "682201": "Anti-Semitism and Russophobia are running rampant in Ukraine and the Baltic states, Lavrov warns",
    "270589": "Latvia's Saeima agreed to open a criminal case against an MP for espionage",
    "428813": "Goliath's revenge, or what Lithuania's cooperation with Taiwan has already led to",
    "600712": "A court in The Hague will hear rights groups' claim of \"genocide of migrants\" in Poland",
    "111994": "\"Like fascists, the Gestapo\": Lukashenko on Poland's defense against illegal migrants",
    "226148": "A NATO meeting in Latvia confirmed an aggressive turn in the alliance's evolution",
    "485234": "Latvia's president was booed at the unveiling of a monument to a dissident Russophobe",
    "638124": "A Latvian party says language limits on campaigning are discriminatory",
    "120427": "\"An outright Nazi gesture\" — social media on the ban of St. George ribbons in Latvia",
    "352777": "Rada deputy Buzhansky spoke of \"Polish, Romanian and Hungarian revanchism\"",
    "424111": "Latvia acknowledged discrimination against young people and people over 50",
    "588682": "Germany, France and Poland said aggression against Ukraine would carry a high price for Russia",
    "199433": "Polish searchers found 77 graves of prisoners from a Nazi concentration camp for children in Lodz",
    "298069": "The State Duma condemned discrimination against Russian compatriots in Latvia",
    "434631": "In Poland, they spoke of \"monetizing Russian aggression\" against Ukraine",
    "578306": "Estonia's chief military hawk and Russophobe is visiting Moscow",
    "18790": "Estonia's only unvaccinated minister resigned",
    "380377": "Estonia's president proposed keeping Russian schools after teaching switches to Estonian",
    "533878": "A Polish soldier who fled to Belarus appealed to the Hague tribunal",
    "628607": "Polish volleyball players rode a bus for 12 hours to meet Lokomotiv in Kaliningrad",
    "99742": "Putin and Lukashenko discussed refugees on Belarus's borders with Poland and Lithuania",
    "300431": "What did Vladimir Putin and Finnish President Sauli Niinistö talk about?",
    "404696": "An Estonian lawmaker called her country a \"petty, spiteful provocateur\"",
    "628593": "Poland intends to prepare for \"different scenarios in Ukraine\"",
    "25690": "A Polish journalist reflected on whether Nord Stream 2 is necessary",
    "308957": "The Baltics were given a lesson in Chinese diplomacy",
    "539524": "2021 was a record year in Poland for the volume of mortgage loans",
    "586183": "Poland recorded 35,960 SARS-CoV-2 cases in one day",
    "150916": "Poland's prime minister urged Germany to stop certification of Nord Stream 2",
    "319555": "A photo of a Polish soldier who fled to Belarus appeared online",
    "429026": "People suspected of cooperating with Russian intelligence were detained in Latvia",
    "655073": "Poland called the arrival of new US Army units very likely",
    "166694": "More than ten thousand migrants are in Belarus, Poland's prime minister said",
    "31930": "Baltic Sea collision: two UK ship crew members exceeded the legal limit for drugs and alcohol",
    "435475": "A Polish soldier who fled to Belarus spoke of the killing of hundreds of refugees",
    "608347": "Finland's Foreign Ministry urged its citizens to leave Ukraine",
    "136165": "Poland ruled out a war using weapons against Belarus",
    "323783": "Latvia's Foreign Ministry considers it impossible to meet Russia's security-guarantee demands",
    "54000": "Kyiv keeps avoiding implementation of the Minsk accords, Putin tells the Finnish president",
    "605175": "COVID certificates in Estonia cannot be canceled before spring",
    "141782": "The worst way the situation on the Poland-Belarus border could develop was described",
    "345078": "A bus overturned on Warsaw Highway in New Moscow",
    "466968": "Poland assessed how its seaports performed in 2021",
    "616330": "COVID certificates were dropped for outdoor events in Estonia",
    "175307": "Poland said it was ready to talk with Russia about the border situation with Belarus",
    "232860": "Poland's Foreign Ministry spoke about new EU sanctions against Belarus",
    "38085": "Lithuania is considering a military draft for women",
    "643062": "Estonian troops are ending their mission in Mali",
    "119080": "Focus: years of inaction and political blindness — the EU itself is to blame for the crisis on the Belarus-Poland border",
    "367495": "Residents of Poland were warned about severe frosts",
    "412427": "A Polish soldier who fled to Belarus demanded his pay from Poland's Defense Ministry",
    "549378": "District heating costs for Tallinn residents rose again",
    "142650": "Poland said migrants were trying to break through the border",
    "239532": "Troops from Britain and Estonia arrived at the Belarus-Poland border",
    "515193": "Latvia's President Levits believes Russia intends to restore the Soviet empire",
    "614574": "Lithuania's Foreign Ministry advised citizens to leave Ukraine immediately",
}


def main() -> None:
    rows = json.loads(PICK.read_text(encoding="utf-8"))
    missing = [row["id"] for row in rows if row["id"] not in EN]
    if missing:
        raise SystemExit(f"missing translations: {missing}")
    if len(rows) != 80:
        raise SystemExit(f"expected 80 rows, got {len(rows)}")
    for row in rows:
        row["title_en"] = EN[row["id"]]
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT} rows={len(rows)} blank_en={sum(1 for row in rows if not row['title_en'].strip())}")


if __name__ == "__main__":
    main()
