# Games

Small browser games, one HTML file each. No account, no ads, no analytics script, no cookies, nothing loaded from another server.

**Live:** https://games.freehtml.dev (Cloudflare Pages, canonical)
**Mirror:** https://tekideki.github.io/Games/ (GitHub Pages, same files, canonical points here)

Shortcut: **https://freehtml.dev/games** (302)

## Games

| Game | Path | Languages | What it is |
|---|---|---|---|
| Guess the word | `/guess-the-word/` | EN, RO, SR Latin, SR Cyrillic | Hangman on themes. 192 words, 6 lives, one letter hint, local stats. |
| Word pairs | `/word-pairs/` | EN, RO, SR Latin, SR Cyrillic | Memory game. Same 192 words, board of 4, 6 or 8 pairs, moves and time, local stats. |
| Word scramble | `/word-scramble/` | EN, RO, SR Latin, SR Cyrillic | Anagrams. Same 192 words, tap letters into place, one letter hint, physical keyboard, local stats. |
| Word of the day | `/word-of-the-day/` | EN, RO, SR Latin, SR Cyrillic | Deduction. One word per day, same for everyone, six tries, green/yellow/grey per letter, shareable emoji grid, free play mode. |
| Odd one out | `/odd-one-out/` | EN, RO, SR Latin, SR Cyrillic | Categories. Four words, three from one theme, pick the intruder. Ten rounds, twelve seconds each, streak bonus. |
| Word search | `/word-search/` | EN, RO, SR Latin, SR Cyrillic | Hidden words. Same 192 words, 12 by 12 grid, eight words per table, all eight directions, drag from the first letter to the last, local stats. |
| Word from definition | `/word-from-definition/` | EN, RO, SR Latin, SR Cyrillic | Vocabulary. One definition from Wikipedia or Wiktionary, four words to choose from, three themes, local score. Text of the definitions is CC BY-SA 4.0. |
| Type fast | `/typing-test/` | EN, RO, SR Latin, SR Cyrillic | Typing test. Words come one after another; a wrong letter never goes through. Words per minute and accuracy, best kept locally. |

## House rules

- Single file per game: HTML, CSS, JS and SVG all inline. No build step, no dependencies, no CDN.
- Four language versions everywhere: `en`, `ro`, `sr-Latn`, `sr-Cyrl`. Not Russian - Serbian Cyrillic, 30 letters, no Ё Ъ Ы Э Ю Я Щ.
- **English is the primary language, in the URL too:** every game lives at an English path (`/word-search/`, not `/cautare-de-cuvinte/`); the old Romanian paths 301 to the English ones (see `_redirects`).
- **English is the default in the page:** Every link opens in English (`<html lang="en">`, English title, meta, OG and JSON-LD, EN button first); the other three are one click away. A returning visitor keeps the language they picked.
- `<html lang>`, `<title>`, `<meta description>` and the JSON-LD all change with the language.
- Light and dark, follows the system setting, manual toggle.
- Support line in the footer: `https://PayPal.me/TekiDeki`. No Ko-fi, no Patreon.
- Words are always checked against the alphabet of their own language - a word that cannot be typed is a bug.

## Structure

```
index.html                 hub, lists the games
guess-the-word/
  index.html               the game (single file)
word-pairs/
  index.html               the game (single file)
word-scramble/
  index.html               the game (single file)
word-of-the-day/
  index.html               the game (single file)
odd-one-out/
  index.html               the game (single file)
word-search/
  index.html               the game (single file)
typing-test/
  index.html               the game (single file)
tools/genereaza-corp.py    writes the word block into every game, from tests/corpus.json
tests/corpus.json          the one source of truth for words: 48 per language, 16 per theme
sitemap.xml                every game URL
robots.txt                 points at the sitemap
_headers                   security headers (CSP with connect-src 'none', HSTS, nosniff, frame DENY)
tests/test_ui.py           Playwright: 4 languages, win, lose, hint, theme switch
tests/test_perechi.py      Playwright: 4 languages, board sizes, pairs, peek, win
tests/test_amesteca.py     Playwright: 4 languages, place/remove/clear, hint, keyboard, win
tests/test_zilei.py        Playwright: 4 languages, board, colours, hint cost, share, free play
tests/test_intrus.py       Playwright: 4 languages, rounds, themes, timer, score, share
tests/test_cautare.py      Playwright: 4 languages, full grid, right and wrong drags, new table, mobile, no page errors
tests/test_tastatura.py    Playwright: keyboard-only play, arrow navigation, Shift selection, Enter, Escape, tap targets 24x24
tests/test_corp.py         one source of truth for the words: 48 per language, 16 per theme, Serbian Latin <-> Cyrillic
tests/test_tastare.py      Playwright: the typing game played for real, WPM maths, diacritics, timer, mobile
tests/test_subsol.py        Playwright: every page has the support link and the report link, in all four languages
tests/test_antete.py       Playwright: every page served with the headers from _headers, zero CSP violations, zero external requests. The page list is discovered with rglob, so a new game is covered the day it is added
```

## Development

Nothing to build. Open `guess-the-word/index.html` in a browser, or serve the folder:

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
python tests/test_tastatura.py
python tests/test_antete.py
```

## Deploy

Cloudflare Pages project connected to this repo, branch `main`, no build command, output directory `/`.
A push to `main` updates the site. GitHub Pages is enabled as a mirror.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
