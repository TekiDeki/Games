#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Translation Pairs: joc real, nu doar verificari de markup.

Se ruleaza din radacina repo-ului cu Playwright si Chromium. Serverul local este
pornit aici pentru proba de service worker/offline; nu sunt necesare servicii externe.
"""
import http.server
import json
import os
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE_FILE = ROOT / "translation-pairs" / "index.html"
DATA_FILE = ROOT / "tests" / "translations.json"
PATH = "/translation-pairs/"
ok = 0
rau = 0


def check(cond, msg):
    global ok, rau
    if cond:
        ok += 1
        print("  ok   " + msg)
    else:
        rau += 1
        print("  FAIL " + msg)


def cards(pg, side=None):
    selector = ".pair-card" + (f'[data-side="{side}"]' if side else "")
    return pg.locator(selector)


def card_map(pg, side):
    return pg.eval_on_selector_all(
        f'.pair-card[data-side="{side}"]',
        "els => els.map(e => ({id:e.dataset.id, text:e.textContent.trim()}))",
    )


def click_pair(pg, left_id, right_id=None):
    right_id = right_id or left_id
    pg.locator(f'.pair-card[data-side="left"][data-id="{left_id}"]').click()
    pg.locator(f'.pair-card[data-side="right"][data-id="{right_id}"]').click()


def main():
    check(PAGE_FILE.is_file(), "pagina exista inainte de proba de browser")
    check(DATA_FILE.is_file(), "harta de traduceri exista")
    if not PAGE_FILE.is_file() or not DATA_FILE.is_file():
        print(f"\n{ok} verificari trecute, {rau} esuate")
        return 1
    entries = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in entries}

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, *args):
            pass

    server = socketserver.TCPServer(("127.0.0.1", 0), Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": 1100, "height": 900}, locale="ro-RO")
        pg = ctx.new_page()
        errors = []
        external = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("request", lambda r: external.append(r.url)
              if not r.url.startswith(base) and not r.url.startswith("data:") else None)
        response = pg.goto(base + PATH, wait_until="load")
        pg.wait_for_timeout(250)
        check(response and response.status == 200, "pagina raspunde 200")
        check(pg.evaluate("document.documentElement.lang") == "en",
              "prima vizita este in engleza chiar cu browser ro-RO")
        check(cards(pg, "left").count() == 6 and cards(pg, "right").count() == 6,
              "runda initiala are 6 perechi, 12 carti")
        left = card_map(pg, "left")
        right = card_map(pg, "right")
        check(all(x["text"] == by_id[x["id"]]["ro"] for x in left),
              "colоana stanga contine cuvintele romanesti ale conceptelor")
        check(all(x["text"] == by_id[x["id"]]["en"] for x in right),
              "coloana dreapta contine traducerile engleze corecte")
        check(pg.locator(".pair-card.matched").count() == 0, "niciun cuplu nu porneste rezolvat")
        check(pg.locator("#supportLinkText").inner_text() == "Support the work" and
              "❤️" in pg.locator("#supportLink").inner_text(),
              "subsolul are buton de sprijin cu inima")
        check(pg.locator("#supportLink").get_attribute("href") == "https://paypal.me/TekiDeki",
              "href-ul de sprijin este exact")

        # O pereche gresita: exact o incercare, feedback rosu, apoi selectia se elibereaza.
        wrong = next(x["id"] for x in right if x["id"] != left[0]["id"])
        click_pair(pg, left[0]["id"], wrong)
        check(pg.locator(".pair-card.bad").count() == 2, "perechea gresita are feedback rosu")
        check(pg.locator("#moves").inner_text() == "1", "perechea gresita numara o incercare")
        pg.wait_for_timeout(600)
        check(pg.locator(".pair-card.bad").count() == 0, "rosul dispare dupa feedback")
        check(pg.locator(".pair-card.selected").count() == 0, "selectia gresita se elibereaza")
        check(pg.locator(".pair-card.matched").count() == 0, "perechea gresita nu este marcată verde")

        # Selectarea repetata pe aceeasi coloana nu este o incercare.
        pg.locator(f'.pair-card[data-side="left"][data-id="{left[1]["id"]}"]').click()
        pg.locator(f'.pair-card[data-side="left"][data-id="{left[2]["id"]}"]').click()
        check(pg.locator("#moves").inner_text() == "1", "reselectarea pe aceeasi coloana nu creste mutarile")
        check(pg.locator(".pair-card.selected").count() == 1, "exista o singura carte selectata")

        # New game in timpul feedback-ului nu lasa un timer vechi sa modifice runda noua.
        pg.click("#againBtn")
        left = card_map(pg, "left")
        wrong = next(x["id"] for x in card_map(pg, "right") if x["id"] != left[0]["id"])
        click_pair(pg, left[0]["id"], wrong)
        pg.click("#againBtn")
        left = card_map(pg, "left")
        pg.locator(f'.pair-card[data-side="left"][data-id="{left[0]["id"]}"]').click()
        pg.wait_for_timeout(600)
        check(pg.locator(".pair-card.selected").count() == 1,
              "timerul vechi nu sterge selectia din runda noua")

        # O pereche buna ramane verde si nu mai poate fi apasata.
        pg.click("#againBtn")
        left = card_map(pg, "left")
        click_pair(pg, left[0]["id"])
        check(pg.locator(".pair-card.matched").count() == 2, "perechea buna ramane verde")
        check(pg.locator(".pair-card.matched:disabled").count() == 2, "perechea rezolvata se dezactiveaza")
        check(pg.locator("#matches").inner_text() == "1", "contorul de perechi creste")
        check(pg.locator("#moves").inner_text() == "1", "perechea buna numara o incercare")

        # Castig real, prin toate cele sase potriviri.
        pg.click("#againBtn")
        for item in card_map(pg, "left"):
            click_pair(pg, item["id"])
        check(pg.locator(".pair-card.matched").count() == 12, "toate perechile pot fi rezolvate")
        check(pg.locator("#matches").inner_text() == "6", "contorul final este 6/6")
        check(pg.locator("#moves").inner_text() == "6", "o runda perfecta are 6 incercari")
        check("6" in pg.locator("#msg").inner_text(), "mesajul de castig contine numarul de incercari")
        check(pg.locator("#rounds").inner_text() == "1", "runda completa este contorizata")
        check(pg.locator("#best").inner_text() == "6", "best salveaza minimul de incercari")
        pg.reload(wait_until="load")
        pg.wait_for_timeout(150)
        check(pg.locator("#rounds").inner_text() == "1" and pg.locator("#best").inner_text() == "6",
              "runda si best raman dupa reload")

        # Cele trei tinte si cele trei dimensiuni.
        pg.click("#targetChip")
        check(all(x["text"] == by_id[x["id"]]["sr"] for x in card_map(pg, "right")),
              "tinta sr-Latn schimba efectiv cuvintele")
        pg.click("#targetChip")
        check(all(x["text"] == by_id[x["id"]]["src"] for x in card_map(pg, "right")),
              "tinta sr-Cyrl schimba efectiv cuvintele")
        pg.click("#targetChip")
        check(all(x["text"] == by_id[x["id"]]["en"] for x in card_map(pg, "right")),
              "tinta revine la engleza")
        pg.click("#sizeChip")
        check(cards(pg, "left").count() == 8, "dimensiunea urmatoare are 8 perechi")
        pg.click("#sizeChip")
        check(cards(pg, "left").count() == 4, "dimensiunea urmatoare are 4 perechi")
        pg.click("#themeChip")
        check(all(by_id[x["id"]]["tema"] == "mancare" for x in card_map(pg, "left")),
              "tema mancare schimba conceptual runda")

        # Limba interfetei, metadatele si persistenta alegerii.
        descriptions = set()
        expected_langs = {"en": "en", "ro": "ro", "sr": "sr-Latn", "src": "sr-Cyrl"}
        for lang, html_lang in expected_langs.items():
            pg.click(f'.langs button[data-lang="{lang}"]')
            pg.wait_for_timeout(80)
            check(pg.evaluate("document.documentElement.lang") == html_lang,
                  f"{lang}: html lang este {html_lang}")
            check(pg.locator("h1").inner_text().strip() != "", f"{lang}: titlul jocului este tradus")
            desc = pg.locator('meta[name="description"]').get_attribute("content")
            descriptions.add(desc)
            check(bool(desc), f"{lang}: meta description exista")
            ld = json.loads(pg.locator('script[type="application/ld+json"]').inner_text())
            check(ld.get("inLanguage") == html_lang and ld.get("description") == desc,
                  f"{lang}: JSON-LD urmareste limba si descrierea")
        check(len(descriptions) == 4, "cele patru limbi au descrieri distincte")
        pg.click('.langs button[data-lang="ro"]')
        pg.reload(wait_until="load")
        check(pg.evaluate("document.documentElement.lang") == "ro", "limba vizitatorului persista")

        # Tema vizuala si joc din tastatura.
        old_theme = pg.evaluate("document.documentElement.dataset.theme")
        pg.click("#themeBtn")
        new_theme = pg.evaluate("document.documentElement.dataset.theme")
        check(old_theme != new_theme, "butonul light/dark schimba tema")
        pg.reload(wait_until="load")
        check(pg.evaluate("document.documentElement.dataset.theme") == new_theme, "tema vizuala persista")
        pg.click("#againBtn")
        item = card_map(pg, "left")[0]
        pg.locator(f'.pair-card[data-side="left"][data-id="{item["id"]}"]').focus()
        pg.keyboard.press("Enter")
        pg.locator(f'.pair-card[data-side="right"][data-id="{item["id"]}"]').focus()
        pg.keyboard.press("Enter")
        check(pg.locator(".pair-card.matched").count() == 2, "o pereche poate fi jucata din tastatura")
        check(not errors, "zero erori JavaScript in parcursul desktop: " + str(errors[:2]))
        check(not external, "zero cereri catre alte origini: " + str(external[:2]))
        ctx.close()

        # Mobil: 320 px, tinte mari si touch real pe o pereche.
        mobile = browser.new_context(viewport={"width": 320, "height": 760}, has_touch=True,
                                     is_mobile=True, locale="en-US")
        mp = mobile.new_page()
        mp.goto(base + PATH, wait_until="load")
        mp.wait_for_timeout(150)
        check(mp.evaluate("document.documentElement.scrollWidth") <= 320, "320 px: fara overflow orizontal")
        sizes = mp.eval_on_selector_all(
            "button, footer a",
            "els => els.filter(e => e.offsetParent !== null).map(e => {const r=e.getBoundingClientRect(); return [r.width,r.height];})",
        )
        check(all(w >= 44 and h >= 44 for w, h in sizes), "320 px: controalele au tinte de minim 44 px")
        item = card_map(mp, "left")[0]
        mp.locator(f'.pair-card[data-side="left"][data-id="{item["id"]}"]').tap()
        mp.locator(f'.pair-card[data-side="right"][data-id="{item["id"]}"]').tap()
        check(mp.locator(".pair-card.matched").count() == 2, "touch-ul rezolva o pereche")
        mobile.close()

        # Offline dupa ce shell-ul a fost instalat, cu controller activ.
        offline = browser.new_context(viewport={"width": 800, "height": 700})
        op = offline.new_page()
        op.goto(base + PATH, wait_until="load")
        op.wait_for_timeout(400)
        op.reload(wait_until="load")
        op.wait_for_timeout(200)
        controlled = op.evaluate("navigator.serviceWorker && !!navigator.serviceWorker.controller")
        check(controlled, "service worker-ul controleaza pagina dupa instalare")
        offline_responses = []
        op.on("response", lambda r: offline_responses.append(r))
        offline.set_offline(True)
        try:
            off_response = op.reload(wait_until="load")
            op.wait_for_timeout(150)
            check(off_response and off_response.status == 200, "pagina se redeschide offline din shell")
            check(op.locator(".pair-card").count() == 12, "jocul este utilizabil offline")
            normal = [r.url for r in offline_responses if not r.from_service_worker]
            check(not normal, "zero raspunsuri normale de retea in offline: " + str(normal[:2]))
            item = card_map(op, "left")[0]
            click_pair(op, item["id"])
            check(op.locator(".pair-card.matched").count() == 2, "o pereche se rezolva si offline")
        except Exception as exc:
            check(False, "reload offline: " + str(exc))
        offline.close()
        browser.close()

    server.shutdown()
    print(f"\n{ok} verificari trecute, {rau} esuate")
    return 1 if rau else 0


if __name__ == "__main__":
    sys.exit(main())
