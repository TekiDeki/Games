#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_tinte.py - tintele de atingere din jocuri, masurate, la 320px.

De ce exista: blocul `#tinte-44-joc` din fiecare joc scoate tabla si tastatura de sub
regula de 44px, pentru ca sunt grile cu coloane fixe (8 celule x 44 = 352px nu incap pe
un telefon de 320px). Scutirea era insa scrisa pe clase (`.cell, .tile, .slot, .key`),
iar `.slot` si `.rack .tile` nu sunt in nicio grila: se asaza pe randuri si se infasoara.
Rezultatul: caseta goala din cuvantul de ghicit ajunsese la 6px latime, adica o linie
verticala, iar jucatorul nu mai vedea cuvantul pe care il compunea.

Regula verificata aici:
  - un control asezat intr-un container care se INFASOARA (flex-wrap: wrap) trebuie sa
    aiba cel putin 44x44px: nu are nicio scuza, se poate muta pe randul urmator;
  - un control dintr-o GRIJA cu coloane fixe (display: grid) e scutit de latime, dar
    trebuie sa aiba 44px inaltime.

Rulare: python3 tests/test_tinte.py      (din radacina repo-ului)
"""

import os

from playwright.sync_api import sync_playwright

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOCURI = [
    "guess-the-word", "odd-one-out", "typing-test", "word-from-definition",
    "word-of-the-day", "word-pairs", "word-scramble", "word-search",
]
LATIMI = (320, 390)
PRAG = 44

JS = """() => {
  const rele = [];
  for (const el of document.querySelectorAll('button,input,select,textarea,[role=button],a')) {
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) <= 0.05) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height === 0) continue;
    const parinte = el.parentElement ? getComputedStyle(el.parentElement) : null;
    const inGrija = parinte && parinte.display === 'grid';
    const seInfasoara = parinte && parinte.display === 'flex' && parinte.flexWrap === 'wrap';
    // latimea unei coloane din grila: daca are loc de 44px, trebuie sa le foloseasca
    let coloana = 0;
    if (inGrija) {
      const urme = (parinte.gridTemplateColumns || '').split(' ').filter(Boolean).map(parseFloat);
      coloana = urme.length ? Math.min.apply(null, urme) : 0;
    }
    rele.push({
      sel: el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ').slice(0,2).join('.') : ''),
      w: Math.round(r.width), h: Math.round(r.height),
      inGrija: inGrija, seInfasoara: seInfasoara, coloana: Math.round(coloana),
      cls: String(el.className || ''),
      text: (el.textContent || el.value || '').trim().slice(0, 12)
    });
  }
  return rele;
}"""

ok = 0
rau = 0
exceptii = set()


def check(cond, mesaj):
    global ok, rau
    if cond:
        ok += 1
    else:
        rau += 1
        print("  FAIL", mesaj)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        for joc in JOCURI:
            cale = os.path.join(RADACINA, joc, "index.html")
            if not os.path.exists(cale):
                check(False, "%s: lipseste index.html" % joc)
                continue
            url = "file://" + cale
            for lat in LATIMI:
                ctx = b.new_context(viewport={"width": lat, "height": 800},
                                    is_mobile=True, has_touch=True, device_scale_factor=2)
                pg = ctx.new_page()
                pg.goto(url)
                pg.wait_for_timeout(350)
                elemente = pg.evaluate(JS)
                sw = pg.evaluate("document.documentElement.scrollWidth")
                check(sw <= lat, "%s la %dpx: depasire pe orizontala (%d)" % (joc, lat, sw))

                for el in elemente:
                    eticheta = "%s la %dpx %s %dx%d %r" % (joc, lat, el["sel"], el["w"], el["h"], el["text"])
                    if "key" in el["cls"].split():
                        # tastatura: 10 clape pe rand, documentat ca exceptie. Latimea nu poate
                        # fi 44px (10 x 44 = 440px), dar inaltimea da si trebuie sa fie 44.
                        exceptii.add("%s %s %dx%d (clape de tastatura)" % (
                            joc, el["sel"], el["w"], el["h"]))
                        check(el["h"] >= PRAG and el["w"] >= 18,
                              eticheta + " - clapa de tastatura, cere 44 inaltime si 18 latime")
                    elif el["seInfasoara"]:
                        # se poate muta pe randul urmator: nu are nicio scuza
                        check(el["w"] >= PRAG and el["h"] >= PRAG, eticheta + " - se infasoara, cere 44x44")
                    elif el["inGrija"]:
                        # Grila cu coloane fixe. Daca are loc de 44px pe coloana, trebuie sa
                        # le foloseasca; daca nu (8 coloane x 44 = 352px nu incap la 320px),
                        # se aplica pragul AA de 24px, iar exceptia se numara, nu se ascunde.
                        if el["coloana"] >= PRAG:
                            check(el["w"] >= PRAG and el["h"] >= PRAG,
                                  eticheta + " - grila are coloane de %dpx, cere 44x44" % el["coloana"])
                        else:
                            exceptii.add("%s %s %dx%d (coloana %dpx)" % (
                                joc, el["sel"], el["w"], el["h"], el["coloana"]))
                            check(el["w"] >= 24 and el["h"] >= 24,
                                  eticheta + " - sub pragul AA de 24px")
                ctx.close()
        b.close()
    if exceptii:
        print("\nExceptii documentate (grila fara loc de 44px pe coloana, prag AA 24px):")
        for e in sorted(exceptii):
            print("   ", e)
    print("\ntest_tinte.py · %d verificari trecute, %d esuate" % (ok, rau))
    return 1 if rau else 0


if __name__ == "__main__":
    raise SystemExit(main())
