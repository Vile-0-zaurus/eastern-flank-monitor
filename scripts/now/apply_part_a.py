#!/usr/bin/env python3
"""Apply Part A data fixes. No model calls. No new sources."""
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
VIEW = ROOT / "frontend" / "now-view.json"

MOD = {
    "2026-08-03": ("The Russian Defence Ministry said air defence shot down 131 drones over 11 regions and the Black Sea overnight.", "Работа ПВО Минобороны РФ: над 11 регионами и Черным морем сбили 131 БПЛА", "https://iz.ru/2142769/2026-08-03/sredstva-pvo-sbili-131-ukrainskii-bespilotnik-nad-territoriei-rossii-za-noch", 40),
    "2026-08-10": ("The Russian Defence Ministry confirmed strikes on military rear areas of the Kyiv authorities.", "В Минобороны РФ подтвердили удары по военным тылам киевского режима.", "https://www.1tv.ru/news/2026-08-10/549943", 26),
    "2026-08-17": ("The Russian Defence Ministry gave figures on the capture of Novosoloshino in the Zaporizhzhia region.", "Освобождение Новосолошино в Запорожской области: данные Минобороны РФ", "https://iz.ru/2151318/2026-08-19/boitcy-vs-rf-rasskazali-ob-osvobozhdenii-novosoloshino", 8),
    "2026-08-24": ("The Russian Defence Ministry gave new details on the capture of Vodyanske in the Donetsk region.", "В Минобороны России рассказали новые детали освобождения Водянского в ДНР", "https://russian.rt.com/ussr/news/1673303-rsosiya-osvobozhdenie-vodyanskoe", 30),
    "2026-08-31": ("A roundup cited a Russian Defence Ministry statement during an advance toward Sloviansk.", "Новости СВО 31 августа: наступление на Славянск, заявление Минобороны России", "https://lenta.ru/news/2026/08/31/opisana-situatsiya-bliz-pos/", 7),
    "2026-09-07": ("The Russian Defence Ministry named the targets it said were hit in Ukraine overnight.", "Минобороны России назвало пораженные за ночь цели на Украине", "https://russian.rt.com/ussr/news/1679676-rossiya-porazila-celi-ukraina", 9),
    "2026-09-14": ("The Russian Defence Ministry said Tu-95MS aircraft flew over neutral waters of two seas.", "Ту-95МС пролетели над нейтральными водами двух морей: заявление Минобороны РФ", "https://iz.ru/2167346/tu-95ms-vypolnili-polet-nad-neitralnymi-vodami-barentceva-i-norvezhskogo-morei-izi", 18),
    "2026-09-21": ("The Russian Defence Ministry published an overnight strike summary.", "Минобороны РФ представило сводку по ударам за ночь", "https://iz.ru/2171878/2026-09-23/vs-rossii-udarili-po-predpriiatiiam-vpk-i-obektam-tek-ukrainy", 15),
    "2026-09-28": ("The Russian Defence Ministry said a corporal delivered ammunition under fire and a sailor saved a group from FPV drones.", "Минобороны РФ: ефрейтор Деревянченко доставил боеприпасы под обстрелом, матрос Андрешко спас группу от FPV-дронов", "https://iz.ru/2175119/efreitor-derevianchenko-dostavil-boepripasy-pod-artilleriiskim-ognem-vsu-izi", 27),
    "2026-10-05": ("The Russian Defence Ministry showed assault troops clearing a Ukrainian position.", "Минобороны России показало работу штурмовиков по зачистке опорника ВСУ", "https://russian.rt.com/ussr/news/1690711-rossiya-shturmoviki-opornik-vsu", 17),
    "2026-10-12": ("The Russian Defence Ministry said it created a service for training military neural networks.", "ИИ в военных целях: сервис Минобороны РФ", "https://iz.ru/2182652/2026-10-12/v-minoborony-rossii-sozdan-servis-dlia-obucheniia-neirosetei-voennogo-naznacheniia", 22),
    "2026-10-19": ("The Russian Defence Ministry named the targets of a large strike in Kyiv.", "Минобороны РФ раскрыло цели массированного удара в Киеве", "https://aif.ru/politics/world/minoborony-rf-raskrylo-celi-massirovannogo-udara-v-kieve", 22),
}
PLANT = {
    "2026-08-03": ("A Moscow court extended house arrest for a deputy head of Uralvagonzavod.", "Суд в Москве продлил домашний арест замглавы \"Уралвагонзавода\" Семизорова", "https://ria.ru/20260803/sud-2108738214.html", 11),
    "2026-08-10": ("The head of Kalashnikov spoke about upgrading Vikhr missiles to fight drones.", "Глава «Калашникова» рассказал о модернизации ракет «Вихрь» для борьбы с дронами", "https://iz.ru/2146513/glava-kalashnikova-rasskazal-o-modernizatcii-raket-vikhr-dlia-borby-s-dronami-izi", 14),
    "2026-08-24": ("Kalashnikov presented the TS 2.0 with a beaver-tail mount.", "«Калашников» представил ТС 2.0 с «Бобровым хвостом»", "https://lenta.ru/news/2026/08/26/kalashnikov-predstavil-ts-2-0-s-bobrovym-hvostom/", 5),
    "2026-08-31": ("Kalashnikov will show an AK-12+ model at the Eastern Economic Forum.", "Павильон «Калашникова» на ВЭФ-2026: концерн представит АК-12+", "https://iz.ru/2158165/kalashnikov-predstavit-na-vef-maket-novogo-avtomata-ak-12-izi", 5),
    "2026-09-07": ("Kalashnikov delivered mounts for anti-aircraft machine guns.", "«Калашников» передал опоры для зенитных пулеметов", "https://lenta.ru/news/2026/09/07/kalashnikov-peredal-opory-dlya-zenitnyh-pulemetov/", 7),
    "2026-09-14": ("Kalashnikov will show an anti-drone gate for the first time.", "«Калашников» впервые представит антидроновую «Калитку»", "https://lenta.ru/news/2026/09/15/kalashnikov-vpervye-predstavit-antidronovuyu-kalitku/", 12),
    "2026-09-21": ("Kalashnikov will show its newest rifles in Azerbaijan for the first time.", "«Калашников» впервые представит в Азербайджане новейшие автоматы", "https://lenta.ru/news/2026/09/25/kalashnikov-vpervye-predstavit-v-azerbaydzhane-noveyshie-avtomaty/", 2),
    "2026-09-28": ("Kalashnikov shipped a batch of upgraded SVD rifles to a foreign customer.", "Калашников поставил партию модернизированных СВД зарубежному партнеру", "https://rg.ru/2026/10/01/koncern-kalashnikov-otgruzil-partiiu-snajperskih-vintovok-zarubezhnomu-zakazchiku.html", 4),
    "2026-10-05": ("Uralvagonzavod tested an updated BREM-80 recovery vehicle.", "«Уралвагонзавод» испытал обновленную БРЭМ-80", "https://lenta.ru/news/2026/10/06/uralvagonzavod-ispytal-obnovlennuyu-brem-80/", 15),
    "2026-10-12": ("Kalashnikov tactical mounts were adapted for drone hunters.", "Тактические опоры «Калашникова» адаптировали для «охотников за дронами»", "https://lenta.ru/news/2026/10/12/takticheskie-opory-kalashnikova-adaptirovali-dlya-ohotnikov-za-dronami/", 1),
    "2026-10-19": ("Kalashnikov shipped a batch of 9M333 missiles.", "«Калашников» отгрузил партию ракет 9М333", "https://lenta.ru/news/2026/10/19/kalashnikov-otgruzil-partiyu-raket-9m333/", 7),
}
CONS = {
    "2026-09-28": ("An Izvestia review of the autumn 2026 call-up: what changed and who it covers.", "Осенний призыв 2026: что изменилось и кого коснется — разбор", "https://iz.ru/2175317/s-1-oktiabria-startuet-osennii-prizyv-chto-izmenilos-v-2026-godu-i-kogo-kosnetsia-izi", 2),
    "2026-10-19": ("The Southern Military District discharged soldiers from the autumn 2025 call-up.", "В Южном военном округе проводили в запас солдат осеннего призыва 2025 года", "https://tvzvezda.ru/news/20261019185-ZHMjG.html", 1),
}
WEEKS = [
    "2026-08-03", "2026-08-10", "2026-08-17", "2026-08-24", "2026-08-31",
    "2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28", "2026-10-05",
    "2026-10-12", "2026-10-19",
]


