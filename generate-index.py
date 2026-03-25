#!/usr/bin/env python3
"""Generates index.html from all mirrored EN pages in the repo."""

import glob
import json
import os
import re
from collections import defaultdict

# Load org config
with open("org-config.json") as f:
    ORG_CONFIG = json.load(f)

# Page type label mapping from EN's pageJson.pageType
PAGE_TYPE_LABELS = {
    "donation": "Donation",
    "premiumgift": "Donation",
    "advocacypetition": "Action",
    "emailtotarget": "Action",
    "otherdatacapture": "Data Capture",
    "survey": "Survey",
    "subscription": "Subscription Management",
}

def get_link_label(title, pagetype, layout, is_multistep):
    """Generate a short descriptive link label like the markdown examples."""
    pt = PAGE_TYPE_LABELS.get(pagetype, pagetype.title() if pagetype else "Page")

    parts = []

    # Layout prefix
    if layout:
        if "2col" in layout:
            parts.append("Side-By-Side")
        # 1col is default, don't mention

    # Multistep
    if is_multistep:
        parts.append("Multistep")

    parts.append(pt)

    label = " ".join(parts)

    # Check for special types from title
    title_lower = (title or "").lower()
    if "symbolic" in title_lower or "premium" in title_lower:
        if "premiumgift" == pagetype:
            label = label  # keep as-is, it's already "Donation"
    if "gated" in title_lower:
        label = "Gated Content"
    if "subscription" in title_lower or "subscriptions" in pagetype:
        label = "Subscription Management"
    if "survey" in pagetype:
        label = "Survey"

    return label


def extract_page_info(filepath):
    """Extract metadata from a mirrored HTML file."""
    with open(filepath, "r", errors="replace") as f:
        html = f.read()

    info = {}

    # Title
    m = re.search(r"<title>([^<]*)</title>", html)
    info["title"] = m.group(1) if m else ""

    # pageJson
    m = re.search(r'var pageJson\s*=\s*(\{[^}]+\})', html)
    if m:
        try:
            pj = json.loads(m.group(1))
            info["pagetype_raw"] = pj.get("pageType", "")
            info["pageid"] = pj.get("campaignPageId", "")
        except json.JSONDecodeError:
            info["pagetype_raw"] = ""
            info["pageid"] = ""
    else:
        info["pagetype_raw"] = ""
        info["pageid"] = ""

    # Layout
    m = re.search(r'data-engrid-layout="([^"]*)"', html)
    info["layout"] = m.group(1) if m else ""

    # Multistep
    info["is_multistep"] = bool(re.search(r'multistep-stepper', html))

    # Origin
    m = re.search(r'rel="canonical"[^>]*href="(https://[^/"]*)', html)
    if not m:
        m = re.search(r'og:url[^>]*content="(https://[^/"]*)', html)
    info["origin"] = m.group(1) if m else ""

    # Favicon domain (parent domain)
    if info["origin"]:
        domain = info["origin"].replace("https://", "")
        parts = domain.split(".")
        if len(parts) > 2:
            domain = ".".join(parts[1:])
        info["favicon"] = f"https://www.google.com/s2/favicons?domain={domain}&sz=32"
    else:
        info["favicon"] = ""

    # Is test/demo/reference
    info["is_test"] = bool(re.search(r"(?i)test|reference|demo", info["title"]))

    return info


def find_all_pages():
    """Find all mirrored pages and return structured data."""
    patterns = [
        "./*/page/*/donate/*.html",
        "./*/page/*/petition/*.html",
        "./*/page/*/action/*.html",
        "./*/page/*/data/*.html",
        "./*/page/*/subscriptions/*.html",
        "./*/page/*/survey/*.html",
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))

    pages = []
    for f in sorted(set(files)):
        if ".claude" in f or "node_modules" in f:
            continue
        relpath = f.lstrip("./")
        parts = relpath.split("/")
        org = parts[0]
        pageid = parts[2]
        url_pagetype = parts[3]
        pagenum = parts[4].replace(".html", "")

        info = extract_page_info(f)
        info["relpath"] = relpath
        info["org"] = org
        info["url_pagetype"] = url_pagetype
        info["pagenum"] = pagenum
        if not info["pageid"]:
            info["pageid"] = pageid

        info["link_label"] = get_link_label(
            info["title"], info["pagetype_raw"], info["layout"], info["is_multistep"]
        )

        pages.append(info)

    return pages


