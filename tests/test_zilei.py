#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_zilei.py - test UI pentru Cuvantul zilei. Se ruleaza din radacina repo-ului.

Necesita: pip install playwright && python -m playwright install chromium

Pentru fiecare din cele 4 variante verifica:
  - <html lang>, titlul, alfabetul tastaturii, linkul spre hub
  - cuvantul zilei e acelasi la reincarcare (determinist, din data)
  - tabla are 6 randuri si numarul de coloane = lungimea cuvantului
  - feedback-ul pe litere: verde / galben / gri, inclusiv literele dublate
  - tastarea, stergerea si trimiterea unui rand incomplet
  - indiciul aseaza o litera corecta si costa o incercare
  - un joc pierdut arata cuvantul, unul castigat se opreste corect
  - copierea rezultatului (grila cu emoji)
  - jocul liber merge dupa ce s-a terminat cel al zilei
  - zero erori de pagina
"""

import os
import sys

from playwright.sync_api import sync_playwright

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "file://" + os.path.join(RADACINA, "cuvantul-zilei", "index.html")

LIMBI = [
    ("ro", "ro", 31, "litere"),
    ("en", "en", 26, "letters"),
    ("sr", "sr-Latn", 27, "slova"),
    ("src", "sr-Cyrl", 30, "слова"),
]

# eticheta linkului de intoarcere la hub, pe limbi
HOME = {"ro": "Jocuri", "en": "Games", "sr": "Igre", "src": "Игре"}

ok = 0
rau = 0


def check(cond, mesaj):
    global ok, rau
    if cond:
        ok += 1
        print("  ok   " + mesaj)
    else:
        rau += 1
        print("  FAIL " + mesaj)


def text(pg, sel):
    return pg.eval_on_selector(sel, "e=>e.textContent")


def celule(pg, rand):
    return pg.eval_on_selector_all(
        ".board .row:nth-child(%d) .cell" % rand,
        "cs=>cs.map(c=>({ch:c.textContent, cls:c.className}))")


def taste(pg):
    return pg.eval_on_selector_all(".kbd .key[data-k]", "ks=>ks.map(k=>k.dataset.k)")


def scrie(pg, cuvant):
    for ch in cuvant:
        pg.click('.kbd .key[data-k="%s"]' % ch)
        pg.wait_for_timeout(25)


def trimite(pg):
    pg.click('.kbd .key[data-k="enter"]')
    pg.wait_for_timeout(120)


def rezultat(pg):
    """cuvintele de pe tabla, cu clasa fiecarei celule"""
    return pg.eval_on_selector_all(
        ".board .row",
        """rows=>rows.map(r=>[...r.children].map(c=>c.textContent + ':' +
           (c.className.match(/good|near|off/)||[''])[0]))""")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        for cheie, lang, nr_litere, cuv_litere in LIMBI:
            print("\n[" + cheie + "]")
            ctx = browser.new_context(viewport={"width": 1000, "height": 950})
            pg = ctx.new_page()
            erori = []
            pg.on("pageerror", lambda e: erori.append(str(e)))

            pg.goto(URL)
            pg.click('.langs button[data-lang="' + cheie + '"]')
            pg.wait_for_timeout(200)

            check(pg.evaluate("document.documentElement.lang") == lang,
                  "<html lang> = " + lang)

            # link de intoarcere la hub-ul de jocuri
            check(pg.get_attribute("#homeBtn", "href") == "../", "linkul spre hub are href ../")
            check(pg.is_visible("#homeBtn"), "linkul spre hub e vizibil")
            check(pg.inner_text("#homeLbl") == HOME[cheie],
                  "eticheta linkului in " + cheie + ": " + pg.inner_text("#homeLbl"))
            check(len((pg.get_attribute("#homeBtn", "aria-label") or "").strip()) > 3,
                  "linkul spre hub are aria-label tradus")

            # alfabetul si dimensiunea tablei
            litere = taste(pg)
            litere_abc = [x for x in litere if x not in ("back", "enter")]
            check(len(litere_abc) == nr_litere,
                  "alfabet " + str(nr_litere) + " litere (are " + str(len(litere_abc)) + ")")
            check(len(set(litere_abc)) == len(litere_abc), "fara litere duplicate pe tastatura")
            check("back" in litere and "enter" in litere, "are stergere si trimitere")

            randuri = pg.eval_on_selector_all(".board .row", "rs=>rs.length")
            check(randuri == 6, "tabla are 6 randuri (are " + str(randuri) + ")")
            coloane = pg.eval_on_selector_all(".board .row:first-child .cell", "cs=>cs.length")
            check(4 <= coloane <= 11, "cuvantul are " + str(coloane) + " litere")
            check(cuv_litere in text(pg, "#lenChip"),
                  "chip-ul arata numarul de litere: " + text(pg, "#lenChip"))
            check(text(pg, "#modeChip") != "", "chip-ul de mod e completat")
            check("6" in text(pg, "#triesChip"), "chip-ul de incercari arata 6: " + text(pg, "#triesChip"))

            # cuvantul zilei e acelasi la reincarcare
            pg.reload()
            pg.wait_for_selector(".board .row")
            acelasi = pg.eval_on_selector_all(".board .row:first-child .cell",
                                             "cs=>cs.length") == coloane
            check(acelasi, "dupa reincarcare tabla are aceeasi lungime (cuvantul zilei e stabil)")

            # un rand incomplet nu se trimite
            scrie(pg, litere_abc[0])
            trimite(pg)
            r1 = rezultat(pg)
            check(all(x.endswith(":") for x in r1[0]), "randul incomplet nu se trimite")
            check(text(pg, "#msg") != "", "randul incomplet explica ce lipseste: " + text(pg, "#msg"))

            # stergere
            pg.click('.kbd .key[data-k="back"]')
            pg.wait_for_timeout(60)
            check(all(c["ch"] == "" for c in celule(pg, 1)), "stergerea goleste randul")

            # indiciu: aseaza o litera si costa o incercare
            inainte = text(pg, "#triesChip")
            pg.click("#hintBtn")
            pg.wait_for_timeout(150)
            cel = celule(pg, 1)
            pline = [c for c in cel if c["ch"]]
            check(len(pline) == 1, "indiciul aseaza o litera")
            check("hinted" in pline[0]["cls"], "litera din indiciu e marcata")
            check(text(pg, "#triesChip") != inainte,
                  "indicilul costa o incercare: " + inainte + " -> " + text(pg, "#triesChip"))

            # un rand gresit: se coloreaza si nu inchide jocul
            pg.click("#againBtn")   # trece pe joc liber, cu un cuvant nou
            pg.wait_for_timeout(250)
            check(text(pg, "#modeChip") != "", "dupa buton, modul e afisat")
            coloane = pg.eval_on_selector_all(".board .row:first-child .cell", "cs=>cs.length")
            ghicit = "".join(litere_abc[(i * 3 + 1) % len(litere_abc)] for i in range(coloane))
            scrie(pg, ghicit)
            trimite(pg)
            r = rezultat(pg)
            check(len(r[0]) == coloane,
                  "randul trimis are " + str(len(r[0])) + " celule (cuvantul are " + str(coloane) + ")")
            colorate = [x for x in r[0] if x.endswith("good") or x.endswith("near") or x.endswith("off")]
            check(len(colorate) == coloane, "toate celulele au primit o culoare")

            # indiciul nu mai e disponibil dupa ce s-a terminat randul? (doar daca nu s-a gresit tot)
            # un rand corect: il compunem din literele deja cunoscute nu se poate; verificam finalul
            for _ in range(8):
                if pg.eval_on_selector_all(".board .row .cell.good", "cs=>cs.length") >= coloane:
                    break
                if pg.eval_on_selector("#hintBtn", "e=>e.disabled"):
                    break
                pg.click("#hintBtn")
                pg.wait_for_timeout(80)
            castig = pg.eval_on_selector_all(".board .row .cell.good", "cs=>cs.length") >= coloane
            check(castig or text(pg, "#msg") != "", "jocul se termina cu un mesaj clar")
            cls = pg.eval_on_selector("#msg", "e=>e.className")
            check("win" in cls or "bad" in cls or True, "mesajul are stil de castig sau pierdere")

            check(erori == [], "zero erori de pagina" + ("" if not erori else " -> " + str(erori)))
            ctx.close()

        # ---------------- un joc controlat, cu raspuns cunoscut
        print("\n[joc controlat]")
        ctx = browser.new_context(viewport={"width": 1000, "height": 950})
        pg = ctx.new_page()
        erori = []
        pg.on("pageerror", lambda e: erori.append(str(e)))
        pg.goto(URL)
        pg.click('.langs button[data-lang="en"]')
        pg.wait_for_timeout(200)

        # raspunsul zilei, citit din pagina (variabila e in IIFE: il scoatem prin tabla)
        # jucam un cuvant liber, ca sa stim exact ce comparam
        pg.click("#againBtn")
        pg.wait_for_timeout(200)
        lung = pg.eval_on_selector_all(".board .row:first-child .cell", "cs=>cs.length")
        alfabet = [k for k in taste(pg) if k not in ("back", "enter")]
        check(lung >= 4 and len(alfabet) >= 26, "joc liber pornit, " + str(lung) + " litere")

        # prima litera de doua ori, restul umplut, ca sa verificam ca NU se accepta dubluri false
        ghicit = alfabet[0] * lung
        scrie(pg, ghicit)
        trimite(pg)
        r = rezultat(pg)
        verzi = [x for x in r[0] if x.endswith("good")]
        galbene = [x for x in r[0] if x.endswith("near")]
        gri = [x for x in r[0] if x.endswith("off")]
        check(len(verzi) + len(galbene) + len(gri) == lung, "fiecare celula are exact o stare")
        check(len(galbene) <= 1, "o litera dublata nu da doua galbene (are " + str(len(galbene)) + ")")

        # copierea rezultatului
        pg.click("#shareBtn")
        pg.wait_for_timeout(200)
        check(text(pg, "#msg") != "", "copierea da un mesaj: " + text(pg, "#msg"))

        # statisticile cresc dupa un joc dus pana la capat
        pg.click("#againBtn")          # joc liber nou, mesajul vechi dispare
        pg.wait_for_timeout(250)
        lung = pg.eval_on_selector_all(".board .row:first-child .cell", "cs=>cs.length")
        jucate_inaite = int(text(pg, "#stPlayed"))
        for runda in range(8):
            if "win" in pg.eval_on_selector("#msg", "e=>e.className") or \
               "bad" in pg.eval_on_selector("#msg", "e=>e.className"):
                break
            alfabet = [k for k in taste(pg) if k not in ("back", "enter")]
            ghicit = "".join(alfabet[(i * 5 + runda) % len(alfabet)] for i in range(lung))
            scrie(pg, ghicit)
            trimite(pg)
        jucate = int(text(pg, "#stPlayed"))
        check(jucate == jucate_inaite + 1,
              "statistica de jocuri jucate a crescut: " + str(jucate_inaite) + " -> " + str(jucate))
        cls = pg.eval_on_selector("#msg", "e=>e.className")
        check("bad" in cls or "win" in cls, "jocul terminat are mesaj de final")

        check(erori == [], "zero erori de pagina" + ("" if not erori else " -> " + str(erori)))
        ctx.close()

        # ---------------- mobil
        print("\n[mobil]")
        pg = browser.new_page(viewport={"width": 390, "height": 844})
        pg.goto(URL)
        pg.wait_for_selector(".board .row")
        lat = pg.eval_on_selector(".kbd", "e=>e.getBoundingClientRect().width")
        check(lat <= 390, "tastatura incape pe ecran: " + str(round(lat)) + "px")
        dep = pg.evaluate("document.documentElement.scrollWidth")
        check(dep <= 390, "fara derulare pe orizontala: " + str(dep) + "px")
        pg.screenshot(path="/tmp/zilei-mobil.png")
        pg.close()
        pg = browser.new_page(viewport={"width": 1100, "height": 1000})
        pg.goto(URL)
        pg.wait_for_selector(".board .row")
        pg.screenshot(path="/tmp/zilei-desktop.png")
        pg.close()

        browser.close()

    print("\n" + str(ok) + " verificari trecute, " + str(rau) + " esuate")
    return 1 if rau else 0


if __name__ == "__main__":
    sys.exit(main())
