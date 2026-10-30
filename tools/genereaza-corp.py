#!/usr/bin/env python3
"""Scrie blocul `var W = {...};` in fiecare joc, din tests/corpus.json.

O singura sursa de adevar pentru cuvinte. De ce: cuvantul inventat „DORMIȘOARĂ" a ajuns in toate
jocurile pentru ca fiecare fisier isi avea lista lui. Acum se editeaza `tests/corpus.json` si se
ruleaza scriptul; `tests/test_corp.py` verifica apoi ca toate fisierele au exact aceleasi liste.

    python3 tools/genereaza-corp.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / "tests" / "corpus.json"
JOCURI = ["index.html"] + [str(p.relative_to(ROOT)) for p in sorted(ROOT.glob("*/index.html"))
                           if p.parent.name != "tests"]


def bloc(corpus):
    linii = ["var W = {"]
    limbi = list(corpus)
    for n, lim in enumerate(limbi):
        linii.append(f"  {lim}:{{")
        teme = list(corpus[lim])
        for m, tema in enumerate(teme):
            cuvinte = ",".join(json.dumps(c, ensure_ascii=False) for c in corpus[lim][tema])
            virgula = "," if m < len(teme) - 1 else ""
            linii.append(f"    {tema}:[{cuvinte}]{virgula}")
        virgula = "," if n < len(limbi) - 1 else ""
        linii.append(f"  }}{virgula}")
    linii.append("};")
    return "\n".join(linii)


def main():
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    nou = bloc(corpus)
    atinse = 0
    for rel in JOCURI:
        f = ROOT / rel
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        start = text.find("var W = {")
        if start < 0:
            print(f"  SARIT {rel}: nu are bloc var W")
            continue
        sfarsit = text.find("\n};", start)
        if sfarsit < 0:
            print(f"  EROARE {rel}: bloc W fara sfarsit")
            return 1
        sfarsit += len("\n};")
        vechi = text[start:sfarsit]
        if vechi == nou:
            print(f"  neschimbat {rel}")
            continue
        f.write_text(text[:start] + nou + text[sfarsit:], encoding="utf-8")
        atinse += 1
        print(f"  scris {rel}")
    total = sum(len(v) for lim in corpus.values() for v in lim.values())
    print(f"\n{atinse} fisiere actualizate · corpus: {len(corpus)} limbi x 3 teme x "
          f"{len(corpus['ro']['animale'])} cuvinte = {total} intrari")
    return 0


if __name__ == "__main__":
    sys.exit(main())