def generate_card_html(page):
    """Generate a card div for the grid view."""
    is_test = "true" if page["is_test"] else "false"
    demo_badge = '<span class="demo-badge">Test</span>' if page["is_test"] else ""
    favicon = f'<img class="favicon" src="{page["favicon"]}" alt="" onerror="this.style.display=\'none\'">' if page["favicon"] else ""

    return f"""    <div class="card" data-org="{page['org']}" data-type="{page['url_pagetype']}" data-status="{is_test}">
      <div class="org">{favicon}{page['org']}<span class="type-badge {page['url_pagetype']}">{page['url_pagetype']}</span>{demo_badge}</div>
      <h2><a href="{page['relpath']}">{page['title']}</a></h2>
      <div class="meta">Page {page['pageid']} &middot; <a href="{page['origin']}/page/{page['pageid']}/{page['url_pagetype']}/{page['pagenum']}" target="_blank" rel="noopener">Live page &#8599;</a></div>
    </div>"""


def generate_list_html(pages):
    """Generate the markdown-style list view grouped by org with bullet sub-items."""
    grouped = defaultdict(list)
    for p in pages:
        grouped[p["org"]].append(p)

    # Sort orgs by config order (or alphabetically)
    org_order = list(ORG_CONFIG.keys())
    sorted_orgs = sorted(grouped.keys(), key=lambda o: org_order.index(o) if o in org_order else 999)

    lines = []
    for org in sorted_orgs:
        config = ORG_CONFIG.get(org, {})
        org_name = config.get("name", org.upper())
        favicon = ""
        if grouped[org]:
            fav_url = grouped[org][0].get("favicon", "")
            if fav_url:
                favicon = f'<img class="list-favicon" src="{fav_url}" alt="" onerror="this.style.display=\'none\'">'

        # Build bullet items for this org, sorted alphabetically by label
        page_bullets = []
        for p in sorted(grouped[org], key=lambda x: x["link_label"].lower()):
            label = p["link_label"]
            badge = ' <span class="demo-badge">Test</span>' if p["is_test"] else ""
            status = "true" if p["is_test"] else "false"
            page_bullets.append(f'        <li data-type="{p["url_pagetype"]}" data-status="{status}"><a href="{p["relpath"]}">{label}</a>{badge}</li>')

        # Add external links from config (no data attrs — always visible)
        ext_bullets = []
        for ext in config.get("externalLinks", []):
            label = ext["label"]
            note = f' <span class="list-note">— {ext["note"]}</span>' if ext.get("note") else ""
            ext_bullets.append(f'        <li class="list-external"><a href="{ext["url"]}" target="_blank" rel="noopener">{label} &#8599;</a>{note}</li>')

        bullets = page_bullets + ext_bullets

        bullet_html = "\n".join(bullets)
        lines.append(f"""    <li class="list-org" data-org="{org}">
      <div class="list-org-header">{favicon}<strong>{org_name}</strong></div>
      <ul class="list-pages">
{bullet_html}
      </ul>
    </li>""")

    return "\n".join(lines)


