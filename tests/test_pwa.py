#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_pwa.py - regula casei: fiecare pagina se instaleaza pe telefon si merge offline.

Ce pazeste:
  1. fiecare pagina are <link rel=manifest> si iconitele (192, 512, maskable, apple-touch-icon);
  2. manifest.json e instalabil: standalone, start_url, scope, theme_color, background_color;
  3. service workerul e FISIER (sw.js), nu inline: pagina doar il inregistreaza, iar CSP-ul
     permite worker-src 'self' (cu 'none' browserul il blocheaza) si connect-src 'self'
     (altfel instalarea pica la cache.addAll);
  4. toate fisierele din SHELL exista pe disc - un 404 acolo face instalarea sa cada;
  5. VERSION se schimba cand se schimba shell-ul (altfel telefonul ramane pe varianta veche).
Se ruleaza din radacina repo-ului: python3 tests/test_pwa.py
"""
import json
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


def main():
    pagini = sorted(p for p in ROOT.rglob("*.html")
                    if "tests" not in p.parts and not p.name.startswith("google"))
    print("== manifest si iconite")
    man = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    check(man.get("display") == "standalone", "manifest: display standalone")
    check(man.get("start_url") and man.get("scope"), "manifest: start_url si scope")
    check(bool(man.get("theme_color")) and bool(man.get("background_color")), "manifest: culori")
    marimi = " ".join(i.get("sizes", "") for i in man.get("icons", []))
    check("192x192" in marimi and "512x512" in marimi, "manifest: iconite 192 si 512")
    check(any(i.get("purpose") == "maskable" for i in man.get("icons", [])), "manifest: iconita maskable")
    for nume in ("icon-192.png", "icon-512.png", "icon-maskable-512.png", "apple-touch-icon.png"):
        check((ROOT / nume).exists(), nume + " exista")

    print("\n== fiecare pagina")
    for p in pagini:
        s = p.read_text(encoding="utf-8")
        relativ = p.relative_to(ROOT).as_posix()
        adancime = len(p.relative_to(ROOT).parts) - 1
        prefix = "../" * adancime
        check('rel="manifest"' in s, relativ + ": are link rel=manifest")
        check('href="%smanifest.json"' % prefix in s, relativ + ": manifestul e legat cu calea corecta")
        check("serviceWorker.register" in s, relativ + ": inregistreaza service workerul")
        check('register("%ssw.js")' % prefix in s, relativ + ": inregistrarea arata spre sw.js")
        check("blob:" not in s.split("serviceWorker.register")[1][:200],
              relativ + ": service workerul nu e inline (fara blob:)")
        check("worker-src 'none'" not in s, relativ + ": CSP nu blocheaza workerul")
        check("connect-src 'none'" not in s,
              relativ + ": CSP nu blocheaza descarcarea shell-ului (connect-src 'self')")
        check('rel="apple-touch-icon"' in s, relativ + ": are apple-touch-icon")

    print("\n== sw.js")
    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    check("importScripts" not in sw, "sw.js nu depinde de alt script")
    shell = re.search(r"var SHELL = \[(.*?)\];", sw, re.S)
    check(shell is not None, "sw.js are lista SHELL")
    if shell:
        fisiere = re.findall(r"'([^']+)'", shell.group(1))
        check(len(fisiere) >= 5, "SHELL are cel putin 5 intrari (%d)" % len(fisiere))
        for f in fisiere:
            cale = ROOT / f.lstrip("./")
            if f in ("./", ""):
                check((ROOT / "index.html").exists(), "SHELL: './' are index.html")
                continue
            if f.endswith("/"):
                check((ROOT / f[2:] / "index.html").exists(), "SHELL: %s are index.html" % f)
                continue
            if cale.exists():
                check(True, "SHELL: %s exista pe disc" % f)
            else:
                # adresa curata (fara .html) - gazda o serveste din fisierul .html
                check((ROOT / (f[2:] + ".html")).exists(),
                      "SHELL: %s exista pe disc (sau ca %s.html)" % (f, f))
    check(re.search(r"var VERSION = '[a-z]+-v\d+'", sw) is not None, "sw.js are VERSION versionat")
    check("redirected" in sw, "sw.js rescrie raspunsurile venite prin redirect (altfel navigarea offline pica)")
    check("catch(function () { return null; })" in sw, "sw.js nu rupe instalarea daca o adresa din SHELL lipseste")

    print("\n== CSP din _headers")
    h = (ROOT / "_headers").read_text(encoding="utf-8")
    check("worker-src 'self'" in h, "_headers permite worker-src 'self'")
    check("connect-src 'self'" in h, "_headers permite connect-src 'self'")
    check("worker-src 'none'" not in h, "_headers nu blocheaza workerul")

    print("\n%d verificari trecute, %d esuate" % (ok, rau))
    return 0 if rau == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
