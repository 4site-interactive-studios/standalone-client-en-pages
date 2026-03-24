#!/bin/bash
# Auto-generates index.html from all mirrored EN pages in the repo.
# Run from repo root: ./generate-index.sh

cd "$(dirname "$0")"

cat > index.html << 'HEADER'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Standalone EN Pages</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; color: #333; padding: 2rem; }
    h1 { margin-bottom: 0.5rem; font-size: 1.75rem; }
    p.subtitle { color: #666; margin-bottom: 2rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; }
    .card { background: #fff; border-radius: 8px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: box-shadow 0.2s; }
    .card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
    .card .org { text-transform: uppercase; font-size: 0.75rem; font-weight: 600; color: #888; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
    .card h2 { font-size: 1.1rem; margin-bottom: 0.75rem; line-height: 1.3; }
    .card h2 a { color: #1a73e8; text-decoration: none; }
    .card h2 a:hover { text-decoration: underline; }
    .card .meta { font-size: 0.8rem; color: #999; }
  </style>
</head>
<body>
  <h1>Standalone EN Pages</h1>
  <p class="subtitle">Local mirrors of Engaging Networks donation pages for development and testing.</p>
  <div class="grid">
HEADER

# Find all mirrored HTML pages and generate cards
find . \( -path './*/page/*/donate/*.html' -o -path './*/page/*/petition/*.html' -o -path './*/page/*/action/*.html' -o -path './*/page/*/data/*.html' -o -path './*/page/*/subscriptions/*.html' -o -path './*/page/*/survey/*.html' \) ! -name 'index.html' ! -path './.claude/*' ! -path './node_modules/*' | sort | while read -r filepath; do
  # Strip leading ./
  relpath="${filepath#./}"
  # Extract org name (first directory)
  org=$(echo "$relpath" | cut -d/ -f1)
  # Extract page title
  title=$(grep -o '<title>[^<]*</title>' "$filepath" | head -1 | sed 's/<title>//;s/<\/title>//')
  # Extract page ID from path
  pageid=$(echo "$relpath" | grep -o 'page/[0-9]*' | head -1 | cut -d/ -f2)
  # Extract origin from canonical link or og:url (most reliable source for the actual domain)
  origin=$(grep 'rel="canonical"' "$filepath" | grep -o 'href="https://[^/]*' | head -1 | sed 's/href="//')
  [ -z "$origin" ] && origin=$(grep 'og:url' "$filepath" | grep -o 'content="https://[^/]*' | head -1 | sed 's/content="//')

  # Extract page type and number from path
  pagetype=$(echo "$relpath" | sed "s|.*page/[0-9]*/||;s|/[^/]*$||")
  pagenum=$(basename "$relpath" .html)

  if [ -n "$title" ]; then
    cat >> index.html << CARD
    <div class="card">
      <div class="org">${org}</div>
      <h2><a href="${relpath}">${title}</a></h2>
      <div class="meta">Page ${pageid} &middot; ${pagetype} &middot; <a href="${origin}/page/${pageid}/${pagetype}/${pagenum}" target="_blank" rel="noopener">Live page</a></div>
    </div>
CARD
  fi
done

cat >> index.html << 'FOOTER'
  </div>
</body>
</html>
FOOTER

echo "Generated index.html with $(grep -c '<div class="card">' index.html) pages."
