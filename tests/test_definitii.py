#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_definitii.py - jocul „Word from definition".

De ce exista: pagina asta nu se joaca din liste de cuvinte, ci din definitii aduse de altundeva.
Un joc de vocabular poate fi stricat in feluri pe care celelalte teste nu le vad - definitia isi
poate spune raspunsul, pot fi doua variante bune, sau textul poate veni in alta limba decat fila.
Testul joaca runde pe bune si verifica exact lucrurile astea.

Se ruleaza din radacina repo-ului: python3 tests/test_definitii.py
"""
import os
import re
import sys
import unicodedata

from playwright.sync_api import sync_playwright

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "file://" + os.path.join(RADACINA, "word-from-definition", "index.html")
LIMBI = ["en", "ro", "sr", "src"]

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


def norm(text):
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def nu_isi_spune_raspunsul(cuvant, definitie):
    """Definitia nu are voie sa contina raspunsul ca vorbă intreaga, nici ca tulpina.

    Comparatia pe litere lipite ar da fals pozitiv: „med” apare in „medonosnih”, iar
    „коњ” in „коњима”, fara ca jucatorul sa vada raspunsul. Se compara deci cuvant cu
    cuvant, iar pentru cuvintele lungi si primele patru litere („овце” fata de „овца”).
    """
    w = [x for x in re.split(r"[^0-9a-zа-яђћџшčćžšđ]+", norm(cuvant)) if x]
    d = [x for x in re.split(r"[^0-9a-zа-яђћџшčćžšđ]+", norm(definitie)) if x]
    if not w or not d:
        return True
    if w[0] in d:
        return False
    prag = max(5, len(w[0]) - 2)          # „cârnați” nu e spus de „carne”, nici „мед” de „медоносних”
    if len(w[0]) >= 5 and any(len(x) >= prag and x.startswith(w[0][:prag]) for x in d):
        return False
    return True


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])

        # ---- o singura fila, jucata pe bune ----
        ctx = browser.new_context(viewport={"width": 900, "height": 950}, locale="ro-RO")
        pg = ctx.new_page()
        erori, externe = [], []
        pg.on("pageerror", lambda e: erori.append(str(e)))
        pg.on("request", lambda r: externe.append(r.url)
              if not r.url.startswith(("file://", "data:")) else None)
        pg.goto(URL)
        pg.wait_for_timeout(250)

        def stare():
            return pg.evaluate("""() => ({
                limba, cuvant, blocat,
                def: document.getElementById('text').textContent,
                lang: document.getElementById('text').getAttribute('lang'),
                variante: [...document.querySelectorAll('#variante button')].map(b => b.textContent),
                categorie: DATE[limba][cuvant].categorie,
                limbaDef: DATE[limba][cuvant].limba_definitiei,
                evita: DATE[limba][cuvant].evita || [],
                scor: document.getElementById('scor').textContent})""")

        check(pg.evaluate("document.documentElement.lang") == "en", "prima vizita e in engleza")
        check(pg.get_attribute("#homeBtn", "href") == "../", "linkul spre hub are href ../")
        check(not externe, "zero cereri catre alt domeniu " + str(externe[:2]))

        vazute = {}
        for limba in LIMBI:
            pg.click('.langs button[data-lang="%s"]' % limba)
            pg.wait_for_timeout(120)
            vazute[limba] = set()
            for runda in range(6):
                s = stare()
                check(len(s["variante"]) == 4, "%s r%d: patru variante" % (limba, runda))
                check(s["variante"].count(s["cuvant"]) == 1, "%s r%d: raspunsul apare o data" % (limba, runda))
                check(len(set(s["variante"])) == 4, "%s r%d: variantele sunt distincte" % (limba, runda))
                check(nu_isi_spune_raspunsul(s["cuvant"], s["def"]),
                      "%s r%d: definitia nu isi spune raspunsul" % (limba, runda))
                pomenite = [w for w in s["evita"] if w in s["variante"]]
                check(not pomenite, "%s r%d: nicio varianta pomenita in definitie" % (limba, runda))
                check(s["lang"] == s["limbaDef"],
                      "%s r%d: limba definitiei e declarata in pagina" % (limba, runda))
                check(len(s["def"]) >= 3, "%s r%d: definitia nu e goala" % (limba, runda))
                vazute[limba].add(s["categorie"])
                # raspundem corect, apoi trecem mai departe
                pg.locator("#variante button", has_text=re.compile(
                    "^" + re.escape(s["cuvant"]) + "$")).first.click()
                pg.wait_for_timeout(40)
                check(pg.eval_on_selector_all("#variante button", "bs => bs.every(b => b.disabled)"),
                      "%s r%d: dupa raspuns butoanele se blocheaza" % (limba, runda))
                pg.click("#urmator")
                pg.wait_for_timeout(30)
            check(re.match(r"6\s+(din|of|od|од)\s+6", stare()["scor"]) is not None,
                  "%s: scorul arata 6 din 6 (" % limba + stare()["scor"] + ")")
            check(len(vazute[limba]) >= 1, "%s: s-a jucat pe cel putin o tema" % limba)

        # ---- reset ----
        pg.click("#reset")
        pg.wait_for_timeout(80)
        check(re.match(r"0\s+(din|of|od|од)\s+0", stare()["scor"]) is not None, "resetul aduce scorul la zero")
        check(not pg.eval_on_selector_all("#variante button", "bs => bs.some(b => b.disabled)"),
              "resetul reactiveaza variantele")
        pg.keyboard.press("r")
        pg.wait_for_timeout(60)
        check(re.match(r"0\s+(din|of|od|од)\s+0", stare()["scor"]) is not None, "tasta R reseteaza")

        # ---- tastatura ----
        s = stare()
        pg.keyboard.press(str(s["variante"].index(s["cuvant"]) + 1))
        pg.wait_for_timeout(60)
        check(pg.evaluate("() => blocat") is True, "tasta 1-4 raspunde")
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(60)
        check(pg.evaluate("() => blocat") is False, "Enter trece la urmatoarea intrebare")

        # ---- tema ----
        fundal = pg.evaluate("getComputedStyle(document.body).backgroundColor")
        pg.click("#themeBtn")
        pg.wait_for_timeout(120)
        check(pg.evaluate("getComputedStyle(document.body).backgroundColor") != fundal, "butonul de tema schimba culorile")
        check(pg.evaluate("() => document.documentElement.getAttribute('data-theme')") in ("light", "dark"),
              "tema aleasa se scrie in pagina")
        pg.click("#themeBtn")
        pg.wait_for_timeout(100)

        check(not erori, "nicio eroare de pagina " + str(erori[:2]))
        check(not externe, "jocul nu face nicio cerere in afara paginii " + str(externe[:2]))
        ctx.close()

        # ---- pe mobil ----
        ctx = browser.new_context(viewport={"width": 380, "height": 800})
        pg = ctx.new_page()
        pg.goto(URL)
        pg.wait_for_timeout(200)
        latime = pg.evaluate("() => document.documentElement.scrollWidth")
        check(latime <= 380, "pe mobil nu deruleaza in lateral (" + str(latime) + "px)")
        marimi = pg.eval_on_selector_all("#themeBtn, #reset, #supportLink, #report",
                                         "els => els.map(e => { const r = e.getBoundingClientRect(); "
                                         "return [Math.round(r.width), Math.round(r.height)]; })")
        check(all(w >= 24 and h >= 24 for w, h in marimi), "tinte de minim 24x24 (" + str(marimi) + ")")
        ctx.close()
        browser.close()

    print("\n" + str(ok) + " verificari trecute, " + str(rau) + " esuate")
    return 0 if rau == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