def main():
    pages = find_all_pages()
    cards_html = "\n".join(generate_card_html(p) for p in pages)
    list_html = generate_list_html(pages)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ENgrid Pages</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; color: #333; padding: 2rem; }}
    h1 {{ margin-bottom: 0.5rem; font-size: 1.75rem; }}
    p.subtitle {{ color: #666; margin-bottom: 1.5rem; }}

    /* View toggle */
    .view-toggle {{ display: flex; gap: 0.25rem; margin-bottom: 1.5rem; background: #e0e0e0; border-radius: 6px; padding: 3px; width: fit-content; }}
    .view-btn {{ padding: 0.4rem 1rem; border-radius: 4px; border: none; background: transparent; font-size: 0.82rem; cursor: pointer; color: #555; font-weight: 500; transition: all 0.15s; }}
    .view-btn.active {{ background: #fff; color: #333; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }}

    /* Filters */
    .filters {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.5rem; }}
    .filters label {{ font-size: 0.8rem; font-weight: 600; color: #555; padding-top: 0.4rem; margin-right: 0.25rem; }}
    .filter-group {{ display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center; }}
    .filter-group + .filter-group {{ margin-left: 1.5rem; }}
    .filter-btn {{ padding: 0.3rem 0.7rem; border-radius: 999px; border: 1px solid #ddd; background: #fff; font-size: 0.78rem; cursor: pointer; color: #555; transition: all 0.15s; }}
    .filter-btn:hover {{ border-color: #aaa; }}
    .filter-btn.active {{ background: #1a73e8; color: #fff; border-color: #1a73e8; }}

    /* Grid view */
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; }}
    .card {{ background: #fff; border-radius: 8px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: box-shadow 0.2s; }}
    .card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
    .card.hidden {{ display: none; }}
    .card .org {{ display: flex; align-items: center; gap: 0.4rem; text-transform: uppercase; font-size: 0.75rem; font-weight: 600; color: #888; letter-spacing: 0.05em; margin-bottom: 0.5rem; }}
    .card .org img.favicon {{ width: 16px; height: 16px; border-radius: 2px; flex-shrink: 0; }}
    .card .type-badge {{ display: inline-block; font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; padding: 0.15rem 0.5rem; border-radius: 999px; margin-left: 0.5rem; }}
    .card .type-badge.donate {{ background: #e8f5e9; color: #2e7d32; }}
    .card .type-badge.petition {{ background: #e3f2fd; color: #1565c0; }}
    .card .type-badge.action {{ background: #fff3e0; color: #e65100; }}
    .card .type-badge.data {{ background: #f3e5f5; color: #7b1fa2; }}
    .card .type-badge.subscriptions {{ background: #fce4ec; color: #c62828; }}
    .card .type-badge.survey {{ background: #e0f7fa; color: #00695c; }}
    .demo-badge {{ display: inline-block; font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; padding: 0.15rem 0.45rem; border-radius: 999px; margin-left: 0.35rem; background: #fff8e1; color: #f57f17; border: 1px solid #ffe082; }}
    .card h2 {{ font-size: 1.1rem; margin-bottom: 0.75rem; line-height: 1.3; }}
    .card h2 a {{ color: #1a73e8; text-decoration: none; }}
    .card h2 a:hover {{ text-decoration: underline; }}
    .card .meta {{ font-size: 0.8rem; color: #999; }}
    .card .meta a {{ color: #999; }}
    .card .meta a:hover {{ color: #1a73e8; }}
    .no-results {{ display: none; grid-column: 1 / -1; text-align: center; padding: 3rem; color: #999; font-size: 1rem; }}
    .no-results.visible {{ display: block; }}

    /* List view */
    .list-view {{ display: none; }}
    .list-view.active {{ display: block; }}
    .list-view > ul {{ list-style: none; padding: 0; }}
    .list-view li.list-org {{ background: #fff; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 0.6rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
    .list-view li.list-org.hidden {{ display: none; }}
    .list-view .list-org-header {{ display: flex; align-items: center; font-size: 0.95rem; margin-bottom: 0.5rem; }}
    .list-view img.list-favicon {{ width: 16px; height: 16px; border-radius: 2px; margin-right: 0.5rem; flex-shrink: 0; }}
    .list-view ul.list-pages {{ list-style: disc; padding-left: 1.5rem; margin: 0; }}
    .list-view ul.list-pages li {{ padding: 0.15rem 0; font-size: 0.9rem; line-height: 1.5; }}
    .list-view li a {{ color: #1a73e8; text-decoration: none; }}
    .list-view li a:hover {{ text-decoration: underline; }}
    .list-view .list-note {{ font-size: 0.82rem; color: #888; font-style: italic; }}
    .list-view .demo-badge {{ font-size: 0.55rem; vertical-align: middle; }}

    /* Filter notice banner */
    .filter-notice {{ display: flex; align-items: center; gap: 0.75rem; background: #e3f2fd; border: 1px solid #90caf9; border-radius: 8px; padding: 0.65rem 1rem; margin-bottom: 1.25rem; font-size: 0.85rem; color: #1565c0; }}
    .filter-notice .notice-btn {{ padding: 0.25rem 0.75rem; border-radius: 4px; border: 1px solid #1a73e8; background: #1a73e8; color: #fff; font-size: 0.78rem; cursor: pointer; white-space: nowrap; }}
    .filter-notice .notice-btn:hover {{ background: #1557b0; }}
    .filter-notice .notice-close {{ background: none; border: none; font-size: 1.2rem; cursor: pointer; color: #1565c0; padding: 0 0.25rem; margin-left: auto; line-height: 1; }}
    .filter-notice .notice-close:hover {{ color: #0d47a1; }}

    /* Toggle visibility */
    .grid-view {{ display: grid; }}
    .grid-view.hidden-view {{ display: none; }}
  </style>
</head>
<body>
  <h1>ENgrid Pages</h1>
  <p class="subtitle">Local mirrors of Engaging Networks ENgrid pages for development, testing, and sharing.</p>

  <div class="view-toggle">
    <button class="view-btn active" data-view="list">List</button>
    <button class="view-btn" data-view="grid">Grid</button>
  </div>

  <div class="filters">
    <div class="filter-group" id="org-filters">
      <label>Client:</label>
      <button class="filter-btn active" data-filter="org" data-value="all">All</button>
    </div>
    <div class="filter-group" id="type-filters">
      <label>Type:</label>
      <button class="filter-btn active" data-filter="type" data-value="all">All</button>
    </div>
    <div class="filter-group" id="status-filters">
      <label>Status:</label>
      <button class="filter-btn active" data-filter="status" data-value="all">All</button>
      <button class="filter-btn" data-filter="status" data-value="live">Live</button>
      <button class="filter-btn" data-filter="status" data-value="test">Test / Demo</button>
    </div>
  </div>

  <div class="list-view active">
    <ul>
{list_html}
    </ul>
  </div>

  <div class="grid grid-view hidden-view">
{cards_html}
    <div class="no-results">No pages match the selected filters.</div>
  </div>

  <div class="filter-notice" id="filter-notice" style="display:none">
    <span id="filter-notice-text"></span>
    <button class="notice-btn" id="notice-reset">Show All</button>
    <button class="notice-close" id="notice-close">&times;</button>
  </div>

  <script>
  (function() {{
    var listView = document.querySelector('.list-view');
    var gridView = document.querySelector('.grid-view');
    var cards = document.querySelectorAll('.card');
    var listOrgs = document.querySelectorAll('.list-org');
    var totalPages = cards.length;
    var notice = document.getElementById('filter-notice');
    var noticeText = document.getElementById('filter-notice-text');
    var activeView = 'list';
    var activeOrg = 'all', activeType = 'all', activeStatus = 'all';
    var fromUrl = false;

    // --- URL state ---
    function readUrl() {{
      var p = new URLSearchParams(location.search);
      activeView = p.get('view') || 'list';
      activeOrg = p.get('org') || 'all';
      activeType = p.get('type') || 'all';
      activeStatus = p.get('status') || 'all';
      fromUrl = p.has('org') || p.has('type') || p.has('status');
    }}

    function writeUrl() {{
      var p = new URLSearchParams();
      if (activeView !== 'list') p.set('view', activeView);
      if (activeOrg !== 'all') p.set('org', activeOrg);
      if (activeType !== 'all') p.set('type', activeType);
      if (activeStatus !== 'all') p.set('status', activeStatus);
      var qs = p.toString();
      var url = location.pathname + (qs ? '?' + qs : '');
      history.replaceState(null, '', url);
    }}

    // --- View toggle ---
    function setView(view) {{
      activeView = view;
      document.querySelectorAll('.view-btn').forEach(function(b) {{
        b.classList.toggle('active', b.dataset.view === view);
      }});
      if (view === 'list') {{
        listView.classList.add('active');
        gridView.classList.add('hidden-view');
      }} else {{
        listView.classList.remove('active');
        gridView.classList.remove('hidden-view');
      }}
    }}

    document.querySelector('.view-toggle').addEventListener('click', function(e) {{
      var btn = e.target.closest('.view-btn');
      if (!btn) return;
      setView(btn.dataset.view);
      writeUrl();
    }});

    // --- Build filter buttons ---
    var orgs = new Set(), types = new Set();
    cards.forEach(function(c) {{ orgs.add(c.dataset.org); types.add(c.dataset.type); }});
    var orgGroup = document.getElementById('org-filters');
    Array.from(orgs).sort().forEach(function(o) {{
      var btn = document.createElement('button');
      btn.className = 'filter-btn';
      btn.dataset.filter = 'org';
      btn.dataset.value = o;
      btn.textContent = o.toUpperCase();
      orgGroup.appendChild(btn);
    }});
    var typeGroup = document.getElementById('type-filters');
    Array.from(types).sort().forEach(function(t) {{
      var btn = document.createElement('button');
      btn.className = 'filter-btn';
      btn.dataset.filter = 'type';
      btn.dataset.value = t;
      btn.textContent = t;
      typeGroup.appendChild(btn);
    }});

    // --- Sync button active states ---
    function syncButtons() {{
      document.querySelectorAll('.filter-btn').forEach(function(b) {{
        var f = b.dataset.filter, v = b.dataset.value;
        var active = (f === 'org' && v === activeOrg) ||
                     (f === 'type' && v === activeType) ||
                     (f === 'status' && v === activeStatus);
        b.classList.toggle('active', active);
      }});
    }}

    // --- Apply filters ---
    function applyFilters() {{
      var visible = 0;
      cards.forEach(function(c) {{
        var matchOrg = activeOrg === 'all' || c.dataset.org === activeOrg;
        var matchType = activeType === 'all' || c.dataset.type === activeType;
        var isTest = c.dataset.status === 'true';
        var matchStatus = activeStatus === 'all' || (activeStatus === 'test' && isTest) || (activeStatus === 'live' && !isTest);
        if (matchOrg && matchType && matchStatus) {{
          c.classList.remove('hidden');
          visible++;
        }} else {{
          c.classList.add('hidden');
        }}
      }});

      listOrgs.forEach(function(li) {{
        var matchOrg = activeOrg === 'all' || li.dataset.org === activeOrg;
        if (!matchOrg) {{ li.classList.add('hidden'); return; }}
        var bullets = li.querySelectorAll('ul.list-pages li');
        var anyVisible = false;
        bullets.forEach(function(b) {{
          if (b.classList.contains('list-external')) {{
            var show = activeType === 'all' && activeStatus === 'all';
            b.style.display = show ? '' : 'none';
            if (show) anyVisible = true;
            return;
          }}
          var bType = b.dataset.type;
          var bStatus = b.dataset.status === 'true';
          var matchType = activeType === 'all' || bType === activeType;
          var matchStatus = activeStatus === 'all' || (activeStatus === 'test' && bStatus) || (activeStatus === 'live' && !bStatus);
          if (matchType && matchStatus) {{
            b.style.display = '';
            anyVisible = true;
          }} else {{
            b.style.display = 'none';
          }}
        }});
        li.classList.toggle('hidden', !anyVisible);
      }});

      var nr = document.querySelector('.no-results');
      nr.classList.toggle('visible', visible === 0);

      // Show notice if filtered via URL
      var isFiltered = activeOrg !== 'all' || activeType !== 'all' || activeStatus !== 'all';
      if (isFiltered && fromUrl) {{
        noticeText.textContent = 'Filtered view: showing ' + visible + ' of ' + totalPages + ' pages.';
        notice.style.display = '';
      }} else {{
        notice.style.display = 'none';
      }}
    }}

    // --- Filter clicks ---
    document.addEventListener('click', function(e) {{
      var btn = e.target.closest('.filter-btn');
      if (!btn) return;
      fromUrl = false;
      var f = btn.dataset.filter, v = btn.dataset.value;
      if (f === 'org') activeOrg = v;
      if (f === 'type') activeType = v;
      if (f === 'status') activeStatus = v;
      syncButtons();
      applyFilters();
      writeUrl();
    }});

    // --- Notice buttons ---
    document.getElementById('notice-reset').addEventListener('click', function() {{
      fromUrl = false;
      activeOrg = 'all'; activeType = 'all'; activeStatus = 'all';
      syncButtons();
      applyFilters();
      writeUrl();
    }});
    document.getElementById('notice-close').addEventListener('click', function() {{
      notice.style.display = 'none';
    }});

    // --- Init from URL ---
    readUrl();
    setView(activeView);
    syncButtons();
    applyFilters();
  }})();
  </script>
</body>
</html>"""

    with open("index.html", "w") as f:
        f.write(html)


if __name__ == "__main__":
    main()
