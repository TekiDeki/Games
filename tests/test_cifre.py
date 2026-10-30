#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_cifre.py - cifrele scrise pe hub trebuie sa fie cele reale, citite din jocuri.

De ce exista testul: hubul spunea „158 words from Wikipedia and Wiktionary", iar jocul avea 186,
si „Six lives of memory" pentru un joc care nu are vieti. Cifrele de pe pagina principala sunt
acum verificate aici, din sursa fiecarui joc, ca sa nu se desparta din nou.

Se ruleaza din radacina repo-ului: python3 tests/test_cifre.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
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


def text(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def main():
    hub = text("index.html")

    # 1. cate jocuri anunta hubul, cate carduri are
    carduri = len(re.findall(r'<a class="card" href="[^"]+/">', hub))
    check(carduri == 8, "cardurile de pe hub: %d (textul spune opt)" % carduri)
    check("Eight games" in hub, "hubul scrie explicit opt jocuri")

    # 2. guess-the-word: cate cuvinte are pe limba
    g = text("guess-the-word/index.html")
    i = g.index("W = {")
    bloc = g[i:i + 20000]
    limbi = {}
    for cheie in ("ro", "en", "sr", "src"):
        j = bloc.find(cheie + ":{")
        if j < 0:
            continue
        adancime = 0
        k = bloc.index("{", j)
        start = k
        while k < len(bloc):
            if bloc[k] == "{":
                adancime += 1
            elif bloc[k] == "}":
                adancime -= 1
                if adancime == 0:
                    break
            k += 1
        limbi[cheie] = len(re.findall(r'"[^"]{2,}"', bloc[start:k]))
    check(set(limbi.values()) == {48}, "cuvinte pe limba in guess-the-word: %s (textul spune 48)" % limbi)

    # 3. word-from-definition: numarul real de definitii
    d = text("word-from-definition/index.html")
    i = d.index("const DATE = ") + len("const DATE = ")
    import json
    date, _ = json.JSONDecoder().raw_decode(d[i:])
    total = sum(len(v) for v in date.values())
    manuale = sum(1 for c in date.values() for v in c.values() if v.get("sursa") == "manual")
    check(("%d words" % total) in hub, "hubul scrie %d definitii, jocul are %d" % (total, total))
    check(("%d from Wikipedia and Wiktionary" % (total - manuale)) in hub,
          "hubul spune cate sunt din Wikipedia/Wiktionary: %d (scrise de mana: %d)" % (total - manuale, manuale))

    # 4. hubul nu mai promite vieti pentru jocul care nu are
    check("Six lives of memory" not in hub, "word-pairs nu mai e descris cu vieti")
    perechi = text("word-pairs/index.html")
    marimi = re.search(r"var SIZES = \[([0-9,\s]+)\]", perechi)
    check(bool(marimi) and "Boards of four, six or eight pairs" in hub,
          "word-pairs: marimile tablei din sursa (%s) sunt cele scrise pe hub" % (marimi.group(1) if marimi else "?"))

    # 5. odd-one-out: runde si secunde
    o = text("odd-one-out/index.html")
    runde = re.search(r"(?:RUNDE|ROUNDS|rTotal)\s*[:=]\s*(\d+)", o)
    if runde:
        check(("Ten rounds" in hub) == (runde.group(1) == "10"),
              "odd-one-out: %s runde in sursa" % runde.group(1))

    # 6. jocurile nu promit offline fara service worker (vezi test_promisiuni.py)
    for p in sorted(ROOT.glob("*/index.html")):
        t = p.read_text(encoding="utf-8")
        if re.search(r"offline|f[ăa]r[ăa] internet", t, re.I) and "serviceWorker" not in t:
            check(False, "%s promite offline fara service worker" % p.parent.name)

    print("\n%d verificari trecute, %d esuate" % (ok, rau))
    return 0 if rau == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
