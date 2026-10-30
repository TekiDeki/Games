#!/usr/bin/env python3
"""Promisiuni: paginile nu au voie sa spuna „merge fara internet" fara un service worker.

De ce exista testul: subsolul celor opt jocuri spunea „Merge si fara internet dupa prima
incarcare". Nu era adevarat: in Chromium, dupa incarcare si apoi offline, pagina nu se mai
incarca (nu exista service worker). Promisiunea a fost scoasa pe 30.10.2026. Testul pazeste
locul, ca sa nu reapara din obisnuinta: daca cineva o scrie din nou, trebuie sa aduca si
service worker-ul care o face adevarata.

Se uita la toate paginile gasite, nu la o lista scrisa de mana.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ok = 0
rau = 0

# formulari de promisiune offline, in cele patru limbi ale site-ului
MODEL = re.compile(r"offline|f[ăa]r[ăa] internet|bez interneta|без интернета", re.IGNORECASE)


def check(cond, mesaj):
    global ok, rau
    if cond:
        ok += 1
        print("  ok   " + mesaj)
    else:
        rau += 1
        print("  RAU  " + mesaj)


def pagini():
    gasite = sorted(ROOT.glob("*/index.html"))
    if (ROOT / "index.html").exists():
        gasite.insert(0, ROOT / "index.html")
    return gasite


def main():
    toate = pagini()
    check(len(toate) >= 9, f"au fost gasite toate paginile ({len(toate)})")

    for p in toate:
        nume = p.relative_to(ROOT)
        text = p.read_text(encoding="utf-8")
        are_sw = "serviceWorker" in text and "register(" in text
        atins = sorted(set(m.group(0).lower() for m in MODEL.finditer(text)))
        if atins and not are_sw:
            check(False, f"{nume}: promite offline ({atins}) dar nu are service worker")
        else:
            check(True, f"{nume}: fara promisiune de offline fara service worker")

    # pagina principala nu mai pune eticheta „offline" pe carduri
    hub = ROOT / "index.html"
    if hub.exists():
        h = hub.read_text(encoding="utf-8")
        check(">offline<" not in h, "hubul nu mai are eticheta „offline” pe carduri")

    # ce a ramas in subsol e o descriere verificabila, nu o promisiune despre viitor
    for p in toate:
        nume = p.relative_to(ROOT)
        text = p.read_text(encoding="utf-8")
        if "foot" in text:
            check("rămâne gratuit" not in text or "supportText" in text,
                  f"{nume}: textul de sustinere e in continuare legat de linkul PayPal")

    print(f"\n{ok} verificari trecute, {rau} esuate")
    return 0 if rau == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
