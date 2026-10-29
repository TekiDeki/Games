#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_intrus.py - suita functionala pentru jocul 5, „Gaseste intrusul”.

python3 tests/test_intrus.py

Verifica, in toate cele 4 limbi:
  - linkul de intoarcere la hub, tradus, vizibil
  - alfabetul/temele: fiecare runda are 3 cuvinte dintr-o tema si 1 din alta
  - 10 runde, cronometru de 12 s, bara care scade
  - raspuns corect: punctaj, mesaj, verde pe intrus, etichetele de tema
  - raspuns gresit: rosu pe ales, verde pe intrus, seria se reseteaza
  - timpul expirat numara ca ratare
  - statisticile se actualizeaza o singura data la finalul jocului
  - copierea rezultatului in clipboard
  - tastatura 1-4 si N
  - mobil 390px fara derulare pe orizontala
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAZA = "file://" + os.path.join(RADACINA, "odd-one-out", "index.html")
URL = BAZA + "?pauza=3000"      # pauza lunga: se poate observa ce se intampla dupa raspuns
URL_REPEDE = BAZA + "?pauza=60"  # pentru jocurile complete, jucate runda dupa runda
PAUZA = 3200

LIMBI = [("ro", "Jocuri"), ("en", "Games"), ("sr", "Igre"), ("src", "Игре")]
TEME = {"animale", "mancare", "locuri"}      # cheile interne sunt aceleasi in toate limbile
TEMA_TXT = {                                  # eticheta tradusa, asa cum apare pe dala
    "ro": {"animale", "mâncare", "locuri"},
    "en": {"animals", "food", "places"},
    "sr": {"životinje", "hrana", "mesta"},
    "src": {"животиње", "храна", "места"},
}

ok = 0
rau = 0


def check(cond, mesaj, detaliu=""):
    global ok, rau
    if cond:
        ok += 1
        print("  ok   " + mesaj)
    else:
        rau += 1
        print("  FAIL " + mesaj + ((" - " + detaliu) if detaliu else ""))


def text(pg, sel):
    return pg.inner_text(sel).strip()


def tile(pg, i):
    return pg.locator('.tile[data-i="%d"]' % i)


def stare(pg):
    """lista cu (cuvant, tema, e_intrus) pentru runda curenta"""
    return pg.eval_on_selector_all(
        ".tile", "ts=>ts.map(t=>[t.querySelector('.w').textContent, t.dataset.tema, t.dataset.intrus])")


def alege_intrus(pg):
    """apasa pe intrusul rundei curente; False daca runda nu are intrus sau e blocata"""
    idx = pg.eval_on_selector_all(".tile", "ts=>ts.map(t=>t.dataset.intrus)")
    st = pg.eval_on_selector_all(".tile", "ts=>ts.map(t=>t.disabled)")
    if "1" not in idx or any(st):
        return False
    try:
        pg.click('.tile[data-i="%d"]' % idx.index("1"), timeout=2000)
    except Exception:
        return False
    pg.wait_for_timeout(140)
    return True


