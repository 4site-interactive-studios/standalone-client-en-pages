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
    p.subtitle { color: #666; margin-bottom: 1.5rem; }
    .filters { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.5rem; }
    .filters label { font-size: 0.8rem; font-weight: 600; color: #555; padding-top: 0.4rem; margin-right: 0.25rem; }
    .filter-group { display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center; }
    .filter-group + .filter-group { margin-left: 1.5rem; }
    .filter-btn { padding: 0.3rem 0.7rem; border-radius: 999px; border: 1px solid #ddd; background: #fff; font-size: 0.78rem; cursor: pointer; color: #555; transition: all 0.15s; }
    .filter-btn:hover { border-color: #aaa; }
    .filter-btn.active { background: #1a73e8; color: #fff; border-color: #1a73e8; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; }
    .card { background: #fff; border-radius: 8px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: box-shadow 0.2s; }
    .card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
    .card.hidden { display: none; }
    .card .org { display: flex; align-items: center; gap: 0.4rem; text-transform: uppercase; font-size: 0.75rem; font-weight: 600; color: #888; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
    .card .org img.favicon { width: 16px; height: 16px; border-radius: 2px; flex-shrink: 0; }
    .card .type-badge { display: inline-block; font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; padding: 0.15rem 0.5rem; border-radius: 999px; margin-left: 0.5rem; }
    .card .type-badge.donate { background: #e8f5e9; color: #2e7d32; }
    .card .type-badge.petition { background: #e3f2fd; color: #1565c0; }
    .card .type-badge.action { background: #fff3e0; color: #e65100; }
    .card .type-badge.data { background: #f3e5f5; color: #7b1fa2; }
    .card .type-badge.subscriptions { background: #fce4ec; color: #c62828; }
    .card .type-badge.survey { background: #e0f7fa; color: #00695c; }
    .card h2 { font-size: 1.1rem; margin-bottom: 0.75rem; line-height: 1.3; }
    .card h2 a { color: #1a73e8; text-decoration: none; }
    .card h2 a:hover { text-decoration: underline; }
    .card .meta { font-size: 0.8rem; color: #999; }
    .card .meta a { color: #999; }
    .card .meta a:hover { color: #1a73e8; }
    .no-results { display: none; grid-column: 1 / -1; text-align: center; padding: 3rem; color: #999; font-size: 1rem; }
    .no-results.visible { display: block; }
  </style>
</head>
<body>
  <h1>Standalone EN Pages</h1>
  <p class="subtitle">Local mirrors of Engaging Networks pages for development and testing.</p>
  <div class="filters">
    <div class="filter-group" id="org-filters">
      <label>Client:</label>
      <button class="filter-btn active" data-filter="org" data-value="all">All</button>
    </div>
    <div class="filter-group" id="type-filters">
      <label>Type:</label>
      <button class="filter-btn active" data-filter="type" data-value="all">All</button>
    </div>
  </div>
  <div class="grid">
HEADER

# Collect unique orgs and types for filter buttons
declare -a ORGS=()
declare -a TYPES=()

# Find all mirrored HTML pages and generate cards
find . \( -path './*/page/*/donate/*.html' -o -path './*/page/*/petition/*.html' -o -path './*/page/*/action/*.html' -o -path './*/page/*/data/*.html' -o -path './*/page/*/subscriptions/*.html' -o -path './*/page/*/survey/*.html' \) ! -name 'index.html' ! -path './.claude/*' ! -path './node_modules/*' | sort | while read -r filepath; do
  relpath="${filepath#./}"
  org=$(echo "$relpath" | cut -d/ -f1)
  title=$(grep -o '<title>[^<]*</title>' "$filepath" | head -1 | sed 's/<title>//;s/<\/title>//')
  pageid=$(echo "$relpath" | grep -o 'page/[0-9]*' | head -1 | cut -d/ -f2)
  origin=$(grep 'rel="canonical"' "$filepath" | grep -o 'href="https://[^/]*' | head -1 | sed 's/href="//')
  [ -z "$origin" ] && origin=$(grep 'og:url' "$filepath" | grep -o 'content="https://[^/]*' | head -1 | sed 's/content="//')
  pagetype=$(echo "$relpath" | sed "s|.*page/[0-9]*/||;s|/[^/]*$||")
  pagenum=$(basename "$relpath" .html)

  # Get favicon URL from origin domain
  favicon=""
  if [ -n "$origin" ]; then
    favicon="https://www.google.com/s2/favicons?domain=$(echo "$origin" | sed 's|https://||')&sz=32"
  fi

  if [ -n "$title" ]; then
    cat >> index.html << CARD
    <div class="card" data-org="${org}" data-type="${pagetype}">
      <div class="org"><img class="favicon" src="${favicon}" alt="" onerror="this.style.display='none'">${org}<span class="type-badge ${pagetype}">${pagetype}</span></div>
      <h2><a href="${relpath}">${title}</a></h2>
      <div class="meta">Page ${pageid} &middot; <a href="${origin}/page/${pageid}/${pagetype}/${pagenum}" target="_blank" rel="noopener">Live page ↗</a></div>
    </div>
CARD
  fi
done

cat >> index.html << 'FOOTER'
    <div class="no-results">No pages match the selected filters.</div>
  </div>
  <script>
  (function() {
    // Build filter buttons from card data attributes
    var cards = document.querySelectorAll('.card');
    var orgs = new Set(), types = new Set();
    cards.forEach(function(c) {
      orgs.add(c.dataset.org);
      types.add(c.dataset.type);
    });
    var orgGroup = document.getElementById('org-filters');
    Array.from(orgs).sort().forEach(function(o) {
      var btn = document.createElement('button');
      btn.className = 'filter-btn';
      btn.dataset.filter = 'org';
      btn.dataset.value = o;
      btn.textContent = o.toUpperCase();
      orgGroup.appendChild(btn);
    });
    var typeGroup = document.getElementById('type-filters');
    Array.from(types).sort().forEach(function(t) {
      var btn = document.createElement('button');
      btn.className = 'filter-btn';
      btn.dataset.filter = 'type';
      btn.dataset.value = t;
      btn.textContent = t;
      typeGroup.appendChild(btn);
    });

    // Filter state
    var activeOrg = 'all', activeType = 'all';

    function applyFilters() {
      var visible = 0;
      cards.forEach(function(c) {
        var matchOrg = activeOrg === 'all' || c.dataset.org === activeOrg;
        var matchType = activeType === 'all' || c.dataset.type === activeType;
        if (matchOrg && matchType) {
          c.classList.remove('hidden');
          visible++;
        } else {
          c.classList.add('hidden');
        }
      });
      var nr = document.querySelector('.no-results');
      if (visible === 0) nr.classList.add('visible');
      else nr.classList.remove('visible');
    }

    document.addEventListener('click', function(e) {
      var btn = e.target.closest('.filter-btn');
      if (!btn) return;
      var filter = btn.dataset.filter;
      var value = btn.dataset.value;
      // Update active state in that group
      var group = btn.parentElement;
      group.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      if (filter === 'org') activeOrg = value;
      if (filter === 'type') activeType = value;
      applyFilters();
    });
  })();
  </script>
</body>
</html>
FOOTER

echo "Generated index.html with $(grep -c 'class="card"' index.html) pages."
