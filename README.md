# Games

Small browser games, one HTML file each. No account, no ads, no tracking, nothing sent to a server.

**Live:** https://games.freehtml.dev (Cloudflare Pages, canonical)
**Mirror:** https://tekideki.github.io/Games/ (GitHub Pages, same files, canonical points here)

Shortcut: **https://freehtml.dev/games** (302)

## Games

| Game | Path | Languages | What it is |
|---|---|---|---|
| Guess the word | `/ghiceste-cuvantul/` | EN, RO, SR Latin, SR Cyrillic | Hangman on themes. 96 words, 6 lives, one letter hint, local stats. |
| Word pairs | `/perechi-cuvinte/` | EN, RO, SR Latin, SR Cyrillic | Memory game. Same 96 words, board of 4, 6 or 8 pairs, moves and time, local stats. |
| Word scramble | `/amesteca-literele/` | EN, RO, SR Latin, SR Cyrillic | Anagrams. Same 96 words, tap letters into place, one letter hint, physical keyboard, local stats. |
| Word of the day | `/cuvantul-zilei/` | EN, RO, SR Latin, SR Cyrillic | Deduction. One word per day, same for everyone, six tries, green/yellow/grey per letter, shareable emoji grid, free play mode. |
| Odd one out | `/gaseste-intrusul/` | EN, RO, SR Latin, SR Cyrillic | Categories. Four words, three from one theme, pick the intruder. Ten rounds, twelve seconds each, streak bonus. |
| Word search | `/cautare-de-cuvinte/` | EN, RO, SR Latin, SR Cyrillic | Hidden words. Same 96 words, 12 by 12 grid, eight words per table, all eight directions, drag from the first letter to the last, local stats. |

## House rules

- Single file per game: HTML, CSS, JS and SVG all inline. No build step, no dependencies, no CDN.
- Four language versions everywhere: `en`, `ro`, `sr-Latn`, `sr-Cyrl`. Not Russian - Serbian Cyrillic, 30 letters, no Ё Ъ Ы Э Ю Я Щ.
- `<html lang>`, `<title>`, `<meta description>` and the JSON-LD all change with the language.
- Light and dark, follows the system setting, manual toggle.
- Support line in the footer: `https://PayPal.me/TekiDeki`. No Ko-fi, no Patreon.
- Words are always checked against the alphabet of their own language - a word that cannot be typed is a bug.

## Structure

```
index.html                 hub, lists the games
ghiceste-cuvantul/
  index.html               the game (single file)
perechi-cuvinte/
  index.html               the game (single file)
amesteca-literele/
  index.html               the game (single file)
cuvantul-zilei/
  index.html               the game (single file)
gaseste-intrusul/
  index.html               the game (single file)
cautare-de-cuvinte/
  index.html               the game (single file)
sitemap.xml                every game URL
robots.txt                 points at the sitemap
tests/test_ui.py           Playwright: 4 languages, win, lose, hint, theme switch
tests/test_perechi.py      Playwright: 4 languages, board sizes, pairs, peek, win
tests/test_amesteca.py     Playwright: 4 languages, place/remove/clear, hint, keyboard, win
tests/test_zilei.py        Playwright: 4 languages, board, colours, hint cost, share, free play
tests/test_intrus.py       Playwright: 4 languages, rounds, themes, timer, score, share
tests/test_cautare.py      Playwright: 4 languages, full grid, right and wrong drags, new table, mobile, no page errors
```

## Development

Nothing to build. Open `ghiceste-cuvantul/index.html` in a browser, or serve the folder:

```
python -m http.server 8000
```

Tests (needs `pip install playwright` and `python -m playwright install chromium`):

```
python tests/test_ui.py
python tests/test_perechi.py
python tests/test_amesteca.py
python tests/test_zilei.py
python tests/test_intrus.py
python tests/test_cautare.py
```

## Deploy

Cloudflare Pages project connected to this repo, branch `main`, no build command, output directory `/`.
A push to `main` updates the site. GitHub Pages is enabled as a mirror.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
