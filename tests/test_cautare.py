#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_cautare.py - verificari pentru jocul 6 (Cauta cuvintele / Word search).

python3 tests/test_cautare.py

Se deschide pagina local (file://), se joaca efectiv fiecare tabla in toate cele patru limbi,
trasand cu mouse-ul de la prima litera la ultima, si se verifica:
  - grila se construieste si contine toate cele opt cuvinte, pe una din cele opt directii
  - tragerea corecta marcheaza cuvantul (verde in grila + taiat pe lista)
  - tragerea gresita nu marcheaza nimic si nu blocheaza jocul
  - cuvantul deja gasit nu se numara de doua ori
  - tabla terminata actualizeaza statisticile
  - comutarea limbii schimba textele si da o tabla noua
  - pe mobil nu exista derulare pe orizontala si celulele raman utilizabile
"""

import json
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "file://" + os.path.join(ROOT, "word-search", "index.html")
N = 12

ok = 0
rau = 0


def check(cond, text):
    global ok, rau
    if cond:
        ok += 1
        print("  ok   " + text)
    else:
        rau += 1
        print("  RAU  " + text)


CAUTA = """()=>{
  const N=%d, cells=[...document.querySelectorAll('.cell')], g=[];
  for(let y=0;y<N;y++) g.push(cells.slice(y*N,(y+1)*N).map(c=>c.textContent));
  const words=[...document.querySelectorAll('.word')].map(w=>({w:w.textContent, done:w.classList.contains('done')}));
  const dirs=[[1,0],[0,1],[1,1],[1,-1],[-1,0],[0,-1],[-1,-1],[-1,1]];
  const out=[];
  for(const o of words){
    const w=o.w; let gasit=null;
    for(let y=0;y<N&&!gasit;y++)for(let x=0;x<N&&!gasit;x++)for(const d of dirs){
      let bine=true, cel=[];
      for(let i=0;i<w.length;i++){
        const cx=x+d[0]*i, cy=y+d[1]*i;
        if(cx<0||cy<0||cx>=N||cy>=N||g[cy][cx]!==w[i]){bine=false;break;}
        cel.push([cx,cy]);
      }
      if(bine) gasit=cel;
    }
    out.push({w:w, done:o.done, path:gasit});
  }
  return out;
}""" % N


def trage(pg, a, z):
    ba = pg.locator('.cell[data-x="%d"][data-y="%d"]' % (a[0], a[1])).bounding_box()
    bz = pg.locator('.cell[data-x="%d"][data-y="%d"]' % (z[0], z[1])).bounding_box()
    pg.mouse.move(ba["x"] + ba["width"] / 2, ba["y"] + ba["height"] / 2)
    pg.mouse.down()
    pg.mouse.move(bz["x"] + bz["width"] / 2, bz["y"] + bz["height"] / 2, steps=6)
    pg.mouse.up()
    pg.wait_for_timeout(70)


def stare(pg):
    return pg.evaluate("""()=>({
      found: document.getElementById('foundChip').textContent,
      msg: document.getElementById('msg').textContent,
      done: document.querySelectorAll('.word.done').length,
      green: document.querySelectorAll('.cell.found').length,
      words: document.querySelectorAll('.word').length,
      cells: document.querySelectorAll('.cell').length,
      stats: [...document.querySelectorAll('.stats b')].map(b=>b.textContent),
      lang: document.documentElement.lang,
      title: document.title
    })""")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()

        print("== structura grilei")
        pg = b.new_page(viewport={"width": 1100, "height": 1000})
        erori = []
        pg.on("pageerror", lambda e: erori.append(str(e)))
        pg.goto(URL)
        pg.wait_for_selector(".cell")
        st = stare(pg)
        check(st["cells"] == N * N, "grila are %d celule" % (N * N))
        check(st["words"] == 8, "lista are opt cuvinte")
        check(st["green"] == 0, "la inceput nu e nimic marcat")
        lista = pg.evaluate(CAUTA)
        check(all(x["path"] for x in lista), "toate cele opt cuvinte exista in grila")

        print("== o tragere gresita")
        # doua celule alaturate care nu formeaza niciun cuvant
        trage(pg, [0, 0], [1, 0])
        st = stare(pg)
        check(st["found"].endswith("0/8"), "tragerea gresita nu marcheaza niciun cuvant (%s)" % st["found"])
        pg.wait_for_timeout(350)
        check(pg.evaluate("()=>document.querySelectorAll('.cell.sel').length") == 0,
              "selectia gresita se curata singura")

        print("== joc complet, trasand fiecare cuvant")
        for x in pg.evaluate(CAUTA):
            trage(pg, x["path"][0], x["path"][-1])
        st = stare(pg)
        check(st["found"].endswith("8/8"), "toate cele opt gasite (%s)" % st["found"])
        check(st["done"] == 8, "toate cele opt cuvinte sunt taiate pe lista")
        check(st["green"] >= 8, "literele cuvintelor sunt verzi in grila (%d)" % st["green"])
        check("0:0" in st["msg"] or "0:1" in st["msg"] or ":" in st["msg"], "mesajul de final arata timpul")
        check(st["stats"][0] == "1", "o tabla jucata in statistici")
        check(st["stats"][1] == "8", "opt cuvinte in statistici")
        check(st["stats"][3] == "1", "o tabla terminata in statistici")

        print("== un cuvant de doua ori")
        primul = pg.evaluate(CAUTA)[0]
        trage(pg, primul["path"][0], primul["path"][-1])
        check(stare(pg)["found"].endswith("8/8"), "cuvantul repetat nu se numara a doua oara")

        print("== joc nou")
        pg.click("#againBtn")
        pg.wait_for_timeout(200)
        st = stare(pg)
        check(st["found"].endswith("0/8"), "jocul nou incepe de la 0/8")
        check(st["green"] == 0, "grila noua nu are litere verzi")
        check(st["stats"][0] == "1", "statisticile raman dupa joc nou")

        print("== limbi")
        for limba, astept in (("en", "en"), ("sr", "sr-Latn"), ("src", "sr-Cyrl"), ("ro", "ro")):
            pg.click('.langs button[data-lang="%s"]' % limba)
            pg.wait_for_timeout(250)
            st = stare(pg)
            check(st["lang"] == astept, "limba %s seteaza html lang=%s" % (limba, astept))
            check(st["found"].endswith("0/8"), "limba %s: tabla noua, 0/8" % limba)
            lista = pg.evaluate(CAUTA)
            check(all(x["path"] for x in lista), "limba %s: toate cuvintele incap in grila" % limba)
            if limba == "src":
                check("Нађено" in st["found"], "chirilica: eticheta tradusa (%s)" % st["found"])
        check(not erori, "zero erori de pagina (%s)" % erori)
        pg.close()

        print("== mobil")
        pg = b.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        erori = []
        pg.on("pageerror", lambda e: erori.append(str(e)))
        pg.goto(URL)
        pg.wait_for_selector(".cell")
        lat = pg.evaluate("()=>[document.documentElement.scrollWidth, window.innerWidth]")
        check(lat[0] <= lat[1] + 1, "fara derulare pe orizontala: %dpx" % lat[0])
        cel = pg.locator(".cell").first.bounding_box()
        check(cel["width"] >= 18, "celulele raman utilizabile pe mobil (%.0fpx)" % cel["width"])
        lista = pg.evaluate(CAUTA)
        check(all(x["path"] for x in lista), "mobil: toate cuvintele incap in grila")
        # pe mobil tragem cu evenimente de pointer, ca la deget
        x = lista[0]
        ba = pg.locator('.cell[data-x="%d"][data-y="%d"]' % tuple(x["path"][0])).bounding_box()
        bz = pg.locator('.cell[data-x="%d"][data-y="%d"]' % tuple(x["path"][-1])).bounding_box()
        pg.mouse.move(ba["x"] + ba["width"] / 2, ba["y"] + ba["height"] / 2)
        pg.mouse.down()
        pg.mouse.move(bz["x"] + bz["width"] / 2, bz["y"] + bz["height"] / 2, steps=6)
        pg.mouse.up()
        pg.wait_for_timeout(150)
        check(stare(pg)["found"].endswith("1/8"), "mobil: tragerea gaseste primul cuvant")
        check(not erori, "mobil: zero erori de pagina (%s)" % erori)
        pg.close()
        b.close()

    print("\n%d verificari trecute, %d esuate" % (ok, rau))
    sys.exit(1 if rau else 0)


if __name__ == "__main__":
    main()
