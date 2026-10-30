#!/usr/bin/env python3
"""Verifica o singura sursa de adevar pentru cuvinte: tests/corpus.json.

Ce prinde:
  1. corpusul e sanatos: 48 de cuvinte pe limba, 16 pe tema, toate unice, majuscule, 2-12 litere;
  2. toate jocurile au EXACT aceleasi liste (nu doar ca au numarul potrivit) - asta e testul care ar
     fi prins „DORMIȘOARĂ" ajuns in toate fisierele si reparat in niciunul;
  3. sârba latină si cea chirilica sunt transliterari una alteia, cuvant cu cuvant;
  4. fiecare cuvant are doar litere (fara cifre, spatii, cratime).

Iese cu cod 1 la orice diferenta.
"""
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / "tests" / "corpus.json"
LIMBI = ["ro", "en", "sr", "src"]
TEME = ["animale", "mancare", "locuri"]

# transliterare sârba: digrafii intai, apoi literele simple
DIGRAFII = [("DŽ", "Џ"), ("LJ", "Љ"), ("NJ", "Њ")]
LITERE = {"A": "А", "B": "Б", "C": "Ц", "Č": "Ч", "Ć": "Ћ", "D": "Д", "Đ": "Ђ", "E": "Е",
          "F": "Ф", "G": "Г", "H": "Х", "I": "И", "J": "Ј", "K": "К", "L": "Л", "M": "М",
          "N": "Н", "O": "О", "P": "П", "R": "Р", "S": "С", "Š": "Ш", "T": "Т", "U": "У",
          "V": "В", "Z": "З", "Ž": "Ж"}

ok = 0
rau = 0


def check(cond, mesaj):
    global ok, rau
    if cond:
        ok += 1
    else:
        rau += 1
        print("  RAU  " + mesaj)


def translitereaza(cuvant):
    rest = cuvant
    for lat, cir in DIGRAFII:
        rest = rest.replace(lat, cir)
    out = []
    for ch in rest:
        out.append(LITERE.get(ch, ch))
    return "".join(out)


def main():
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))

    print("== corpusul")
    check(set(corpus) == set(LIMBI), f"are exact limbile {LIMBI}, nu {list(corpus)}")
    for lim in LIMBI:
        check(set(corpus[lim]) == set(TEME), f"{lim}: are exact temele {TEME}")
        toate = []
        for tema in TEME:
            lista = corpus[lim][tema]
            check(len(lista) == 16, f"{lim}/{tema}: 16 cuvinte (are {len(lista)})")
            toate += lista
        check(len(toate) == 48, f"{lim}: 48 de cuvinte (are {len(toate)})")
        check(len(set(toate)) == len(toate), f"{lim}: niciun cuvant repetat")
        for w in toate:
            check(w == w.upper(), f"{lim}: {w} e scris cu majuscule")
            check(2 <= len(w) <= 12, f"{lim}: {w} are 2-12 litere ({len(w)})")
            check(all(unicodedata.category(c).startswith("L") for c in w),
                  f"{lim}: {w} are doar litere")
            check(not any(c.isascii() and c.isdigit() for c in w), f"{lim}: {w} fara cifre")

    print("== transliterare sârba")
    perechi = 0
    for tema in TEME:
        for lat, cir in zip(corpus["sr"][tema], corpus["src"][tema]):
            perechi += 1
            check(translitereaza(lat) == cir, f"{lat} ar trebui sa fie {translitereaza(lat)}, nu {cir}")
    print(f"  {perechi} perechi latină-chirilică verificate")

    print("== fisierele jocurilor")
    fisiere = sorted(p for p in ROOT.glob("*/index.html") if p.parent.name != "tests")
    check(len(fisiere) >= 6, f"am gasit {len(fisiere)} jocuri")
    for f in fisiere:
        text = f.read_text(encoding="utf-8")
        start = text.find("var W = {")
        check(start >= 0, f"{f.parent.name}: are blocul var W")
        if start < 0:
            continue
        sfarsit = text.find("\n};", start)
        bloc = text[start:sfarsit]
        # taie blocul pe limbi: fiecare incepe la "  ro:{" etc.
        bucati = {}
        for lim in LIMBI:
            i = bloc.find(f"  {lim}:{{")
            if i < 0:
                break
            urmator = [bloc.find(f"  {x}:{{", i + 1) for x in LIMBI if bloc.find(f"  {x}:{{", i + 1) > 0]
            bucati[lim] = bloc[i:min(urmator) if urmator else len(bloc)]
        for lim in LIMBI:
            check(lim in bucati, f"{f.parent.name}: are secțiunea {lim}")
            if lim not in bucati:
                continue
            for tema in TEME:
                # scoate lista exact asa cum e scrisa in fisier
                m = re.search(rf'{tema}:\[(.*?)\]', bucati[lim])
                check(m is not None, f"{f.parent.name}: are lista {tema}")
                if not m:
                    continue
                in_fisier = json.loads("[" + m.group(1) + "]")
                check(in_fisier == corpus[lim][tema],
                      f"{f.parent.name}/{lim}/{tema}: lista difera de corpus.json")
    print(f"\n{ok} verificari trecute, {rau} esuate")
    return 0 if rau == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
