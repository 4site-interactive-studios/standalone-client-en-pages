# Standalone EN Page Mirrors

This repo contains standalone local mirrors of Engaging Networks (EN) pages running ENgrid.

## Directory Structure

```
{org}/page/{pageId}/{pageType}/{pageNumber}.html           # Mirrored HTML page
{org}/page/{pageId}/{pageType}/{pageNumber}.pagedata.json  # Cached pagedata response
{org}/page/{pageId}/{pageType}/{pageNumber}.viewport.jpg   # Viewport screenshot (1280x800)
{org}/page/{pageId}/{pageType}/{pageNumber}.full.jpg        # Full-page screenshot
pageassets/js/enPage.js                                     # Local copy of EN's JS
org-config.json                                             # Org display names and external links
generate-index.py                                           # Python script that builds index.html
generate-index.sh                                           # Shell wrapper that calls generate-index.py
process-page.sh                                             # Automates path fixing and XHR injection
```

- Org folders (e.g. `ran/`, `tnc/`, `wwf/`) keep pages organized by source organization.
- Page types include: `donate`, `petition`, `action`, `data`, `subscriptions`, `survey`.
- The path structure mirrors the original URL path (e.g. `act.ran.org/page/90802/donate/1`).

## How to Add a New EN Page

### Quick path (automated)

1. Fetch the HTML and pagedata (see "Fetching" section below)
2. Run the processing script:
   ```bash
   ./process-page.sh {org} {origin} {pageId} {pageType} {pageNumber} {raw-html-file} '{pagedata-json}'
   # Example:
   ./process-page.sh ran https://act.ran.org 90802 donate 1 /tmp/90802.html '{"firstName":null,...}'
   ```
3. If it's a new org, add it to `org-config.json`
4. Take screenshots (see "Screenshots" section below)
5. Regenerate the landing page: `./generate-index.sh`

### What process-page.sh does

- Creates the directory structure `{org}/page/{pageId}/{pageType}/`
- Copies the HTML and saves the pagedata JSON
- Fixes CSS path to use full origin URL
- Fixes pagedata.js and form action paths to use full origin URL
- Replaces the enPage.js script tag with the XHR intercept + local path

### Manual path (understanding each step)

#### Step 1: Save the HTML source

Fetch the page HTML from the source URL. Cloudflare may block curl — use Playwright or Chrome automation.

#### Step 2: Fix asset paths

Convert all paths in the HTML to either relative or absolute origin URLs:

- **`/pageassets/css/enPage.css`** → keep as absolute to the origin: `https://{origin}/pageassets/css/enPage.css`
- **`/pageassets/js/enPage.js`** → point to local copy: `../../../../pageassets/js/enPage.js` (adjust depth based on file location)
- **`/page/{id}/...`** (pagedata.js, form actions) → absolute to origin: `https://{origin}/page/{id}/...`

**Key rule:** Paths that need to hit the live server (CSS, locale URLs, pagedata.js) use the full origin URL. Only enPage.js is served locally because we need to control its behavior.

#### Step 3: Fetch and cache the pagedata response

The EN page JS makes XHR calls to `/page/{id}/{pageType}/{pageNumber}/pagedata`. This fails due to CORS when served from localhost.

1. Open the live page in a browser
2. Fetch the pagedata from the browser console:
   ```js
   const r = await fetch('/page/{pageId}/{pageType}/{pageNumber}/pagedata');
   const d = await r.json();
   JSON.stringify(d);
   ```
3. Save the JSON as `{pageNumber}.pagedata.json`
4. Inline the response in the HTML (see Step 4)

#### Step 4: Add the XHR intercept script

Insert this script block **before** the enPage.js `<script>` tag:

```html
<script>
window.__cachedPageData = {"firstName":null,...}; // <-- paste actual pagedata JSON here
(function() {
  var _open = XMLHttpRequest.prototype.open;
  var _send = XMLHttpRequest.prototype.send;
  var _setRequestHeader = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open = function(method, url) {
    this.__pagedata = (typeof url === 'string' && url.indexOf('/pagedata') !== -1);
    this.__method = method;
    if (!this.__pagedata) return _open.apply(this, arguments);
  };
  XMLHttpRequest.prototype.setRequestHeader = function() {
    if (!this.__pagedata) return _setRequestHeader.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function(data) {
    if (!this.__pagedata) return _send.apply(this, arguments);
    var self = this;
    var jsonStr = JSON.stringify(window.__cachedPageData);
    Object.defineProperties(self, {
      readyState:   { value: 4, writable: true, configurable: true },
      status:       { value: 200, writable: true, configurable: true },
      statusText:   { value: 'OK', writable: true, configurable: true },
      responseText: { value: jsonStr, writable: true, configurable: true },
      response:     { value: jsonStr, writable: true, configurable: true },
      responseType: { value: '', writable: true, configurable: true }
    });
    self.request = self;
    if (self.__method === 'GET') {
      if (typeof self.onreadystatechange === 'function') self.onreadystatechange();
      if (typeof self.onload === 'function') self.onload();
    } else {
      setTimeout(function() {
        if (typeof self.onreadystatechange === 'function') self.onreadystatechange();
        if (typeof self.onload === 'function') self.onload();
      }, 0);
    }
  };
})();
</script>
<script src="../../../../pageassets/js/enPage.js?v=4.0.0"></script>
```

### Why each XHR patch is needed

