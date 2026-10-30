#!/usr/bin/env python3
"""Scrie repede (typing-test): test de browser pentru jocul nou.

Se joaca pe bune: se tasteaza litere cu Playwright, se verifica matematica scorului, oprirea din
timp, schimbarea limbii, diacriticele si ca nu pleaca nicio cerere in afara paginii.

Determinist prin URL: `?seed=1&s=300&n=8` fixeaza ordinea cuvintelor, durata si cate cuvinte intra.
"""
import http.server
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
BAZA_URL = "/typing-test/"

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


def serveste():
    class Tacut(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(ROOT), **kw)

        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Tacut)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def main():
    httpd, port = serveste()
    baza = f"http://127.0.0.1:{port}"

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])

        def nou(query="seed=1&s=300&n=8", viewport=(1100, 900), redus=False):
            ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
            if redus:
                ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]},
                                          reduced_motion="reduce")
            pg = ctx.new_page()
            jurnal = {"viol": [], "err": [], "ext": []}
            pg.on("console", lambda m: jurnal["viol"].append(m.text)
                  if ("Content Security Policy" in m.text or "Refused to" in m.text) else None)
            pg.on("pageerror", lambda e: jurnal["err"].append(str(e)))
            pg.on("request", lambda r: jurnal["ext"].append(r.url)
                  if not r.url.startswith(baza) and not r.url.startswith("data:") else None)
            raspuns = pg.goto(f"{baza}{BAZA_URL}?{query}", wait_until="load")
            return ctx, pg, jurnal, raspuns

        def cuvant_curent(pg):
            return pg.evaluate("() => state.lista[state.idx]")

        # ---------- 1. pagina si datele ----------
        print("\n== pagina si datele")
        ctx, pg, jurnal, resp = nou()
        check(resp.status == 200, "pagina raspunde 200")
        check("Scrie repede" in pg.title(), f"titlul e al jocului ({pg.title()[:40]})")
        check(pg.get_attribute("html", "lang") == "ro", "html lang=ro la pornire")

        nr = pg.evaluate("""() => {
            const out = {};
            for (const lim in W) out[lim] = Object.values(W[lim]).flat().length;
            return out; }""")
        check(set(nr) == {"ro", "en", "sr", "src"}, f"are cele patru limbi: {sorted(nr)}")
        check(all(v == 48 for v in nr.values()), f"48 de cuvinte pe limba: {nr}")

        unice = pg.evaluate("""() => {
            const out = {};
            for (const lim in W) {
              const toate = Object.values(W[lim]).flat();
              out[lim] = new Set(toate).size === toate.length;
            }
            return out; }""")
        check(all(unice.values()), "niciun cuvant repetat in vreo limba")

        lungime = pg.evaluate("() => state.lista.length")
        check(lungime == 8, f"?n=8 da 8 cuvinte in runda (are {lungime})")
        check(pg.evaluate("() => document.querySelectorAll('.words .w').length") > 0,
              "cuvintele se vad in pagina")
        check(not jurnal["ext"], f"nicio cerere in afara paginii {jurnal['ext'][:2]}")
        check(not jurnal["viol"], f"nicio violare de CSP {jurnal['viol'][:1]}")
        check(not jurnal["err"], f"nicio eroare de pagina {jurnal['err'][:1]}")

        # ---------- 2. determinismul ----------
        print("\n== determinism")
        primul = cuvant_curent(pg)
        ctx2, pg2, _, _ = nou("seed=1&s=300&n=8")
        check(cuvant_curent(pg2) == primul, f"acelasi seed da acelasi prim cuvant ({primul})")
        ctx3, pg3, _, _ = nou("seed=99&s=300&n=8")
        diferit = pg3.evaluate("() => state.lista.join(' ')") != pg.evaluate("() => state.lista.join(' ')")
        check(diferit, "alt seed da alta ordine")
        ctx2.close(); ctx3.close()

        # ---------- 3. jocul: litere corecte ----------
        print("\n== jocul")
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(150)
        check(pg.evaluate("() => state.rulare"), "Enter porneste runda")
        cuv = cuvant_curent(pg)
        pg.keyboard.type(cuv.lower())
        pg.wait_for_timeout(120)
        check(pg.evaluate("() => state.cuvinteGata") == 1, f"cuvantul '{cuv}' s-a terminat si a trecut mai departe")
        check(pg.text_content("#cuvChip") == "1", "contorul de cuvinte arata 1")

        # ---------- 4. litera gresita nu trece ----------
        print("\n== litera gresita")
        inainte_poz = pg.evaluate("() => state.poz")
        inainte_bune = pg.evaluate("() => state.bune")
        inainte_total = pg.evaluate("() => state.total")
        urmator = cuvant_curent(pg)
        gresita = "Q" if urmator.upper()[0] != "Q" else "Z"
        pg.keyboard.type(gresita.lower())
        pg.wait_for_timeout(120)
        check(pg.evaluate("() => state.poz") == inainte_poz,
              "pozitia in cuvant nu s-a schimbat dupa o litera gresita")
        check(pg.evaluate("() => state.bune") == inainte_bune, "literele corecte au ramas aceleasi")
        check(pg.evaluate("() => state.total") == inainte_total + 1, "tastarea gresita a fost numarata")
        asteptat = round(100 * inainte_bune / (inainte_total + 1))
        check(int(pg.text_content("#precChip")) == asteptat,
              f"precizia e calculata corect ({pg.text_content('#precChip')}% = {asteptat}%)")
        check("nu e corectă" in pg.text_content("#msg") or "not right" in pg.text_content("#msg"),
              "mesajul spune ca litera nu e corecta")

        # ---------- 5. matematica WPM ----------
        print("\n== cuvinte pe minut")
        afisat, estimat = pg.evaluate(
            "() => { const w = wpm(); const m = (Date.now() - state.start) / 60000; "
            "return [w, m > 0 ? Math.round((state.bune / 5) / m) : 0]; }")
        check(abs(afisat - estimat) <= 1,
              f"WPM ({afisat}) = litere corecte / 5 / minute ({estimat})")
        check(afisat > 0, "WPM creste dupa ce ai scris")

        # ---------- 6. diacritice ----------
        print("\n== diacritice")
        ctx4, pg4, j4, _ = nou("seed=3&s=300&n=40&limba=ro")
        pg4.keyboard.press("Enter")
        pg4.wait_for_timeout(100)
        toate_diacritice = pg4.evaluate(
            "() => state.lista.filter(w => /[ĂÂÎȘȚ]/.test(w)).length")
        check(toate_diacritice >= 3,
              f"runda are cuvinte cu diacritice ({toate_diacritice} din 40)")

        def scrie_cu_evenimente(w):
            pg4.evaluate("""(w) => {
                for (const ch of w) {
                  document.dispatchEvent(new KeyboardEvent('keydown', {key: ch.toLowerCase(), bubbles: true}));
                }
              }""", w)

        gasit = None
        for _ in range(20):
            w = cuvant_curent(pg4)
            inainte_gata = pg4.evaluate("() => state.cuvinteGata")
            scrie_cu_evenimente(w)
            pg4.wait_for_timeout(60)
            trecut = pg4.evaluate("() => state.cuvinteGata") > inainte_gata
            if any(c in "ĂÂÎȘȚ" for c in w):
                gasit = w
                check(trecut, f"cuvantul cu diacritice '{w}' se scrie pana la capat")
                check(pg4.evaluate("() => state.gresite") == 0,
                      "diacriticele nu au fost numarate ca greseli")
                break
        check(gasit is not None, "am ajuns la un cuvant cu diacritice si l-am scris")
        ctx4.close()

        # ---------- 7. oprirea ----------
        print("\n== oprire")
        check(pg.evaluate("() => state.rulare"), "runda inca ruleaza")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(150)
        check(not pg.evaluate("() => state.rulare"), "Esc opreste runda")
        check(pg.evaluate("() => document.getElementById('rezultat').classList.contains('aratat')"),
              "rezultatul apare dupa oprire")
        check(pg.text_content("#rezWpm").isdigit(), "rezultatul arata un numar de cuvinte pe minut")
        ctx.close()

        # ---------- 8. timpul expira singur ----------
        print("\n== cronometru")
        ctx5, pg5, j5, _ = nou("seed=2&s=5&n=40")
        pg5.keyboard.press("Enter")
        pg5.wait_for_timeout(5600)
        check(not pg5.evaluate("() => state.rulare"), "runda s-a oprit singura dupa 5 secunde")
        check("expirat" in pg5.text_content("#msg") or "up" in pg5.text_content("#msg"),
              f"mesajul spune ca timpul a expirat ({pg5.text_content('#msg')[:40]})")
        check(pg5.evaluate("() => document.getElementById('rezultat').classList.contains('aratat')"),
              "rezultatul e afisat")
        check(not j5["viol"], "nicio violare de CSP nici la final")
        ctx5.close()

        # ---------- 9. limbi ----------
        print("\n== limbi")
        ctx6, pg6, _, _ = nou()
        pg6.click("#limbaBtn")
        pg6.wait_for_timeout(120)
        check(pg6.get_attribute("html", "lang") == "en", "a doua limba e engleza (html lang=en)")
        check("Type Fast" in pg6.title(), f"titlul se schimba ({pg6.title()[:30]})")
        check(pg6.text_content("#startBtn") in ("Start", "Again"), "butonul isi schimba textul")
        pg6.click("#limbaBtn")
        pg6.wait_for_timeout(120)
        check(pg6.get_attribute("html", "lang") == "sr", "a treia limba e sarba")
        pg6.click("#limbaBtn")
        pg6.wait_for_timeout(120)
        check("Куцај" in pg6.text_content("#titlu"), "a patra limba e sarba chirilica")
        pg6.click("#limbaBtn")
        pg6.wait_for_timeout(120)
        check(pg6.get_attribute("html", "lang") == "ro", "a cincea apasare revine la romana")

        # ---------- 10. tema ----------
        print("\n== tema si animatii")
        inainte = pg6.get_attribute("html", "data-theme")
        pg6.click("#temăBtn")
        pg6.wait_for_timeout(100)
        check(pg6.get_attribute("html", "data-theme") != inainte, "butonul de tema schimba tema")
        ctx6.close()

        ctx7 = browser.new_context(viewport={"width": 900, "height": 800}, reduced_motion="reduce")
        pg7 = ctx7.new_page()
        pg7.goto(f"{baza}{BAZA_URL}?seed=1&s=300&n=8", wait_until="load")
        anim = pg7.evaluate("() => { const c = document.querySelector('.caret'); "
                            "return c ? getComputedStyle(c).animationName : 'lipsa'; }")
        check(anim in ("none", "lipsa"), f"la prefers-reduced-motion cursorul nu mai clipeste ({anim})")
        ctx7.close()

        # ---------- 11. mobil ----------
        print("\n== mobil")
        ctx8, pg8, j8, _ = nou("seed=1&s=300&n=8", viewport=(390, 780))
        latime = pg8.evaluate("() => document.documentElement.scrollWidth")
        check(latime <= 392, f"fara scroll orizontal la 390px ({latime}px)")
        tinte = pg8.eval_on_selector_all("#startBtn, #dinouBtn, #limbaBtn, [data-durata]",
                                         "els => els.map(e => { const r = e.getBoundingClientRect(); "
                                         "return Math.min(r.width, r.height); })")
        check(min(tinte) >= 40, f"tinte de atingere de minim 40px ({min(tinte):.0f})")
        ctx8.close()

        # ---------- 12. joaca doar de la tastatura ----------
        print("\n== doar de la tastatura")
        ctx9, pg9, j9, _ = nou("seed=5&s=300&n=8")
        pg9.keyboard.press("Tab")
        pg9.keyboard.press("Enter")
        pg9.wait_for_timeout(200)
        pornit = pg9.evaluate("() => state.rulare")
        if not pornit:
            pg9.keyboard.press("Enter")
            pg9.wait_for_timeout(200)
        check(pg9.evaluate("() => state.rulare"), "runda porneste fara mouse")
        for _ in range(3):
            cuv9 = cuvant_curent(pg9)
            pg9.keyboard.type(cuv9.lower())
            pg9.wait_for_timeout(80)
        check(pg9.evaluate("() => state.cuvinteGata") >= 2, "s-au scris cuvinte doar cu tastatura")
        check(not j9["err"], f"nicio eroare in timpul jocului {j9['err'][:1]}")
        ctx9.close()

        # ---------- 13. copiere ----------
        print("\n== copiere rezultat")
        ctx10, pg10, j10, _ = nou("seed=1&s=300&n=2")
        pg10.keyboard.press("Enter")
        pg10.wait_for_timeout(100)
        for _ in range(2):
            c = cuvant_curent(pg10)
            pg10.keyboard.type(c.lower())
            pg10.wait_for_timeout(80)
        pg10.wait_for_timeout(150)
        check(pg10.evaluate("() => state.gata"), "runda de 2 cuvinte se termina singura")
        pg10.click("#copiazaBtn")
        pg10.wait_for_timeout(150)
        check(not j10["err"], f"butonul de copiere nu arunca erori {j10['err'][:1]}")
        ctx10.close()

        browser.close()

    httpd.shutdown()
    print(f"\n{ok} verificari trecute, {rau} esuate")
    return 0 if rau == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
