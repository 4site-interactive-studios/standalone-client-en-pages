#!/bin/bash
# Usage: ./process-page.sh <org> <origin> <pageId> <pageType> <pageNumber> <raw-html-file> <pagedata-json>
# Example: ./process-page.sh aiusa https://donate.amnestyusa.org 137732 donate 1 /tmp/page.html '{"firstName":null,...}'
#
# Automates: create directory, copy HTML, fix paths, inject XHR intercept, save pagedata.

set -e
cd "$(dirname "$0")"

ORG="$1"
ORIGIN="$2"
PAGE_ID="$3"
PAGE_TYPE="$4"
PAGE_NUM="$5"
RAW_HTML="$6"
PAGEDATA="$7"

if [ -z "$PAGEDATA" ]; then
  echo "Usage: $0 <org> <origin> <pageId> <pageType> <pageNumber> <raw-html-file> <pagedata-json>"
  exit 1
fi

DEST_DIR="${ORG}/page/${PAGE_ID}/${PAGE_TYPE}"
DEST_FILE="${DEST_DIR}/${PAGE_NUM}.html"
DEPTH=$(echo "$DEST_DIR" | tr '/' '\n' | wc -l | tr -d ' ')
REL_PREFIX=$(printf '../%.0s' $(seq 1 $DEPTH))

mkdir -p "$DEST_DIR"
cp "$RAW_HTML" "$DEST_FILE"

# Save pagedata JSON for reference
echo "$PAGEDATA" > "${DEST_DIR}/${PAGE_NUM}.pagedata.json"

# Fix CSS path
sed -i '' "s|href='/pageassets/css/enPage.css|href='${ORIGIN}/pageassets/css/enPage.css|g" "$DEST_FILE"
sed -i '' "s|href=\"/pageassets/css/enPage.css|href=\"${ORIGIN}/pageassets/css/enPage.css|g" "$DEST_FILE"

# Fix pagedata.js and productvariants.js paths
sed -i '' "s|src='/page/|src='${ORIGIN}/page/|g" "$DEST_FILE"
sed -i '' "s|src=\"/page/|src=\"${ORIGIN}/page/|g" "$DEST_FILE"

# Fix form action paths
sed -i '' "s|action=\"/page/|action=\"${ORIGIN}/page/|g" "$DEST_FILE"
sed -i '' "s|action='/page/|action='${ORIGIN}/page/|g" "$DEST_FILE"

# Replace enPage.js with local copy + XHR intercept
# Handle both single and double quoted versions
XHR_BLOCK="<script>
window.__cachedPageData = ${PAGEDATA};
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
<script src='${REL_PREFIX}pageassets/js/enPage.js?v=4.0.0'></script>"

# Create a temp file with the XHR block
TMPFILE=$(mktemp)
echo "$XHR_BLOCK" > "$TMPFILE"

# Replace the enPage.js script tag with the intercept + local path
# Handle single-quoted version
python3 -c "
import re, sys
with open('$DEST_FILE', 'r') as f:
    html = f.read()
with open('$TMPFILE', 'r') as f:
    replacement = f.read()
# Replace single or double quoted enPage.js reference
html = re.sub(r\"<script src=['\\\"]/?pageassets/js/enPage\.js\?v=4\.0\.0['\\\"]></script>\", replacement, html)
with open('$DEST_FILE', 'w') as f:
    f.write(html)
"
rm "$TMPFILE"

echo "Processed: $DEST_FILE"
