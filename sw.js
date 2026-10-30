/* Free browser games · TekiDeki - offline shell
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 Kristian Mario Miskovic (TekiDeki)
 *
 * Regula casei: fiecare aplicatie se instaleaza pe telefon si se deschide si fara retea.
 * Toata logica sta aici, in fisierul asta - in pagina raman doar cateva linii de inregistrare.
 * Se creste VERSION cand se schimba vreun fisier din SHELL.
 *
 * Doua griji pe care le rezolva fisierul asta, invatate pe pielea lui:
 *  - gazda poate raspunde cu redirect (de ex. /vpn-vodic.html -> /vpn-vodic). Un raspuns venit
 *    prin redirect nu poate fi folosit de browser pentru o NAVIGARE, asa ca il rescriem curat
 *    inainte sa-l punem in cache;
 *  - o singura adresa lipsa nu are voie sa strice instalarea: fiecare intrare se descarca separat.
 */
var VERSION = 'games-v3';
var CACHE = VERSION;
var SHELL = [
  './',
  './index.html',
  './guess-the-word/',
  './odd-one-out/',
  './typing-test/',
  './word-from-definition/',
  './word-of-the-day/',
  './word-pairs/',
  './word-scramble/',
  './word-search/',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  './icon-maskable-512.png',
  './apple-touch-icon.png'
];

/* descarca o adresa si intoarce un raspuns curat (200, fara urma de redirect) */
function curat(url) {
  return fetch(new Request(url, { credentials: 'same-origin', redirect: 'follow' }))
    .then(function (response) {
      if (!response || !response.ok) return null;
      return response.blob().then(function (body) {
        return new Response(body, {
          status: 200,
          statusText: 'OK',
          headers: { 'Content-Type': response.headers.get('Content-Type') || 'text/html; charset=utf-8' }
        });
      }).then(function (raspuns) {
        return { raspuns: raspuns, final: response.url || url };
      });
    })
    .catch(function () { return null; });
}

self.addEventListener('install', function (event) {
  event.waitUntil(caches.open(CACHE).then(function (cache) {
    return Promise.all(SHELL.map(function (url) {
      var absolut = new URL(url, self.registration.scope).href;
      return curat(absolut).then(function (rezultat) {
        if (!rezultat) return;                      /* lipseste: instalarea merge inainte */
        return Promise.all([
          cache.put(absolut, rezultat.raspuns.clone()),
          cache.put(rezultat.final, rezultat.raspuns.clone())
        ]);
      });
    }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (event) {
  event.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) {
      return k.indexOf('games-') === 0 && k !== CACHE;
    }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

/* un raspuns venit prin redirect nu poate satisface o navigare: il rescriem */
function pentruNavigare(raspuns) {
  if (!raspuns || !raspuns.redirected) return Promise.resolve(raspuns);
  return raspuns.blob().then(function (body) {
    return new Response(body, {
      status: 200,
      statusText: 'OK',
      headers: { 'Content-Type': raspuns.headers.get('Content-Type') || 'text/html; charset=utf-8' }
    });
  });
}

self.addEventListener('fetch', function (event) {
  var request = event.request;
  if (request.method !== 'GET') return;
  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith(caches.open(CACHE).then(function (cache) {
    return cache.match(request, { ignoreSearch: true }).then(function (cached) {
      var network = fetch(request).then(function (response) {
        if (response && response.ok && response.type === 'basic' && !response.redirected) {
          cache.put(request, response.clone()).catch(function () {});
        }
        return response;
      });
      if (cached) {
        event.waitUntil(network.catch(function () {}));
        return pentruNavigare(cached);
      }
      return network.catch(function () {
        /* fara retea si fara copie: intoarce pagina principala, ca aplicatia sa porneasca totusi */
        return cache.match(new URL('./index.html', self.registration.scope).href, { ignoreSearch: true })
          .then(function (fallback) { return fallback || Response.error(); });
      });
    });
  }));
});
