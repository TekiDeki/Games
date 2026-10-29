#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_ui.py - test UI pentru joc. Se ruleaza din radacina repo-ului.

Necesita: pip install playwright && python -m playwright install chromium

Pentru fiecare din cele 4 variante verifica:
  - limba pe <html>, alfabetul tastaturii (numar si unicitate)
  - un castig real (dezvaluind literele cu indiciul, care nu costa vieti)
  - un joc dus pana la capat, cu mesajul potrivit pentru rezultat
  - schimbarea temei
  - linkul de suport din subsol
  - zero erori de pagina
"""

import os
import sys

from playwright.sync_api import sync_playwright

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "file://" + os.path.join(RADACINA, "ghiceste-cuvantul", "index.html")

LIMBI = [
    ("ro", "ro", 31),
    ("en", "en", 26),
    ("sr", "sr-Latn", 27),
    ("src", "sr-Cyrl", 30),
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


def umplute(pg):
    return pg.eval_on_selector("#word", "e=>[...e.children].filter(c=>c.textContent).length")


def toate(pg):
    return pg.eval_on_selector("#word", "e=>e.children.length")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        for cheie, lang_asteptat, nr_litere in LIMBI:
            print("\n[" + cheie + "]")
            ctx = browser.new_context(viewport={"width": 900, "height": 950})
            pg = ctx.new_page()
            erori = []
            pg.on("pageerror", lambda e: erori.append(str(e)))

            pg.goto(URL)
            pg.click('.langs button[data-lang="' + cheie + '"]')
            pg.wait_for_timeout(150)

            check(pg.evaluate("document.documentElement.lang") == lang_asteptat,
                  "<html lang> = " + lang_asteptat)
            # link de intoarcere la hub-ul de jocuri
            check(pg.get_attribute("#homeBtn", "href") == "../", "linkul spre hub are href ../")
            check(pg.is_visible("#homeBtn"), "linkul spre hub e vizibil")
            check(pg.inner_text("#homeLbl") == HOME[cheie],
                  "eticheta linkului in " + cheie + ": " + pg.inner_text("#homeLbl"))
            check(len((pg.get_attribute("#homeBtn", "aria-label") or "").strip()) > 3,
                  "linkul spre hub are aria-label tradus")


            taste = pg.eval_on_selector_all(".key", "ks=>ks.map(k=>k.dataset.k)")
            check(len(taste) == nr_litere,
                  "alfabet " + str(nr_litere) + " litere (are " + str(len(taste)) + ")")
            check(len(set(taste)) == len(taste), "fara litere duplicate")

            n = toate(pg)
            check(3 <= n <= 13, "cuvantul are " + str(n) + " litere")

            # castig garantat: indiciul dezvaluie litere fara sa coste vieti
            for _ in range(20):
                if umplute(pg) == toate(pg):
                    break
                pg.click("#hintBtn")
                pg.wait_for_timeout(60)
            cuvant = text(pg, "#word")
            mesaj = text(pg, "#msg")
            check(umplute(pg) == toate(pg), "toate literele dezvaluite")
            check(cuvant in mesaj, "mesajul de castig contine cuvantul (" + cuvant + ")")
            check(text(pg, "#stWon") == "1", "statistica: o victorie")

            # runda noua: jucata pana la capat, oricum s-ar termina
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(100)
            for ch in taste:
                if text(pg, "#msg"):
                    break
                el = pg.query_selector('.key[data-k="' + ch + '"]')
                if el and not el.is_disabled():
                    el.click()
            cls = pg.eval_on_selector("#msg", "e=>e.className")
            check("win" in cls or "lose" in cls, "jocul se termina cu mesaj clar")
            check(text(pg, "#stPlayed") == "2", "statistica: doua jocuri jucate")

            # tema
            tema1 = text(pg, "#themeChip")
            pg.click("#themeChip")
            pg.wait_for_timeout(80)
            tema2 = text(pg, "#themeChip")
            check(tema1 != tema2, "tema se schimba (" + tema1 + " -> " + tema2 + ")")

            # subsol
            href = pg.eval_on_selector("#supportLink", "e=>e.href")
            check("paypal.me/TekiDeki" in href, "link de suport corect")
            check(len(text(pg, "footer")) > 40, "subsolul are text tradus")

            check(len(erori) == 0, "zero erori de pagina " + str(erori))
            ctx.close()

        # pagina hub
        print("\n[hub]")
        pg = browser.new_page()
        pg.goto("file://" + os.path.join(RADACINA, "index.html"))
        check("Ghiceste" in pg.content() or "Guess the word" in pg.content(),
              "hub-ul listeaza jocul")
        link = pg.eval_on_selector('a.card[href]', "e=>e.getAttribute('href')")
        check(link == "ghiceste-cuvantul/", "link relativ corect: " + link)
        carduri = pg.eval_on_selector_all("a.card[href]", "as=>as.map(a=>a.getAttribute('href'))")
        check(carduri == ["ghiceste-cuvantul/", "perechi-cuvinte/", "amesteca-literele/", "cuvantul-zilei/"],
              "hub-ul listeaza toate cele 4 jocuri: " + ", ".join(carduri))
        for cale in carduri:
            check(os.path.exists(os.path.join(RADACINA, cale, "index.html")),
                  "fisierul din card exista: " + cale)
        browser.close()

    print("\n" + str(ok) + " verificari trecute, " + str(rau) + " esuate")
    return 1 if rau else 0


if __name__ == "__main__":
    sys.exit(main())