def arrow(count: int, usual: int) -> str:
    if count > usual:
        return "↑"
    if count < usual:
        return "↓"
    return "→"


def card(title: str, row: tuple[str, str, str, int], usual: int) -> dict:
    line, russian, url, count = row
    return {
        "title": title,
        "line": line,
        "russian": russian,
        "url": url,
        "count": f"{count} stories, usual {usual}",
        "arrow": arrow(count, usual),
    }


def main() -> None:
    view = json.loads(VIEW.read_text(encoding="utf-8"))
    changes = []
    for item in view["incidents"]:
        old = item["type"]
        if item["place"] == "South of Utö" and "IL-20" in item["summary"]:
            item["type"] = "aircraft"
        elif item["place"] == "North of Braniewo" and "Mi-8" in item["summary"]:
            item["type"] = "aircraft"
        elif item["place"] == "Alūksne Municipality":
            item["type"] = "unspecified"
            item["source_note"] = (
                "Latvian defence ministry page did not connect on 22 November 2026. "
                "The stored note says the page declares an airspace threat and does not name a drone or an aircraft. "
                "Type is not drone."
            )
        if item["type"] != old:
            changes.append(f"{item['date']} {item['country']} {item['place']}: {old} -> {item['type']}")
    mod_usual = int(median([row[3] for row in MOD.values()]))
    plant_counts = [PLANT[week][3] if week in PLANT else 0 for week in WEEKS]
    plant_usual = int(median(plant_counts))
    cons_counts = [CONS[week][3] if week in CONS else 0 for week in WEEKS]
    cons_usual = int(median(cons_counts))
    weeks = {}
    for week in WEEKS:
        cards = [card("Defence Ministry", MOD[week], mod_usual)]
        if week in PLANT:
            cards.append(card("Defence contractors", PLANT[week], plant_usual))
        if week in CONS:
            cards.append(card("Conscription", CONS[week], cons_usual))
        weeks[week] = {"cards": cards}
    view["inside"] = {
        "note": "Inside Russia informs. It does not change the reading. English lines were written from the stored Russian titles. No model call.",
        "coverage": "Now window only, 3 August through 25 October 2026. Bank of Russia ruble and key-rate files stop on 21 February 2022, so those cards are absent.",
        "volume_note": "Usual is the median weekly count of matching stored headlines in this frozen window. It is not the registered scoring baseline.",
        "weeks": weeks,
    }
    VIEW.write_text(json.dumps(view, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("type changes:")
    for row in changes:
        print("-", row)
    print("mod usual", mod_usual, "plant usual", plant_usual, "cons usual", cons_usual)
    lines = []
    for week, block in weeks.items():
        for item in block["cards"]:
            lines.append(item["line"])
    print("unique lines", len(set(lines)), "of", len(lines))


if __name__ == "__main__":
    main()
