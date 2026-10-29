#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_limba.py - limba la prima vizita: ENGLEZA, indiferent de limba browserului.

Regula casei (29.10.2026): engleza e limba principala, deci un link deschis prima data
trebuie sa arate pagina in engleza, oricare ar fi limba din browser. Alegerea facuta de
vizitator se pastreaza in localStorage si trece peste regula.

Se ruleaza din radacina repo-ului: python3 tests/test_limba.py
"""

import os

from playwright.sync_api import sync_playwright

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOCURI = ["guess-the-word", "word-pairs", "word-scramble", "word-of-the-day", "odd-one-out", "word-search"]
# limbi de browser pe care legea veche le-ar fi lasat sa treaca: ro si sarba (latin + chirilic)
LOCALE = ["ro-RO", "sr-RS", "sr-Cyrl-RS", "de-DE", "en-US"]

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


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        for joc in JOCURI:
            url = "file://" + os.path.join(RADACINA, joc, "index.html")
            print("\n[" + joc + "]")
            for loc in LOCALE:
                ctx = browser.new_context(locale=loc)
                pg = ctx.new_page()
                erori = []
                pg.on("pageerror", lambda e: erori.append(str(e)))
                pg.goto(url)
                pg.wait_for_timeout(120)
                lang = pg.evaluate("document.documentElement.lang")
                check(lang == "en", "browser " + loc + " -> limba paginii " + lang + " (asteptat en)")
                check(not erori, "zero erori de pagina (" + loc + ")")
                ctx.close()

            # alegerea vizitatorului trece peste regula si se pastreaza
            ctx = browser.new_context(locale="ro-RO")
            pg = ctx.new_page()
            pg.goto(url)
            pg.wait_for_timeout(100)
            pg.click('.langs button[data-lang="ro"]')
            pg.wait_for_timeout(120)
            check(pg.evaluate("document.documentElement.lang") == "ro",
                  "dupa clic pe RO, limba paginii devine ro")
            pg.reload()
            pg.wait_for_timeout(150)
            check(pg.evaluate("document.documentElement.lang") == "ro",
                  "dupa reincarcare ramane ro (alegerea vizitatorului)")
            ctx.close()

        browser.close()

    print("\n" + str(ok) + " verificari trecute, " + str(rau) + " esuate")
    return 1 if rau else 0


if __name__ == "__main__":
    raise SystemExit(main())
