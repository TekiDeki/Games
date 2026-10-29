# -*- coding: utf-8 -*-
"""verifica_cuvinte.py - verifica toate cuvintele din jocuri in dictionare online.

python3 tests/verifica_cuvinte.py        (are nevoie de internet)

Surse: dexonline.ro (ro), api.dictionaryapi.dev (en), en.wiktionary.org (sr, src).
Scrie raport.json in directorul curent.

Capcane (de ce arata codul asa):
  1. API-ul Wikimedia (api.php, REST) e blocat din sandbox-ul asta (trafic de bot). Paginile
     HTML normale merg, deci verificarea se face pe HTML, nu pe API.
  2. en.wiktionary e sensibil la majuscule: "MOST" da 404, "most" da 200.
  3. Lista se citeste din jocurile din depozit, ca sa nu se verifice o copie invechita.
"""
import html, json, re, subprocess, time, urllib.parse

import os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOC = os.path.join(REPO, "ghiceste-cuvantul", "index.html")
if not os.path.exists(JOC):                       # script copiat in alta parte
    JOC = os.path.join(os.getcwd(), "ghiceste-cuvantul", "index.html")

def liste():
    """listeaza cuvintele din jocul 1 (lista canonica a site-ului)"""
    s = open(JOC, encoding="utf-8").read()
    bloc = re.search(r"var W = (\{.*?\n\});", s, re.S).group(1)
    return json.loads(re.sub(r"([{,])\s*([A-Za-z_]\w*)\s*:", r'\1"\2":', bloc))

DATE = liste()
UA = "games-wordcheck/1.0 (github.com/TekiDeki)"

def curl(url, timeout=30):
    r = subprocess.run(["curl", "-sL", "-m", str(timeout), "-A", UA, "-w", "\n@@%{http_code}", url],
                       capture_output=True, text=True)
    out = r.stdout
    cod = out.rsplit("@@", 1)[-1].strip() if "@@" in out else "000"
    corp = out.rsplit("\n@@", 1)[0] if "@@" in out else out
    return cod, corp

def curat(t):
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def ro(w):
    cod, corp = curl("https://dexonline.ro/definitie/" + urllib.parse.quote(w.lower()))
    i = corp.find('class="def"')
    if i < 0:
        return False, "dexonline: nicio definitie (HTTP " + cod + ")"
    bucata = corp[i:i + 3000]
    bucata = bucata.split("</span></span>")[0]
    d = curat(bucata)
    d = re.sub(r"^def[^ ]* *", "", d)
    return True, d[:150]

def en(w):
    cod, corp = curl("https://api.dictionaryapi.dev/api/v2/entries/en/" + urllib.parse.quote(w.lower()))
    try:
        d = json.loads(corp)
    except Exception:
        return False, "dictionaryapi: raspuns neasteptat (HTTP " + cod + ")"
    if isinstance(d, dict) or not d:
        return False, "dictionaryapi: negasit (HTTP " + cod + ")"
    for p in d[0].get("meanings", []):
        for df in p.get("definitions", []):
            if df.get("definition"):
                return True, (p.get("partOfSpeech", "") + ": " + df["definition"])[:150]
    return True, "(fara definitie in raspuns)"

def wiktionary(w, limbi):
    mic = w.lower()                      # ATENTIE: en.wiktionary e sensibil la majuscule
    cod, corp = curl("https://en.wiktionary.org/wiki/" + urllib.parse.quote(mic))
    if cod != "200":
        return False, "en.wiktionary: pagina lipseste (HTTP " + cod + ")"
    gasite = [l for l in limbi if re.search(r'id="%s"' % re.escape(l), corp)]
    if not gasite:
        return False, "en.wiktionary: pagina exista, dar fara secțiunea " + "/".join(limbi)
    i = corp.find('id="%s"' % gasite[0])
    bucata = corp[i:i + 12000]
    m = re.search(r"<li>(.*?)</li>", bucata, re.S)
    return True, "[" + gasite[0] + "] " + (curat(m.group(1))[:130] if m else "")

def sr_local(w):
    cod, corp = curl("https://sr.wiktionary.org/wiki/" + urllib.parse.quote(w.lower()))
    if cod != "200":
        return False, "sr.wiktionary: HTTP " + cod
    return True, "sr.wiktionary: pagina exista"

LIMIT = int(os.environ.get("LIMIT", "0"))    # 0 = toate; altfel cate cuvinte pe fiecare limba
rez = []
for limba in ["ro", "en", "sr", "src"]:
    for tema, cuvinte in DATE[limba].items():
        for w in (cuvinte[:LIMIT] if LIMIT else cuvinte):
            if limba == "ro":
                ok, d = ro(w); sursa = "dexonline"
            elif limba == "en":
                ok, d = en(w); sursa = "dictionaryapi.dev"
            else:
                ok, d = wiktionary(w, ["Serbo-Croatian", "Serbian"]); sursa = "en.wiktionary"
                if not ok:
                    ok2, d2 = sr_local(w)
                    if ok2: ok, d, sursa = True, d2, "sr.wiktionary"
            rez.append({"limba": limba, "tema": tema, "cuvant": w, "ok": ok,
                        "definitie": d, "sursa": sursa})
            print(("  OK    " if ok else "  LIPSA ") + "%-13s %-4s %-9s %s" % (w, limba, tema, d[:85]))
            time.sleep(0.7)

json.dump(rez, open("raport.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
lipsa = [r for r in rez if not r["ok"]]
print("\n%d cuvinte verificate, %d negasite" % (len(rez), len(lipsa)))
for r in lipsa: print("  NEGASIT:", r["cuvant"], r["limba"], "-", r["definitie"])