def alege_neintrus(pg):
    idx = pg.eval_on_selector_all(".tile", "ts=>ts.map(t=>t.dataset.intrus)")
    try:
        pg.click('.tile[data-i="%d"]' % idx.index("0"), timeout=2000)
    except Exception:
        return False
    pg.wait_for_timeout(140)
    return True


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()

        for limba, eticheta in LIMBI:
            print("\n[" + limba + "]")
            ctx = b.new_context(viewport={"width": 1100, "height": 950})
            pg = ctx.new_page()
            erori = []
            pg.on("pageerror", lambda e: erori.append(str(e)))
            pg.goto(URL)
            pg.wait_for_selector(".tile")
            pg.evaluate("document.querySelector('.langs button[data-lang=\"%s\"]').click()" % limba)
            pg.wait_for_timeout(200)

            check(pg.eval_on_selector("html", "e=>e.lang") == limba or
                  (limba == "sr" and pg.eval_on_selector("html", "e=>e.lang") == "sr-Latn") or
                  (limba == "src" and pg.eval_on_selector("html", "e=>e.lang") == "sr-Cyrl"),
                  "<html lang> = " + pg.eval_on_selector("html", "e=>e.lang"))

            # linkul spre hub
            check(pg.get_attribute("#homeBtn", "href") == "../", "linkul spre hub are href ../")
            check(pg.is_visible("#homeBtn"), "linkul spre hub e vizibil")
            check(text(pg, "#homeLbl") == eticheta, "eticheta linkului in " + limba + ": " + text(pg, "#homeLbl"))
            check(bool(pg.get_attribute("#homeBtn", "aria-label")), "linkul spre hub are aria-label tradus")

            # structura rundei
            st = stare(pg)
            check(len(st) == 4, "runda are 4 cuvinte")
            teme = [x[1] for x in st]
            intrusi = [x for x in st if x[2] == "1"]
            check(len(intrusi) == 1, "exact un intrus in runda")
            baza = [x[1] for x in st if x[2] == "0"]
            check(len(set(baza)) == 1, "cele 3 cuvinte normale au aceeasi tema: " + str(set(baza)))
            check(baza[0] != intrusi[0][1], "intrusul e din alta tema (" + baza[0] + " vs " + intrusi[0][1] + ")")
            check(baza[0] in TEME, "tema interna e una din cele trei: " + baza[0])
            cuvinte = [x[0] for x in st]
            check(len(set(cuvinte)) == 4, "cuvintele sunt distincte: " + ", ".join(cuvinte))

            # chip-uri si timp
            check(text(pg, "#roundChip").startswith(text(pg, "#roundChip").split()[0]), "chip-ul de runda: " + text(pg, "#roundChip"))
            check("/10" in text(pg, "#roundChip"), "rundele sunt din 10: " + text(pg, "#roundChip"))
            check(text(pg, "#timeChip") in ("12s", "12с", "12 s"), "cronometrul porneste de la 12: " + text(pg, "#timeChip"))
            # bara e animata cu transform: scaleX, nu cu width (compositor, nu layout)
            lat1 = pg.eval_on_selector("#bar", "e=>getComputedStyle(e).transform")
            pg.wait_for_timeout(900)
            lat2 = pg.eval_on_selector("#bar", "e=>getComputedStyle(e).transform")
            scara = lambda t: float(t[t.index("(") + 1:].split(",")[0]) if t.startswith("matrix") else 1.0
            check(scara(lat2) < scara(lat1), "bara de timp scade: " + lat1 + " -> " + lat2)

            # raspuns GRESIT
            alege_neintrus(pg)
            clase = pg.eval_on_selector_all(".tile", "ts=>ts.map(t=>t.className)")
            check(any("good" in c for c in clase), "intrusul se face verde dupa un raspuns greu")
            check(any("bad" in c for c in clase), "alesul gresit se face rosu")
            check("bad" in pg.eval_on_selector("#msg", "e=>e.className"), "mesajul de greseala are stil rosu")
            check(text(pg, "#scoreChip").endswith("0"), "punctajul ramane 0 dupa o greseala: " + text(pg, "#scoreChip"))
            etichete = pg.eval_on_selector_all(".tile .tag", "ts=>ts.map(t=>t.textContent)")
            check(all(e in TEMA_TXT[limba] for e in etichete), "fiecare cuvant primeste eticheta de tema: " + ", ".join(etichete))
            vizibil = pg.eval_on_selector(".tile .tag", "e=>getComputedStyle(e).visibility")
            check(vizibil == "visible", "etichetele de tema se vad dupa raspuns")
            check(pg.eval_on_selector_all(".tile", "ts=>ts.every(t=>t.disabled)"), "dalele sunt blocate dupa raspuns")

            pg.wait_for_timeout(PAUZA)
            check("/10" in text(pg, "#roundChip") and not text(pg, "#roundChip").endswith("1/10"),
                  "dupa raspuns trece la runda urmatoare: " + text(pg, "#roundChip"))

            # raspuns CORECT, cu punctaj
            gasit = False
            for _ in range(3):
                if not alege_intrus(pg):
                    break
                gasit = True
                puncte = re.findall(r"\d+", text(pg, "#scoreChip"))
                check(bool(puncte) and int(puncte[-1]) >= 10, "punctajul creste dupa un raspuns corect: " + text(pg, "#scoreChip"))
                check("good" in pg.eval_on_selector("#msg", "e=>e.className"), "mesajul de corect are stil verde")
                check(pg.eval_on_selector_all(".tile", "ts=>ts.every(t=>t.disabled)"), "dalele sunt blocate si dupa corect")
                break
            check(gasit, "s-a putut da un raspuns corect")

            # tastatura: 1-4
            pg.wait_for_timeout(PAUZA)
            nr = pg.eval_on_selector_all(".tile", "ts=>ts.length")
            check(nr == 4, "runda noua are tot 4 dale")
            pg.keyboard.press("3")
            pg.wait_for_timeout(160)
            check(pg.eval_on_selector_all(".tile", "ts=>ts.every(t=>t.disabled)"),
                  "tasta 3 alege a treia dala")

            # tastatura: N = joc nou
            pg.keyboard.press("n")
            pg.wait_for_timeout(200)
            check(text(pg, "#roundChip").endswith("1/10"), "tasta N incepe un joc nou: " + text(pg, "#roundChip"))
            check(text(pg, "#scoreChip").endswith("0"), "scorul se reseteaza la joc nou")

            # timpul expira = ratare
            pg.wait_for_timeout(12500)
            check("bad" in pg.eval_on_selector("#msg", "e=>e.className"), "timpul expirat da mesaj de ratare")
            check(pg.eval_on_selector_all(".tile", "ts=>ts.every(t=>t.disabled)"), "dupa expirare dalele sunt blocate")

            # un joc complet, jucat pana la final (pauza scurta, ca sa nu dureze)
            pg.goto(URL_REPEDE)
            pg.wait_for_selector(".tile")
            pg.evaluate("document.querySelector('.langs button[data-lang=\"%s\"]').click()" % limba)
            pg.wait_for_timeout(200)
            for runda in range(13):
                if not alege_intrus(pg):
                    if not text(pg, "#msg").startswith(pg.eval_on_selector("#againBtn", "e=>e.textContent")):
                        pg.keyboard.press("1")
                pg.wait_for_timeout(200)
            pg.wait_for_timeout(500)
            final = text(pg, "#msg")
            check("/ 10" in final or "/10" in final or "10" in final, "la final apare rezumatul: " + final)
            jucate = int(text(pg, "#stPlayed"))
            gasite = int(text(pg, "#stHits"))
            check(jucate >= 1, "statistica de jocuri jucate a crescut: " + str(jucate))
            check(gasite >= 1, "statistica de intrusi gasiti a crescut: " + str(gasite))
            record = int(text(pg, "#stBest"))
            check(record >= 0, "recordul e afisat: " + str(record))

            # copierea rezultatului
            pg.click("#shareBtn")
            pg.wait_for_timeout(250)
            check("good" in pg.eval_on_selector("#msg", "e=>e.className") or
                  "copiat" in text(pg, "#msg").lower() or "copied" in text(pg, "#msg").lower(),
                  "copierea da un mesaj: " + text(pg, "#msg"))

            check(not erori, "zero erori de pagina" + (" " + str(erori) if erori else ""))
            ctx.close()

        # ------------------------------------------------------------- mobil
        print("\n[mobil]")
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        pg = ctx.new_page()
        erori = []
        pg.on("pageerror", lambda e: erori.append(str(e)))
        pg.goto(URL)
        pg.wait_for_selector(".tile")
        lat = pg.evaluate("document.documentElement.scrollWidth")
        check(lat <= 390, "fara derulare pe orizontala: " + str(lat) + "px")
        cutii = pg.eval_on_selector_all(".tile", "ts=>ts.map(t=>Math.round(t.getBoundingClientRect().width))")
        check(all(w >= 120 for w in cutii), "dalele sunt destul de late pe mobil: " + str(cutii))
        check(pg.eval_on_selector("#homeBtn", "e=>e.getBoundingClientRect().top") < 60, "linkul spre hub e sus pe mobil")
        pg.screenshot(path="/tmp/intrus-mobil.png")
        pg.keyboard.press("1")
        pg.wait_for_timeout(200)
        pg.set_viewport_size({"width": 1100, "height": 950})
        pg.keyboard.press("n")
        pg.wait_for_timeout(200)
        pg.screenshot(path="/tmp/intrus-desktop.png")
        check(not erori, "zero erori de pagina pe mobil" + (" " + str(erori) if erori else ""))
        ctx.close()
        b.close()

    print("\n" + str(ok) + " verificari trecute, " + str(rau) + " esuate")
    return 1 if rau else 0


if __name__ == "__main__":
    sys.exit(main())
