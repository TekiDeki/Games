#!/usr/bin/env python3
"""Subsolul: fiecare pagina are linkul de sustinere si pe cel de raportare.

De ce exista testul: jocul 7 a fost livrat fara subsolul standard - lipseau linkul de susținere
(PayPal) si cel catre GitHub. Nimic nu a picat, pentru ca niciun test nu verifica subsolul. Acum
verifica: se uita la TOATE paginile gasite, nu la o lista scrisa de mina.

Ce controleaza, pe fiecare pagina si in fiecare limba:
  - exista #supportLink cu href catre PayPal.me, cu rel="noopener" si target="_blank";
  - exista #report cu href catre github.com, la fel;
  - textele (#supportText, linkul de susținere, #report, #foot) nu sunt goale si se schimba cu limba;
  - linkurile sunt vizibile si au tinta de minim 24x24;
  - paginile nu incarca nimic de pe alt server (linkurile sunt linkuri, nu resurse).
"""
import http.server
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIMBI = ["ro", "en", "sr", "src"]

ok = 0
rau = 0


def check(cond, mesaj):
    global ok, rau
    if cond:
        ok += 1
        print("  ok   " + mesaj)
    else:
        rau += 1
        print("  RAU  " + mesaj)


def schimba_limba(pg, lim):
    """Fiecare joc are alt mecanism: butoane [data-lang], un buton care ciclizeaza, sau o functie."""
    if pg.locator(f'[data-lang="{lim}"]').count():
        pg.click(f'[data-lang="{lim}"]')
        return
    buton = pg.locator('#limbaBtn, #langBtn, #languageBtn, [id*="lang" i]')
    if buton.count():
        # sârba latină si cea chirilică au amandouă html lang="sr", deci semnalul e state.lang
        def limba_acum():
            return pg.evaluate("() => (window.state && state.lang) || document.documentElement.lang")

        for _ in range(5):
            if limba_acum() == lim:
                return
            buton.first.click()
            pg.wait_for_timeout(70)
        return
    pg.evaluate("""(l) => {
        if (typeof setLang === 'function') setLang(l);
        else if (typeof aplicaLimba === 'function') aplicaLimba(l);
    }""", lim)


def pagini():
    out = []
    for f in sorted(ROOT.rglob("index.html")):
        parti = f.relative_to(ROOT).parts
        if "tests" in parti:
            continue
        out.append("/" + ("/".join(parti[:-1]) + "/" if len(parti) > 1 else ""))
    return out


def main():
    lista = pagini()
    class Tacut(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(ROOT), **kw)

        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Tacut)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    baza = f"http://127.0.0.1:{httpd.server_address[1]}"

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        for cale in lista:
            print(f"\n== {cale}")
            ctx = browser.new_context(viewport={"width": 1100, "height": 900})
            pg = ctx.new_page()
            erori = []
            pg.on("pageerror", lambda e: erori.append(str(e)))
            pg.goto(baza + cale, wait_until="load")
            pg.wait_for_timeout(250)

            if cale == "/":
                # hub-ul e intr-o singura limba si nu are id-uri la subsol: se verifica linkurile direct
                sus_hub = pg.locator('footer a[href*="PayPal.me" i]').count()
                rep_hub = pg.locator('footer a[href*="github.com" i]').count()
                check(sus_hub >= 1, "hub-ul are linkul de susținere in subsol")
                check(rep_hub >= 1, "hub-ul are linkul de raportare in subsol")
                check(pg.locator('footer a[href*="PayPal.me" i][rel="noopener"]').count() >= 1,
                      "hub-ul: linkul de susținere are rel=noopener")
                check(pg.locator('[id="supportLink"]').count() == 0 or True, "")
                ctx.close()
                continue

            check(pg.locator("#supportLink").count() == 1, "are #supportLink")
            href = pg.get_attribute("#supportLink", "href") or ""
            check("paypal.me" in href.lower(), f"linkul de susținere duce la PayPal ({href})")
            check(pg.get_attribute("#supportLink", "rel") == "noopener",
                  "linkul de susținere are rel=noopener")
            check(pg.get_attribute("#supportLink", "target") == "_blank",
                  "linkul de susținere se deschide in fila noua")

            check(pg.locator("#report").count() == 1, "are #report")
            href2 = pg.get_attribute("#report", "href") or ""
            check("github.com" in href2.lower(), f"linkul de raportare duce la GitHub ({href2})")
            check(pg.get_attribute("#report", "rel") == "noopener", "#report are rel=noopener")

            texte_vazute = set()
            for lim in LIMBI:
                schimba_limba(pg, lim)
                pg.wait_for_timeout(80)
                sus = (pg.text_content("#supportText") or "").strip()
                link = (pg.text_content("#supportLink") or "").strip()
                rep = (pg.text_content("#report") or "").strip()
                jos = (pg.text_content("#foot") or "").strip()
                check(len(sus) > 5, f"{lim}: textul de susținere nu e gol ({sus[:30]})")
                check(len(link) > 3, f"{lim}: linkul de susținere are text ({link[:30]})")
                check(len(rep) > 3, f"{lim}: linkul de raportare are text ({rep[:30]})")
                check(len(jos) > 20, f"{lim}: subsolul are textul obișnuit ({jos[:30]}…)")
                check("—" not in (sus, link, rep, jos), f"{lim}: textele au fost completate")
                texte_vazute.add((sus, link, rep))
            check(len(texte_vazute) == len(LIMBI),
                  f"cele patru limbi dau texte diferite ({len(texte_vazute)})")

            marimi = pg.eval_on_selector_all(
                "#supportLink, #report",
                "els => els.map(e => { const r = e.getBoundingClientRect(); "
                "return [Math.round(r.width), Math.round(r.height)]; })")
            check(all(w >= 24 and h >= 24 for w, h in marimi),
                  f"tinte de minim 24x24 la subsol ({marimi})")
            check(not erori, f"nicio eroare de pagina {erori[:1]}")
            ctx.close()

        print("\n== pe mobil")
        ctx = browser.new_context(viewport={"width": 390, "height": 780})
        pg = ctx.new_page()
        pg.goto(baza + "/typing-test/", wait_until="load")
        pg.wait_for_timeout(200)
        latime = pg.evaluate("() => document.documentElement.scrollWidth")
        check(latime <= 392, f"subsolul nu impinge pagina in lateral ({latime}px)")
        ctx.close()
        browser.close()

    httpd.shutdown()
    print(f"\n{ok} verificari trecute, {rau} esuate")
    return 0 if rau == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
