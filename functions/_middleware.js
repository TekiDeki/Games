// Pages Function: Cloudflare Pages strips the .html extension from HTML files and
// answers 307 to the version with it. Search Console verification asks for the exact
// file name, and a redirect is not accepted, so this middleware answers that one
// path directly, before the static asset handling kicks in.
const TOKENS = ['googlee27c9c9c38210b47'];

export async function onRequest(context) {
  const { pathname } = new URL(context.request.url);
  const file = pathname.replace(/^\//, '');
  const token = TOKENS.find(t => file === `${t}.html`);
  if (token) {
    return new Response(`google-site-verification: ${token}.html\n`, {
      status: 200,
      headers: {
        'content-type': 'text/html; charset=utf-8',
        'cache-control': 'public, max-age=300',
      },
    });
  }
  return context.next();
}
