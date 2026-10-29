#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_perechi.py - test UI pentru Perechi de cuvinte. Se ruleaza din radacina repo-ului.

Necesita: pip install playwright && python -m playwright install chromium

Pentru fiecare din cele 4 variante verifica:
  - <html lang>, titlul, canonical
  - tabla are 2 x numarul de perechi de carti, toate cu "?" pe spate
  - o pereche găsită rămâne deschisă, o nepotrivire se întoarce
  - joc câștigat: toate perechile găsite, mesaj, statistică
  - butonul de arătat tot descoperă tabla și costă o mutare
  - schimbarea temei și a mărimii tablei
  - subsolul cu linkul de suport
  - zero erori de pagina
"""

import os
import sys

from playwright.sync_api import sync_playwright

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "file://" + os.path.join(RADACINA, "word-pairs", "index.html")

LIMBI = [
    ("ro", "ro", "perechi"),
    ("en", "en", "pairs"),
    ("sr", "sr-Latn", "parova"),
    ("src", "sr-Cyrl", "парова"),
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


def perechi_pe_tabla(pg):
    """intoarce lista [(index, cuvant)] din fata fiecarei carti"""
    return pg.eval_on_selector_all(
        ".tile", "ts=>ts.map((t,i)=>[i, t.querySelector('.face.front').textContent])")


def deschide(pg, idx):
    pg.eval_on_selector_all(".tile", "(ts,i)=>ts[i].click()", idx)


def rezolva_tot(pg):
    """joaca tabela pana la capat, fara sa greseasca"""
    carti = perechi_pe_tabla(pg)
    grup = {}
    for i, w in carti:
        grup.setdefault(w, []).append(i)
    for w, idx in grup.items():
        for i in idx:
            pg.eval_on_selector_all(".tile", "(ts,i)=>ts[i].click()", i)
            pg.wait_for_timeout(90)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        for cheie, lang, cuv_pereche in LIMBI:
            print("\n[" + cheie + "]")
            ctx = browser.new_context(viewport={"width": 1000, "height": 950})
            pg = ctx.new_page()
            erori = []
            pg.on("pageerror", lambda e: erori.append(str(e)))

            pg.goto(URL)
            pg.click('.langs button[data-lang="' + cheie + '"]')
            pg.wait_for_timeout(150)

            check(pg.evaluate("document.documentElement.lang") == lang,
                  "<html lang> = " + lang)
            # link de intoarcere la hub-ul de jocuri
            check(pg.get_attribute("#homeBtn", "href") == "../", "linkul spre hub are href ../")
            check(pg.is_visible("#homeBtn"), "linkul spre hub e vizibil")
            check(pg.inner_text("#homeLbl") == HOME[cheie],
                  "eticheta linkului in " + cheie + ": " + pg.inner_text("#homeLbl"))
            check(len((pg.get_attribute("#homeBtn", "aria-label") or "").strip()) > 3,
                  "linkul spre hub are aria-label tradus")

            chip = text(pg, "#sizeChip").lower()
            check(cuv_pereche in chip and "6" in chip,
                  "chip-ul de marime e tradus si arata 6: " + text(pg, "#sizeChip"))

            carti = perechi_pe_tabla(pg)
            check(len(carti) == 12, "implicit 6 perechi = 12 carti (are " + str(len(carti)) + ")")
            check(len(set(w for _, w in carti)) == 6, "exact 6 cuvinte distincte")
            spate = pg.eval_on_selector_all(".tile .face.back", "bs=>bs.every(b=>b.textContent==='?')")
            check(spate, "toate cartile incep cu spatele")

            # o pereche găsită rămâne deschisă
            w0 = carti[0][1]
            idx0 = [i for i, w in carti if w == w0]
            deschide(pg, idx0[0]); pg.wait_for_timeout(120)
            deschide(pg, idx0[1]); pg.wait_for_timeout(200)
            cls = pg.eval_on_selector_all(".tile", "(ts,i)=>ts[i].className", idx0[0])
            check("done" in cls, "perechea găsită rămâne deschisă")

            # o nepotrivire se întoarce la loc
            ramase = [i for i, w in carti if w != w0]
            a = ramase[0]
            # a doua carte trebuie sa fie SIGUR alt cuvant, altfel verificarea ar fi sarita aleator
            b = next(i for i in ramase[1:] if carti[i][1] != carti[a][1])
            deschide(pg, a); pg.wait_for_timeout(120)
            deschide(pg, b); pg.wait_for_timeout(950)
            cls2 = pg.eval_on_selector_all(".tile", "(ts,i)=>ts[i].className", a)
            check("open" not in cls2, "nepotrivirea se intoarce cu spatele")

            # arata tot
            mutari_inainte = int(text(pg, "#movesChip").split(": ")[1])
            pg.click("#peekBtn"); pg.wait_for_timeout(250)
            deschise = pg.eval_on_selector_all(".tile", "ts=>ts.filter(t=>t.className.includes('open')).length")
            check(deschise >= 8, "butonul arata tabla (" + str(deschise) + " carti deschise)")
            pg.wait_for_timeout(900)
            mutari_dupa = int(text(pg, "#movesChip").split(": ")[1])
            check(mutari_dupa == mutari_inainte + 1, "aratatul costa o mutare")

            # tema si marimea
            tema1 = text(pg, "#themeChip")
            pg.click("#themeChip"); pg.wait_for_timeout(200)
            check(text(pg, "#themeChip") != tema1, "tema se schimba (" + tema1 + " -> " + text(pg, "#themeChip") + ")")

            pg.click("#sizeChip"); pg.wait_for_timeout(200)
            check(len(perechi_pe_tabla(pg)) == 16, "marimea creste la 8 perechi = 16 carti")
            pg.click("#sizeChip"); pg.wait_for_timeout(200)
            check(len(perechi_pe_tabla(pg)) == 8, "marimea scade la 4 perechi = 8 carti")

            # joc nou curat si castig
            pg.click("#againBtn"); pg.wait_for_timeout(200)
            check(len(perechi_pe_tabla(pg)) == 8, "jocul nou pastreaza marimea aleasa")
            rezolva_tot(pg)
            pg.wait_for_timeout(400)
            msg = text(pg, "#msg")
            check(len(msg) > 10, "mesaj de final: " + msg)
            check("win" in pg.eval_on_selector("#msg", "e=>e.className"), "mesajul e marcat ca victorie")
            check(text(pg, "#stPlayed") == "1", "statistica: un joc jucat")
            check(text(pg, "#stWon") == "1", "statistica: un joc castigat")
            check(text(pg, "#stBest") != "0", "recordul se salveaza")

            # subsol
            href = pg.eval_on_selector("#supportLink", "e=>e.href")
            check("paypal.me/TekiDeki" in href, "link de suport corect")
            check(len(text(pg, "footer")) > 40, "subsolul are text tradus")

            check(len(erori) == 0, "zero erori de pagina " + str(erori))
            ctx.close()

        browser.close()

    print("\n" + str(ok) + " verificari trecute, " + str(rau) + " esuate")
    return 1 if rau else 0


if __name__ == "__main__":
    sys.exit(main())
