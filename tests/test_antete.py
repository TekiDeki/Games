#!/usr/bin/env python3
"""Antetele de securitate din _headers, verificate pe bune.

Ce face:
  1. citeste `_headers` si verifica sa fie acolo tot ce trebuie (CSP, HSTS, nosniff, frame, referrer,
     permissions) si ca CSP-ul chiar interzice iesirea in retea (`connect-src 'none'`);
  2. serveste paginile local si **aplica antetele din `_headers`** (ca Cloudflare), apoi verifica:
       - zero violari de CSP in consola,
       - zero cereri catre alt domeniu,
       - fiecare pagina inca functioneaza (hub-ul are 6 carduri, jocurile se incarca, iar la
         word-search se joaca un cuvant intreg de la tastatura),
       - fiecare pagina incarca favicon-ul `data:` (altfel CSP-ul l-ar fi taiat);
  3. daca are retea, verifica si antetele de pe site-ul live.

Antetele se aplica prin rutare Playwright, nu prin fisier: asa testul nu depinde de Cloudflare.
"""
import http.server
import pathlib
import re
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEADERS_FILE = ROOT / "_headers"

def descopera_pagini():
    """Toate paginile din repo, gasite singure: orice index.html, oriunde ar fi.

    Nu e o lista scrisa de mina: un joc nou intra automat sub testul asta in ziua in care e adaugat,
    fara sa-si aminteasca nimeni sa actualizeze ceva. `tests/` e sarit (are pagini de test proprii).
    """
    pagini = set()
    for fisier in ROOT.rglob("index.html"):
        parti = fisier.relative_to(ROOT).parts
        if "tests" in parti or not parti[-1] == "index.html":
            continue
        folder = "/".join(parti[:-1])
        pagini.add("/" if not folder else f"/{folder}/")
    return sorted(pagini)


PAGINI = descopera_pagini()