- **`open()`** — detects `/pagedata` URLs and skips the native open (which would trigger a CORS-blocked request)
- **`setRequestHeader()`** — no-ops for intercepted requests because the XHR was never opened natively (calling setRequestHeader on an unopened XHR throws `InvalidStateError`)
- **`send()`** — returns the cached JSON response synchronously for GET (enPage.js uses `async: false`) and async for POST, setting all the properties that `reqwest` (the XHR library enPage.js uses) expects

## Fetching HTML from Cloudflare-Protected Sites

EN pages are behind Cloudflare, so curl won't work. Use **Playwright** (preferred for batch operations):

```js
const { chromium } = require('playwright');
const browser = await chromium.launch({ headless: false, args: ['--disable-blink-features=AutomationControlled'] });
const context = await browser.newContext({ userAgent: '...' });
const page = await context.newPage();
await page.goto(url, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(10000); // Wait for Cloudflare challenge
const result = await page.evaluate(async () => {
  const html = await (await fetch(location.href)).text();
  const pd = await (await fetch(`/page/${pageId}/${pageType}/${pageNum}/pagedata`)).json();
  return { html, pagedata: JSON.stringify(pd) };
});
```

**Tips:**
- Use `headless: false` — Cloudflare blocks headless browsers more aggressively
- Wait 10-15s for Cloudflare challenge to resolve
- Some pages have very aggressive Cloudflare that blocks even visible Playwright browsers
- Check `page.title()` — if it contains "moment" or is empty, Cloudflare is still blocking
- Pages may redirect to different page IDs (e.g. 90802 → 90804). Always check the final URL.

### Verifying a page uses ENgrid

Before mirroring, confirm the page uses ENgrid by checking for `engrid.min.js`:

```js
const hasEngrid = await page.evaluate(() => {
  return Array.from(document.querySelectorAll('script[src]')).some(s => s.src.includes('engrid.min.js'));
});
```

## Screenshots

After adding pages, capture screenshots for the Screenshots view:

```js
// Use Playwright with file:// URLs (no Cloudflare needed for local files)
const page = await context.newPage();
await page.goto('file:///path/to/page.html', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2000);
await page.screenshot({ path: '1.viewport.jpg', type: 'jpeg', quality: 75 });
await page.screenshot({ path: '1.full.jpg', fullPage: true, type: 'jpeg', quality: 65 });
```

Screenshots are taken from local files (no server needed). Viewport is 1280x800.

## Running Locally

Pages must be served over HTTP, not opened as `file://` URLs (Chrome blocks cross-origin requests from `file://` origins).

```bash
npx serve . -l 8080
# Then open http://localhost:8080/
```

A launch config exists at `.claude/launch.json` for the preview server.

## Landing Page

The landing page (`index.html`) has three views:

- **List** — grouped by org with bullet sub-items (like a markdown reference doc)
- **Grid** — card grid with title, page type badge, and live page link
- **Screenshots** — masonry layout of page screenshots with viewport/full-page toggle

Filters: Client, Type (donate/petition/action/data/subscriptions/survey), Layout (One Column/Side-by-Side/Multistep), Status (Live/Test/Demo). Filters update the URL for shareability and cross-disable unavailable options.

**Always regenerate after changes:**

```bash
./generate-index.sh
```

This runs `generate-index.py` which scans all `*/page/*/*.html` files, extracts metadata from each page's HTML (pageJson, data-engrid-layout, multistep-stepper, dd360search), and generates the index with all three views.

## Configuration Files

### org-config.json

Maps org folder names to display names and optional external links:

```json
{
  "ran": {
    "name": "Rainforest Action Network (RAN)"
  },
  "wwf": {
    "name": "World Wildlife Fund (WWF)",
    "externalLinks": [
      { "label": "Multistep Donation Lightbox Demo", "url": "https://apps.4sitestudios.com/fernando/wwf/" }
    ]
  }
}
```

### Page metadata auto-detection

`generate-index.py` extracts these from each page's HTML:
- **Page type** — from `pageJson.pageType` (donation, advocacypetition, emailtotarget, etc.)
- **Layout** — from `data-engrid-layout` attribute (leftleft1col = one column, leftleft2col = side-by-side)
- **Multistep** — presence of `.multistep-stepper` class
- **Double the Donation** — presence of `.en__component--dd360search` class
- **Test/Demo** — title contains "test", "reference", or "demo" (case-insensitive)

## Gotchas & Lessons Learned

1. **Cloudflare blocks curl** — EN pages are behind Cloudflare. Use Playwright with `headless: false` for best results.
2. **Page redirects** — Some page IDs redirect (e.g. 65368 → 58307). The pagedata endpoint works with both IDs. Check the final URL after the page loads.
3. **Don't use a FakeXHR wrapper class** — Replacing `window.XMLHttpRequest` with a proxy class causes "Illegal invocation" errors because native XHR properties require the correct native `this` context. Patching the prototype methods directly avoids this.
4. **responseType must be `''`** — If responseType is set to `'json'`, the reqwest library skips `JSON.parse()` and the response becomes `[object Object]` when code downstream tries to parse it as a string.
5. **Sync vs async** — The initial pagedata GET uses `async: false` (synchronous XHR). Callbacks must fire immediately (not via setTimeout) for sync requests.
6. **`self.request = self`** — The reqwest library's sync codepath reads `returnValue.request.responseText`. It sets `request` to the XHR instance, so we point it back to `self` so it finds our patched `responseText`.
7. **Some pages can't be fetched** — A few pages have Cloudflare protection that blocks even visible Playwright browsers. These may need to be fetched manually via view-source in a regular browser session.
8. **Not all /page/ URLs use ENgrid** — Always verify `engrid.min.js` is present before mirroring. Some EN pages use custom templates without ENgrid.
