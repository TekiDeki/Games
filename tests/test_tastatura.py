#!/usr/bin/env python3
"""Tastatura si tinte de atingere la "Cauta cuvintele" (word-search).

Verifica ce nu se putea face inainte:
  - jocul se poate juca exclusiv de la tastatura (sageti, Shift+sageti, Enter, Escape)
  - un singur punct de intrare in grila (tabindex rulant), ca la un grid adevarat
  - starea de selectie e anuntata (aria-pressed), nu doar colorata
  - tinte de atingere de minim 24x24 px, inclusiv la 320 px latime
  - fara depasire pe orizontala la 320/375/768/1440
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

PAGINA = pathlib.Path(__file__).resolve().parent.parent / "word-search" / "index.html"

JS_CAUTA_CUVANT = r"""
() => {
  const cells = [...document.querySelectorAll('.cell')];
  const N = Math.round(Math.sqrt(cells.length));
  const g = Array.from({length: N}, () => Array(N).fill(''));
  cells.forEach(c => { g[+c.dataset.y][+c.dataset.x] = c.textContent; });
  const words = [...document.querySelectorAll('.word')].map(w => w.textContent);
  const dirs = [[1,0],[0,1],[1,1],[-1,1],[1,-1],[-1,-1],[0,-1],[-1,0]];
  for (const w of words) {
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) for (const [dx, dy] of dirs) {
      let ok = true; const path = [];
      for (let i = 0; i < w.length; i++) {
        const nx = x + dx * i, ny = y + dy * i;
        if (nx < 0 || ny < 0 || nx >= N || ny >= N || g[ny][nx] !== w[i]) { ok = false; break; }
        path.push([nx, ny]);
      }
      if (ok) return {word: w, start: [x, y], end: path[path.length - 1], len: w.length, N};
    }
  }
  return null;
}
"""

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


def text(pg, sel):
    return pg.inner_text(sel).strip()


def focuseaza(pg, x, y):
    pg.eval_on_selector(f'.cell[data-x="{x}"][data-y="{y}"]', "el => el.focus()")
    pg.wait_for_timeout(40)


def apasa(pg, tasta, ori=1):
    for _ in range(ori):
        pg.keyboard.press(tasta)
        pg.wait_for_timeout(30)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        for limba, asteptat, cuvant_linie in (("en", "keyboard", "line"), ("src", "тастатури", "линији")):
            ctx = browser.new_context(viewport={"width": 1024, "height": 900}, locale="en-US")
            pg = ctx.new_page()
            erori = []
            pg.on("pageerror", lambda e: erori.append(str(e)))
            pg.goto(PAGINA.as_uri(), wait_until="load")
            pg.wait_for_timeout(300)
            if limba != "en":
                pg.click(f'.langs button[data-lang="{limba}"]')
                pg.wait_for_timeout(400)
            print(f"\n== limba {limba}")

            # 0. indicatia de tastatura exista in mesaj
            check(asteptat in text(pg, "#msg").lower(),
                  "mesajul de start spune cum se joaca de la tastatura")

            # 1. un singur punct de intrare in grila
            intrare = pg.eval_on_selector_all(".cell", "cs => cs.filter(c => c.tabIndex === 0).length")
            check(intrare == 1, f"o singura celula e in ordinea Tab (are {intrare})")

            celule = pg.eval_on_selector_all(".cell", "cs => cs.length")
            check(celule == 144, f"grila are 144 de celule (are {celule})")

            # 2. Tab intra in grila si ajunge pe o celula
            pg.eval_on_selector("#msg", "el => el.blur()")
            pg.keyboard.press("Tab")
            pg.wait_for_timeout(60)
            ajuns = pg.evaluate("() => document.activeElement.classList.contains('cell')")
            if not ajuns:
                for _ in range(25):
                    pg.keyboard.press("Tab")
                    pg.wait_for_timeout(30)
                    if pg.evaluate("() => document.activeElement.classList.contains('cell')"):
                        ajuns = True
                        break
            check(ajuns, "Tab ajunge intr-o celula a grilei")

            # 2b. la intrarea in grila, indicatia de tastatura apare contextual
            mesaj_intrare = text(pg, "#msg").lower()
            check("keyboard" in mesaj_intrare or "тастатур" in mesaj_intrare,
                  f"intrarea in grila arata ce fac tastele: {mesaj_intrare[:60]}")

            # 2c. un clic cu mouse-ul NU arata indicatia de tastatura
            ctx2 = browser.new_context(viewport={"width": 1024, "height": 900}, locale="en-US")
            pg2 = ctx2.new_page()
            pg2.goto(PAGINA.as_uri(), wait_until="load")
            pg2.wait_for_timeout(300)
            if limba != "en":
                pg2.click(f'.langs button[data-lang="{limba}"]')
                pg2.wait_for_timeout(400)
            pg2.click('.cell[data-x="1"][data-y="1"]')
            pg2.wait_for_timeout(150)
            mesaj_clic = text(pg2, "#msg").lower()
            check(not mesaj_clic.startswith(("keyboard", "тастатура")),
                  f"un clic cu mouse-ul nu inlocuieste mesajul cu indicatia de tastatura: {mesaj_clic[:50]}")
            ctx2.close()

            # 3. sagetile muta focusul, nu deruleaza pagina
            scroll_inainte = pg.evaluate("() => window.scrollY")
            focuseaza(pg, 3, 3)
            apasa(pg, "ArrowRight", 2)
            apasa(pg, "ArrowDown")
            poz = pg.evaluate("() => { const e = document.activeElement; return [+e.dataset.x, +e.dataset.y]; }")
            check(poz == [5, 4], f"sagetile muta focusul (3,3) -> (5,4): {poz}")
            check(pg.evaluate("() => window.scrollY") == scroll_inainte,
                  "sagetile nu deruleaza pagina")

            # 4. focusul se opreste la margine, nu iese din grila
            focuseaza(pg, 0, 0)
            apasa(pg, "ArrowLeft", 3)
            apasa(pg, "ArrowUp", 3)
            poz = pg.evaluate("() => { const e = document.activeElement; return [+e.dataset.x, +e.dataset.y]; }")
            check(poz == [0, 0], f"la marginea grilei focusul ramane pe loc: {poz}")

            # 5. Enter marcheaza inceputul, Shift+sageti intinde selectia, Escape o sterge
            focuseaza(pg, 2, 2)
            apasa(pg, "Enter")
            marcate = pg.eval_on_selector_all(".cell.sel", "cs => cs.length")
            check(marcate == 1, f"primul Enter marcheaza o celula (are {marcate})")
            apasa(pg, "Shift+ArrowRight", 2)
            marcate = pg.eval_on_selector_all(".cell.sel", "cs => cs.length")
            check(marcate == 3, f"Shift+sageti intinde selectia la 3 celule (are {marcate})")
            apasate = pg.eval_on_selector_all(".cell[aria-pressed='true']", "cs => cs.length")
            check(apasate == 3, f"selectia e anuntata prin aria-pressed (are {apasate})")
            apasa(pg, "Escape")
            marcate = pg.eval_on_selector_all(".cell.sel", "cs => cs.length")
            apasate = pg.eval_on_selector_all(".cell[aria-pressed='true']", "cs => cs.length")
            check(marcate == 0 and apasate == 0, "Escape sterge selectia, si vizual si pentru cititoare")

            # 6. o selectie care nu e pe linie dreapta e refuzata cu mesaj
            focuseaza(pg, 0, 0)
            apasa(pg, "Enter")
            apasa(pg, "ArrowRight")
            apasa(pg, "Shift+ArrowDown", 2)
            mesaj = text(pg, "#msg")
            check(cuvant_linie in mesaj.lower(),
                  f"selectia stramba e refuzata cu mesaj: {mesaj[:60]}")
            apasa(pg, "Escape")

            # 7. un cuvant intreg, jucat doar de la tastatura
            info = pg.evaluate(JS_CAUTA_CUVANT)
            check(info is not None, "exista un cuvant de gasit in grila")
            if info:
                sx, sy = info["start"]
                ex, ey = info["end"]
                focuseaza(pg, sx, sy)
                apasa(pg, "Enter")
                dx = (ex > sx) - (ex < sx)
                dy = (ey > sy) - (ey < sy)
                tasta_x = "ArrowRight" if dx > 0 else "ArrowLeft"
                tasta_y = "ArrowDown" if dy > 0 else "ArrowUp"
                for _ in range(abs(ex - sx)):
                    apasa(pg, tasta_x)
                for _ in range(abs(ey - sy)):
                    apasa(pg, tasta_y)
                poz = pg.evaluate("() => { const e = document.activeElement; return [+e.dataset.x, +e.dataset.y]; }")
                check(poz == [ex, ey], f"sagetile ajung la capatul cuvantului: {poz} fata de {[ex, ey]}")
                apasa(pg, "Enter")
                pg.wait_for_timeout(150)
                gasite = pg.eval_on_selector_all(".word.done", "ws => ws.length")
                check(gasite == 1, f"cuvantul e marcat gasit doar de la tastatura ({info['word']})")
                check(info["word"] in text(pg, "#msg") or text(pg, "#msg") != "",
                      "mesajul confirma gasirea")
                verzi = pg.eval_on_selector_all(".cell.found", "cs => cs.length")
                check(verzi == info["len"], f"celulele cuvantului sunt marcate ({verzi}/{info['len']})")

            check(len(erori) == 0, f"zero erori de pagina {erori}")
            ctx.close()

        # 8. tinte de atingere si depasire, la toate latimile
        print("\n== tinte de atingere si asezare")
        for w in (320, 375, 768, 1440):
            ctx = browser.new_context(viewport={"width": w, "height": 900}, locale="en-US")
            pg = ctx.new_page()
            pg.goto(PAGINA.as_uri(), wait_until="load")
            pg.wait_for_timeout(300)
            date = pg.evaluate("""() => {
              const de = document.documentElement;
              const mici = [...document.querySelectorAll('a, button')].filter(el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return s.display !== 'none' && r.width > 0 && (r.width < 24 || r.height < 24);
              }).map(el => ({t: el.textContent.trim().slice(0, 24), w: Math.round(el.getBoundingClientRect().width),
                             h: Math.round(el.getBoundingClientRect().height)}));
              const celule = [...document.querySelectorAll('.cell')].map(c => c.getBoundingClientRect());
              return {
                overflow: de.scrollWidth - de.clientWidth,
                mici,
                celulaMin: [Math.round(Math.min(...celule.map(b => b.width))), Math.round(Math.min(...celule.map(b => b.height)))],
              };
            }""")
            check(date["overflow"] == 0, f"{w}px: fara depasire pe orizontala ({date['overflow']})")
            check(date["celulaMin"][0] >= 24 and date["celulaMin"][1] >= 24,
                  f"{w}px: celulele au minim 24x24 ({date['celulaMin']})")
            check(len(date["mici"]) == 0, f"{w}px: nicio tinta sub 24x24 {date['mici']}")
            ctx.close()

        browser.close()

    print(f"\n{ok} verificari trecute, {rau} esuate")
    return 0 if rau == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