OBLIGATORII = [
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
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
        print("  RAU  " + mesaj)


def citeste_headers():
    """Intoarce dict-ul de antete din blocul `/*` din _headers."""
    text = HEADERS_FILE.read_text(encoding="utf-8")
    blocuri, curent = {}, None
    for linie in text.splitlines():
        if not linie.strip() or linie.lstrip().startswith("#"):
            continue
        if not linie.startswith((" ", "\t")):
            curent = linie.strip()
            blocuri[curent] = {}
            continue
        if curent and ":" in linie:
            nume, valoare = linie.split(":", 1)
            blocuri[curent][nume.strip()] = valoare.strip()
    return blocuri


def serveste_local():
    """Un server simplu pe un port liber, care serveste radacina repo-ului."""
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(
        *a, directory=str(ROOT), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def verifica_fisier():
    print("\n== fisierul _headers")
    check(HEADERS_FILE.exists(), "_headers exista in radacina repo-ului")
    blocuri = citeste_headers()
    check("/*" in blocuri, "are blocul /* (se aplica tuturor fisierelor)")
    h = blocuri.get("/*", {})
    for nume in OBLIGATORII:
        check(nume in h, f"antetul {nume} e definit")
    csp = h.get("Content-Security-Policy", "")
    check("default-src 'self'" in csp, "CSP porneste de la default-src 'self'")
    check("connect-src 'none'" in csp,
          "CSP are connect-src 'none' - nicio cerere de retea nu poate iesi din pagina")
    check("frame-ancestors 'none'" in csp, "CSP refuza sa fie pus in frame (clickjacking)")
    check("object-src 'none'" in csp, "CSP refuza plugin-uri (object/embed)")
    check("form-action 'none'" in csp, "CSP refuza trimiterea de formulare")
    check("'unsafe-eval'" not in csp, "CSP nu permite eval")
    check(h.get("X-Frame-Options", "").upper() == "DENY", "X-Frame-Options e DENY")
    check(h.get("X-Content-Type-Options", "").lower() == "nosniff", "X-Content-Type-Options e nosniff")
    hsts = h.get("Strict-Transport-Security", "")
    check("max-age=" in hsts and int(re.search(r"max-age=(\d+)", hsts).group(1)) >= 15552000,
          f"HSTS are max-age de minim 180 de zile ({hsts})")
    return h


def main():
    headers = verifica_fisier()
    httpd, port = serveste_local()
    baza = f"http://127.0.0.1:{port}"

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        print("\n== pagini servite cu antetele din _headers")
        for cale in PAGINI:
            ctx = browser.new_context(viewport={"width": 1024, "height": 900}, locale="en-US")
            pg = ctx.new_page()
            violari, erori, externe = [], [], []

            def adauga_antete(route):
                resp = route.fetch()
                route.fulfill(response=resp, headers={**resp.headers, **headers})

            pg.route("**/*", adauga_antete)
            pg.on("console", lambda m: violari.append(m.text)
                  if "Content Security Policy" in m.text or "Refused to" in m.text else None)
            pg.on("pageerror", lambda e: erori.append(str(e)))
            pg.on("request", lambda r: externe.append(r.url)
                  if not r.url.startswith(baza) and not r.url.startswith("data:") else None)

            resp = pg.goto(baza + cale, wait_until="load")
            pg.wait_for_timeout(400)

            check(resp.status == 200, f"{cale}: raspunde 200")
            check(not violari, f"{cale}: zero violari de CSP {violari[:2]}")
            check(not erori, f"{cale}: zero erori de pagina {erori[:2]}")
            check(not externe, f"{cale}: zero cereri catre alt domeniu {externe[:2]}")
            are_favicon = pg.evaluate(
                "() => !!document.querySelector(\"link[rel='icon'][href^='data:']\")")
            check(are_favicon, f"{cale}: favicon-ul data: e in pagina (CSP il permite)")

            if cale == "/":
                carduri = pg.eval_on_selector_all("a.card, .card a, article", "els => els.length")
                check(carduri >= 6, f"{cale}: hub-ul arata cele 6 jocuri ({carduri})")
            if cale == "/word-search/":
                pagina = pg.evaluate("""() => {
                  const c = [...document.querySelectorAll('.cell')];
                  const N = Math.round(Math.sqrt(c.length));
                  const g = Array.from({length: N}, () => Array(N).fill(''));
                  c.forEach(x => { g[+x.dataset.y][+x.dataset.x] = x.textContent; });
                  const w = [...document.querySelectorAll('.word')].map(x => x.textContent);
                  const dirs = [[1,0],[0,1],[1,1],[-1,1],[1,-1],[-1,-1],[0,-1],[-1,0]];
                  for (const cuv of w) for (let y=0;y<N;y++) for (let x=0;x<N;x++) for (const [dx,dy] of dirs) {
                    let bun = true; const drum=[];
                    for (let i=0;i<cuv.length;i++) { const nx=x+dx*i, ny=y+dy*i;
                      if (nx<0||ny<0||nx>=N||ny>=N||g[ny][nx]!==cuv[i]) { bun=false; break; }
                      drum.push([nx,ny]); }
                    if (bun) return {cuv, s:[x,y], e:drum[drum.length-1]};
                  }
                  return null; }""")
                check(pagina is not None, "word-search: grila s-a desenat")
                if pagina:
                    sx, sy = pagina["s"]; ex, ey = pagina["e"]
                    pg.eval_on_selector(f'.cell[data-x="{sx}"][data-y="{sy}"]', "el => el.focus()")
                    pg.keyboard.press("Enter")
                    for _ in range(abs(ex - sx)):
                        pg.keyboard.press("ArrowRight" if ex > sx else "ArrowLeft")
                    for _ in range(abs(ey - sy)):
                        pg.keyboard.press("ArrowDown" if ey > sy else "ArrowUp")
                    pg.keyboard.press("Enter")
                    pg.wait_for_timeout(200)
                    gasite = pg.eval_on_selector_all(".word.done", "ws => ws.length")
                    check(gasite == 1,
                          f"word-search: jocul merge sub CSP, cuvant gasit din tastatura ({pagina['cuv']})")
            ctx.close()

        print("\n== site-ul live")
        ctx = browser.new_context()
        pg = ctx.new_page()
        try:
            r = pg.goto("https://games.freehtml.dev/", wait_until="load", timeout=20000)
            h_live = {k.lower(): v for k, v in r.headers.items()}
            check(r.status == 200, "live: raspunde 200")
            check("content-security-policy" in h_live,
                  "live: CSP e servit de Cloudflare (nu doar in fisier)")
            if "content-security-policy" in h_live:
                check("connect-src 'none'" in h_live["content-security-policy"],
                      "live: CSP-ul servit are connect-src 'none'")
            check("x-frame-options" in h_live, "live: X-Frame-Options e servit")
            check("strict-transport-security" in h_live, "live: HSTS e servit")
        except Exception as e:
            print(f"  (sar peste verificarea live: {type(e).__name__})")
        ctx.close()
        browser.close()

    httpd.shutdown()
    print(f"\n{ok} verificari trecute, {rau} esuate")
    return 0 if rau == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
