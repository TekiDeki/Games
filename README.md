# Games

Small browser games, one HTML file each. No account, no ads, no tracking, nothing sent to a server.

**Live:** https://games.freehtml.dev (Cloudflare Pages, canonical)
**Mirror:** https://tekideki.github.io/Games/ (GitHub Pages, same files, canonical points here)

Shortcut: **https://freehtml.dev/games** (302)

## Games

| Game | Path | Languages | What it is |
|---|---|---|---|
| Guess the word | `/ghiceste-cuvantul/` | EN, RO, SR Latin, SR Cyrillic | Hangman on themes. 96 words, 6 lives, one letter hint, local stats. |

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
sitemap.xml                both URLs
robots.txt                 points at the sitemap
tests/test_ui.py           Playwright: 4 languages, win, lose, hint, theme switch
```

## Development

Nothing to build. Open `ghiceste-cuvantul/index.html` in a browser, or serve the folder:

```
python -m http.server 8000
```

Tests (needs `pip install playwright` and `python -m playwright install chromium`):

```
python tests/test_ui.py
```

## Deploy

Cloudflare Pages project connected to this repo, branch `main`, no build command, output directory `/`.
A push to `main` updates the site. GitHub Pages is enabled as a mirror.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
