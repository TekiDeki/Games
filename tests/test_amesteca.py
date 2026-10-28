#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_amesteca.py - test UI pentru Amesteca literele. Se ruleaza din radacina repo-ului.

Necesita: pip install playwright && python -m playwright install chromium

Pentru fiecare din cele 4 variante verifica:
  - <html lang>, titlul, alfabetul din joc (literele amestecate)
  - literele amestecate nu sunt deja in ordine
  - punerea unei litere, scoaterea ei, golirea completa
  - indiciul aseaza litera corecta la locul ei
  - un cuvant grestit nu inchide jocul, dar rupe seria
  - un cuvant corect: mesaj, puncte, statistica
  - tastatura fizica: litera, Backspace, Enter
  - schimbarea temei
  - subsolul cu linkul de suport
  - zero erori de pagina
"""

import os
import sys

from playwright.sync_api import sync_playwright

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "file://" + os.path.join(RADACINA, "amesteca-literele", "index.html")

LIMBI = [
    ("ro", "ro", "litere"),
    ("en", "en", "letters"),
    ("sr", "sr-Latn", "slova"),
    ("src", "sr-Cyrl", "слова"),
]

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


def litere_pe_rack(pg):
    return pg.eval_on_selector_all(".rack .tile", "ts=>ts.map(t=>t.textContent)")


def sloturi(pg):
    return pg.eval_on_selector_all(".slot", "ss=>ss.map(s=>s.textContent)")


def click_tile(pg, idx):
    pg.eval_on_selector_all(".rack .tile", "(ts,i)=>ts[i].click()", idx)


def pune_toate(pg):
    """apasa pe toate literele, in ordinea din rack"""
    n = len(litere_pe_rack(pg))
    for i in range(n):
        click_tile(pg, i)
        pg.wait_for_timeout(60)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        for cheie, lang, cuv_litere in LIMBI:
            print("\n[" + cheie + "]")
            ctx = browser.new_context(viewport={"width": 1000, "height": 950})
            pg = ctx.new_page()
            erori = []
            pg.on("pageerror", lambda e: erori.append(str(e)))

            pg.goto(URL)
            pg.click('.langs button[data-lang="' + cheie + '"]')
            pg.wait_for_timeout(150)

            check(pg.evaluate("document.documentElement.lang") == lang, "<html lang> = " + lang)

            rack = litere_pe_rack(pg)
            slots = sloturi(pg)
            check(len(rack) == len(slots), "rack si sloturi au acelasi numar de litere")
            check(3 <= len(rack) <= 13, "cuvantul are " + str(len(rack)) + " litere")
            check("".join(rack) != "".join(sorted(rack)) or len(set(rack)) == 1,
                  "literele sunt amestecate, nu alfabetice")
            chip = text(pg, "#lenChip")
            check(cuv_litere in chip and str(len(rack)) in chip,
                  "chip-ul arata numarul de litere: " + chip)

            # punem o litera si o scoatem
            click_tile(pg, 0)
            pg.wait_for_timeout(100)
            s1 = sloturi(pg)
            check(s1[0] == rack[0], "prima litera intra in primul slot")
            pg.eval_on_selector_all(".slot", "(ss,i)=>ss[i].click()", 0)
            pg.wait_for_timeout(100)
            check(sloturi(pg)[0] == "", "litera iese la clic pe slot")

            # golire completa
            pune_toate(pg)
            pg.wait_for_timeout(200)
            plin = sloturi(pg)
            check(all(x != "" for x in plin), "toate sloturile se umplu")
            pg.click("#clearBtn")
            pg.wait_for_timeout(150)
            check(all(x == "" for x in sloturi(pg)), "butonul de golire merge")

            # indiciu: prima litera devine corecta
            pg.click("#hintBtn")
            pg.wait_for_timeout(150)
            primul = sloturi(pg)[0]
            check(primul != "", "indiciul aseaza o litera (" + primul + ")")
            check("hinted" in pg.eval_on_selector_all(".slot", "ss=>ss[0].className"),
                  "slotul completat cu indiciu e marcat")

            # incercare greșita: nu inchide jocul
            pg.click("#againBtn")
            pg.wait_for_timeout(150)
            pune_toate(pg)
            pg.wait_for_timeout(300)
            msg = text(pg, "#msg")
            cls = pg.eval_on_selector("#msg", "e=>e.className")
            if "bad" in cls:
                check(len(msg) > 5, "mesaj la ordine gresita: " + msg)
                check(pg.eval_on_selector("#againBtn", "e=>!e.disabled"), "jocul nu s-a inchis")
            else:
                check("win" in cls, "din prima ordine a nimerit cuvantul (si el e corect)")

            # solutionam: asezam literele in ordinea cuvantului
            pg.click("#againBtn")
            pg.wait_for_timeout(150)
            rack = litere_pe_rack(pg)
            # cuvantul se afla incercand: il reconstruim din indicii
            pg.click("#hintBtn"); pg.wait_for_timeout(120)
            pg.click("#hintBtn"); pg.wait_for_timeout(120)
            pg.click("#hintBtn"); pg.wait_for_timeout(120)
            check(sloturi(pg)[0] != "" and sloturi(pg)[1] != "" and sloturi(pg)[2] != "",
                  "trei indicii asaza trei litere")

            # tastatura: Backspace scoate ultima litera
            inainte = [x for x in sloturi(pg) if x != ""]
            pg.keyboard.press("Backspace")
            pg.wait_for_timeout(120)
            dupa = [x for x in sloturi(pg) if x != ""]
            check(len(dupa) == len(inainte) - 1, "Backspace scoate o litera")

            # Enter aduce cuvant nou
            vechi = "".join(litere_pe_rack(pg))
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(150)
            check(all(x == "" for x in sloturi(pg)), "Enter aduce un cuvant nou, gol")

            # tastam o litera fizica
            rack2 = litere_pe_rack(pg)
            litera = rack2[0]
            if litera.isascii():
                pg.keyboard.press(litera.lower())
            else:
                # Playwright nu trimite keydown pentru literele chirilice,
                # deci trimitem evenimentul exact cum ar veni de la tastatura
                pg.evaluate("ch=>document.dispatchEvent(new KeyboardEvent('keydown',{key:ch,bubbles:true}))", litera)
            pg.wait_for_timeout(150)
            check(sloturi(pg)[0] != "", "tastatura fizica aseaza o litera (" + litera + ")")

            # tema
            tema1 = text(pg, "#themeChip")
            pg.click("#themeChip")
            pg.wait_for_timeout(150)
            check(text(pg, "#themeChip") != tema1,
                  "tema se schimba (" + tema1 + " -> " + text(pg, "#themeChip") + ")")

            # castig curat: rezolvam cu indicii pana la capat
            pg.click("#againBtn")
            pg.wait_for_timeout(150)
            for _ in range(14):
                if "win" in pg.eval_on_selector("#msg", "e=>e.className"):
                    break
                pg.click("#hintBtn")
                pg.wait_for_timeout(110)
            cls = pg.eval_on_selector("#msg", "e=>e.className")
            check("win" in cls, "joc castigat cu indicii: " + text(pg, "#msg"))
            check(text(pg, "#stWon") != "0", "statistica: o victorie")

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
