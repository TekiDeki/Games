#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Datele si integrarea jocului Translation Pairs.

Harta este o lista de concepte cu traduceri explicite. Nu se deduc perechi din
pozitia cuvintelor in tests/corpus.json: listele corpusului nu sunt aliniate.
"""
import json
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "tests" / "translations.json"
PAGE = ROOT / "translation-pairs" / "index.html"
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


def translit(text):
    multi = {"LJ": "Љ", "NJ": "Њ", "DŽ": "Џ"}
    one = dict(zip(
        "ABCČĆDĐEFGHIJKLMNOPRSŠTUVZŽ",
        "АБЦЧЋДЂЕФГХИЈКЛМНОПРСШТУВЗЖ",
    ))
    for latin, cyr in multi.items():
        text = text.replace(latin, cyr)
    return "".join(one.get(ch, ch) for ch in text)


def main():
    check(DATA.is_file(), "tests/translations.json exista")
    check(PAGE.is_file(), "translation-pairs/index.html exista")
    if not DATA.is_file() or not PAGE.is_file():
        print("\n%d verificari trecute, %d esuate" % (ok, rau))
        return 1

    entries = json.loads(DATA.read_text(encoding="utf-8"))
    html = PAGE.read_text(encoding="utf-8")
    check(isinstance(entries, list), "harta este o lista de concepte")
    check(len(entries) == 24, "24 de concepte, suficiente pentru 8 perechi pe tema")
    check(Counter(e.get("tema") for e in entries) == Counter({"animale": 8, "mancare": 8, "locuri": 8}),
          "fiecare tema are exact 8 concepte")
    ids = [e.get("id") for e in entries]
    check(len(set(ids)) == len(ids) and all(isinstance(i, str) and i for i in ids),
          "fiecare concept are un id explicit si unic")
    check(all(isinstance(e, dict) for e in entries), "fiecare intrare este un obiect semantic")
    check(all(set(e) == {"id", "tema", "ro", "en", "sr", "src"} for e in entries),
          "toate intrarile au exact cele patru traduceri si tema")

    alphabets = {
        "ro": set("ABCDEFGHIJKLMNOPRSTUVWXYZĂÂÎȘȚ"),
        "en": set("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        "sr": set("ABCCČĆDĐEFGHIJKLMNOPRSŠTUVWXYZZŽ"),
        "src": set("АБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШ"),
    }
    for lang in ("ro", "en", "sr", "src"):
        words = [e[lang] for e in entries]
        check(all(2 <= len(w) <= 12 for w in words), f"{lang}: toate cuvintele au 2..12 litere")
        check(all(set(w) <= alphabets[lang] for w in words), f"{lang}: alfabet corect")
        check(len(set(words)) == len(words), f"{lang}: nu exista duplicate in harta")
    check(all(e["src"] == translit(e["sr"]) for e in entries),
          "sr-Latn si sr-Cyrl sunt aceleasi concepte, transliterate")
    check(not any(ch in "".join(e["src"] for e in entries) for ch in "ЁЪЫЭЮЯЩ"),
          "chirilica nu contine litere rusesti ne-sarbe")

    marker = "var PAIRS = "
    start = html.find(marker)
    check(start >= 0, "pagina inglobeaza var PAIRS")
    if start >= 0:
        start += len(marker)
        try:
            embedded, end = json.JSONDecoder().raw_decode(html[start:])
            check(embedded == entries, "var PAIRS este identic cu tests/translations.json")
            check(html[start + end:].lstrip().startswith(";"), "blocul de date se termina cu ;")
        except Exception as exc:
            check(False, "var PAIRS este JSON valid: " + str(exc))
    check("name=\"joc-date\" content=\"traduceri\"" in html,
          "pagina declara sursa de date separata de corpus")
    check("var W = {" not in html, "jocul nu pretinde ca foloseste corpusul nealiniat")
    check("—" not in html, "nu exista em dash in pagina")

    hub = (ROOT / "index.html").read_text(encoding="utf-8")
    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    check('href="translation-pairs/"' in hub, "hub-ul are cardul jocului")
    check("'./translation-pairs/'" in sw, "service worker-ul include jocul in shell")
    check("https://games.freehtml.dev/translation-pairs/" in sitemap, "sitemap-ul include URL-ul")

    print("\n%d verificari trecute, %d esuate" % (ok, rau))
    return 1 if rau else 0


if __name__ == "__main__":
    sys.exit(main())
