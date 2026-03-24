# Standalone EN Page Mirrors

This repo contains standalone local mirrors of Engaging Networks (EN) donation/action pages.

## Directory Structure

```
{org}/page/{pageId}/donate/{pageNumber}.html      # Mirrored HTML page
{org}/page/{pageId}/donate/{pageNumber}.pagedata.json  # Cached pagedata response (reference)
pageassets/js/enPage.js                            # Local copy of EN's JS
```

- Org folders (e.g. `ran/`) keep pages organized by source organization.
- The path structure mirrors the original URL path (e.g. `act.ran.org/page/90802/donate/1`).

## How to Convert an EN Page to Standalone

### Step 1: Save the HTML source

Fetch the page HTML from the source URL. Cloudflare may block curl — if so, use the browser (view-source or Save As) or Chrome automation to get the HTML.

### Step 2: Fix asset paths

Convert all paths in the HTML to either relative or absolute origin URLs:

- **`/pageassets/css/enPage.css`** → keep as absolute to the origin: `https://{origin}/pageassets/css/enPage.css`
- **`/pageassets/js/enPage.js`** → point to local copy: `../../../../pageassets/js/enPage.js` (adjust depth based on file location)
- **`/page/{id}/donate/1?locale=en-US`** → absolute to origin: `https://{origin}/page/{id}/donate/1?locale=en-US`
- **Any other `/path` references** → absolute to origin: `https://{origin}/path`

**Key rule:** Paths that need to hit the live server (CSS, locale URLs, pagedata.js) should use the full origin URL (e.g. `https://act.ran.org/...`). Only enPage.js is served locally because we need to control its behavior.

### Step 3: Fetch and cache the pagedata response

The EN page JS makes XHR calls to `/page/{id}/donate/{pageNumber}/pagedata` to get form configuration. This will fail due to CORS when served from localhost.

1. Open the live page in a browser
2. Fetch the pagedata from the browser console:
   ```js
   const r = await fetch('/page/{pageId}/donate/{pageNumber}/pagedata');
   const d = await r.json();
   JSON.stringify(d);
   ```
3. Save the JSON response for reference as `{pageNumber}.pagedata.json`
4. Inline the response in the HTML (see Step 4)

### Step 4: Add the XHR intercept script

Insert this script block **before** the enPage.js `<script>` tag. It monkey-patches `XMLHttpRequest.prototype` to intercept all `/pagedata` requests and return cached data instead of making network calls.

```html
<script>
// Cache pagedata locally to avoid CORS issues when running as a static mirror
window.__cachedPageData = {"firstName":null,"lastName":null,...}; // <-- paste actual pagedata JSON here
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

### Why each patch is needed

- **`open()`** — detects `/pagedata` URLs and skips the native open (which would trigger a CORS-blocked request)
- **`setRequestHeader()`** — no-ops for intercepted requests because the XHR was never opened natively (calling setRequestHeader on an unopened XHR throws `InvalidStateError`)
- **`send()`** — returns the cached JSON response synchronously for GET (enPage.js uses `async: false`) and async for POST, setting all the properties that `reqwest` (the XHR library enPage.js uses) expects

## Running Locally

Pages must be served over HTTP, not opened as `file://` URLs (Chrome blocks cross-origin requests from `file://` origins).

```bash
# From repo root
npx serve . -l 8080
# Then open http://localhost:8080/ran/page/90802/donate/1.html
```

A launch config exists at `.claude/launch.json` for the preview server.

## Landing Page

After adding a new page, **always regenerate the landing page**:

```bash
./generate-index.sh
```

This scans for all `*/page/*/donate/*.html` files and generates `index.html` with cards linking to each mirrored page. The landing page is served at `http://localhost:8080/`.

## Fetching HTML from Cloudflare-Protected Sites

EN pages are behind Cloudflare, so curl won't work. Use browser automation:

1. Navigate to the page in Chrome
2. Fetch the HTML via JS: `fetch(location.href).then(r => r.text())`
3. Transfer it locally. Methods that work (in order of preference):
   - **data: URI download**: `a.href = 'data:application/octet-stream;base64,' + btoa(...)` with `a.download`
   - **Temp Node server + sendBeacon/form POST**: Start a local Node HTTP server and POST the HTML to it from the page
   - **navigator.sendBeacon** to localhost (may be blocked by CSP)
4. Some pages have strict CSP that blocks outbound requests to localhost. The data URI download approach usually works regardless of CSP.

## Gotchas & Lessons Learned

1. **Cloudflare blocks curl** — EN pages are behind Cloudflare. Use browser automation or view-source to fetch HTML/pagedata.
2. **Page redirects** — Some page IDs redirect (e.g. 90802 → 90804). The pagedata endpoint works with both IDs. Check the final URL after the page loads.
3. **Don't use a FakeXHR wrapper class** — Replacing `window.XMLHttpRequest` with a proxy class causes "Illegal invocation" errors because native XHR properties (onreadystatechange, withCredentials, etc.) require the correct native `this` context. Patching the prototype methods directly avoids this.
4. **responseType must be `''`** — If responseType is set to `'json'`, the reqwest library skips `JSON.parse()` and the response becomes `[object Object]` when code downstream tries to parse it as a string.
5. **Sync vs async** — The initial pagedata GET uses `async: false` (synchronous XHR). Callbacks must fire immediately (not via setTimeout) for sync requests, or the calling code won't see the response.
6. **`self.request = self`** — The reqwest library's sync codepath reads `returnValue.request.responseText`. It sets `request` to the XHR instance, so we point it back to `self` so it finds our patched `responseText`.
