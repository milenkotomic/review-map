#!/usr/bin/env python3 -I
"""Render a review-map Markdown file to a standalone HTML page.

Usage: render.py input.md output.html

GitHub-flavored Markdown via marked.js, sanitized with DOMPurify. Both are
vendored in vendor/ and inlined, so the page is fully offline. The Markdown is
untrusted (it quotes diffs and PR bodies), so it is embedded as a JSON string,
parsed in the browser, and sanitized before it touches the DOM; a
Content-Security-Policy allows only the page's own inline scripts (by hash)
and no network access. Diff fences get per-line add/remove coloring,
<details> blocks collapse, and review-note severities (Blocker, Should fix,
Consider, FYI) become badges.

Styling follows the Milenko Tomic brand book (claude.ai/design project
"Milenko Tomic - Brand Book"): Cobalt / Ink / Paper / Wire tokens, Geist for
text, JetBrains Mono for code and labels, 1px Wire borders, 8px cards, 4px
badges, semantic green / amber / red used only where meaning requires them.
Dark mode is the brand's Inverted Ink surface. Fonts are expected to be
installed locally (they are in the brand book's fonts/ folder); the stacks
fall back to system fonts. Tokens live in the :root blocks below; change them
there only.
"""
import base64
import datetime
import hashlib
import html
import json
import pathlib
import re
import sys

if len(sys.argv) != 3:
    sys.exit("usage: render.py input.md output.html")

src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as handle:
    md = handle.read()

VENDOR = pathlib.Path(__file__).resolve().parent / "vendor"

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="__CSP__">
<title>__TITLE__</title>
<style>
/* ---- Brand tokens (raw) ---- */
:root {
  --cobalt: #1B4DCC; --cobalt-deep: #143CA0; --azure: #5B8DEF; --azure-soft: #C9D8FA;
  --ink: #0A1530; --ink-2: #2A3454; --ink-3: #58607A;
  --paper: #F4F5F8; --paper-2: #ECEEF3; --white: #FFFFFF;
  --wire: #D4D9E4; --wire-strong: #B7BFD0;
  --success: #10A37F; --warning: #E0A106; --error: #D14836;
  --font-sans: "Geist", "Geist Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --radius-sm: 4px; --radius-md: 8px;
  --size: 17px;
}
/* ---- Semantic tokens, light (Paper) ---- */
:root {
  --bg: var(--paper); --bg-elev: var(--white); --bg-alt: var(--paper-2);
  --fg: var(--ink); --fg-muted: var(--ink-2); --fg-subtle: var(--ink-3);
  --accent: var(--cobalt); --accent-hi: var(--azure); --mark: var(--cobalt);
  --border: var(--wire); --border-strong: var(--wire-strong);
  --code-bg: var(--paper-2);
  --pre-bg: var(--ink); --pre-fg: var(--paper);
  --add-bg: rgba(16, 163, 127, 0.22); --add-fg: #8FE8CF;
  --del-bg: rgba(209, 72, 54, 0.26); --del-fg: #F7B0A6;
  --badge-error-bg: rgba(209, 72, 54, 0.12); --badge-error-fg: #A03325;
  --badge-warning-bg: rgba(224, 161, 6, 0.18); --badge-warning-fg: #8C6500;
  --badge-info-bg: rgba(27, 77, 204, 0.10); --badge-info-fg: var(--cobalt);
  --badge-neutral-bg: var(--paper-2); --badge-neutral-fg: var(--ink-3);
  --banner-ok-bg: rgba(16, 163, 127, 0.10); --banner-ok-fg: #0B7A60;
  --banner-bad-bg: rgba(209, 72, 54, 0.10); --banner-bad-fg: #A03325;
}
/* ---- Semantic tokens, dark (Inverted Ink) ---- */
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: var(--ink); --bg-elev: #111D3E; --bg-alt: #16234A;
  --fg: var(--paper); --fg-muted: #C3CADB; --fg-subtle: #8A94B0;
  --accent: var(--azure); --accent-hi: #8FB0F5; --mark: var(--azure);
  --border: #243359; --border-strong: #35466F;
  --code-bg: #16234A;
  --pre-bg: #060D22; --pre-fg: var(--paper);
  --add-bg: rgba(16, 163, 127, 0.20); --add-fg: #8FE8CF;
  --del-bg: rgba(209, 72, 54, 0.24); --del-fg: #F7B0A6;
  --badge-error-bg: rgba(209, 72, 54, 0.22); --badge-error-fg: #F7B0A6;
  --badge-warning-bg: rgba(224, 161, 6, 0.22); --badge-warning-fg: #F2CF6B;
  --badge-info-bg: rgba(91, 141, 239, 0.18); --badge-info-fg: #9DBBF7;
  --badge-neutral-bg: #1C2A55; --badge-neutral-fg: #A9B3CC;
  --banner-ok-bg: rgba(16, 163, 127, 0.14); --banner-ok-fg: #8FE8CF;
  --banner-bad-bg: rgba(209, 72, 54, 0.16); --banner-bad-fg: #F7B0A6;
} }
:root[data-theme="dark"] {
  --bg: var(--ink); --bg-elev: #111D3E; --bg-alt: #16234A;
  --fg: var(--paper); --fg-muted: #C3CADB; --fg-subtle: #8A94B0;
  --accent: var(--azure); --accent-hi: #8FB0F5; --mark: var(--azure);
  --border: #243359; --border-strong: #35466F;
  --code-bg: #16234A;
  --pre-bg: #060D22; --pre-fg: var(--paper);
  --add-bg: rgba(16, 163, 127, 0.20); --add-fg: #8FE8CF;
  --del-bg: rgba(209, 72, 54, 0.24); --del-fg: #F7B0A6;
  --badge-error-bg: rgba(209, 72, 54, 0.22); --badge-error-fg: #F7B0A6;
  --badge-warning-bg: rgba(224, 161, 6, 0.22); --badge-warning-fg: #F2CF6B;
  --badge-info-bg: rgba(91, 141, 239, 0.18); --badge-info-fg: #9DBBF7;
  --badge-neutral-bg: #1C2A55; --badge-neutral-fg: #A9B3CC;
  --banner-ok-bg: rgba(16, 163, 127, 0.14); --banner-ok-fg: #8FE8CF;
  --banner-bad-bg: rgba(209, 72, 54, 0.16); --banner-bad-fg: #F7B0A6;
}

/* ---- Base ---- */
html { background: var(--bg); }
body { margin: 0; color: var(--fg); background: var(--bg); font: 400 var(--size)/1.55 var(--font-sans);
  font-feature-settings: "ss01", "cv11"; -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; }
::selection { background: var(--azure-soft); color: var(--ink); }
.strip { font: 500 12px/1 var(--font-mono); letter-spacing: 0.04em; text-transform: uppercase; color: var(--fg-subtle);
  border-bottom: 1px solid var(--border); padding: 10px 24px; display: flex; gap: 20px; align-items: center; background: var(--bg-elev); }
.strip .mark { color: var(--fg); text-transform: none; letter-spacing: 0; font-weight: 600; }
.strip .mark b { color: var(--mark); font-weight: 600; }
.strip .cursor { display: inline-block; width: 7px; height: 12px; background: var(--mark); vertical-align: -1px; margin-left: 2px;
  animation: blink 1.1s steps(1) 3; }
@keyframes blink { 50% { opacity: 0; } }
.strip .sep { color: var(--border-strong); }
article { max-width: 1040px; margin: 0 auto; padding: 40px 24px 80px; }

/* ---- Type ---- */
h1 { font-size: 2.1em; font-weight: 600; line-height: 1.1; letter-spacing: -0.018em; margin: 0 0 10px; }
h1 + p { font-size: 1.15em; line-height: 1.45; color: var(--fg-muted); margin: 0 0 8px; }
h2 { font-size: 1.5em; font-weight: 600; line-height: 1.15; letter-spacing: -0.012em; margin: 48px 0 14px; padding-bottom: 8px;
  border-bottom: 1px solid var(--border); }
h3 { font: 600 0.95em/1.4 var(--font-mono); letter-spacing: 0; margin: 32px 0 6px; color: var(--fg); }
h3 code { font-size: 1em; background: none; border: 0; padding: 0; }
p, li { max-width: 80ch; text-wrap: pretty; }
li { margin: 4px 0; }
a { color: var(--accent); text-decoration: none; background: linear-gradient(currentColor, currentColor) 0 100% / 0 1px no-repeat;
  transition: background-size 200ms cubic-bezier(0.2, 0, 0, 1); }
a:hover { background-size: 100% 1px; color: var(--accent-hi); }
strong { font-weight: 600; }

/* ---- Code ---- */
code { font-family: var(--font-mono); font-feature-settings: "calt" 0; font-size: 0.9em; background: var(--code-bg);
  padding: 2px 6px; border-radius: var(--radius-sm); border: 1px solid var(--border); color: var(--fg); }
pre { font-family: var(--font-mono); font-size: 13.5px; line-height: 1.55; background: var(--pre-bg); color: var(--pre-fg);
  padding: 16px; border-radius: var(--radius-md); overflow-x: auto; margin: 10px 0; }
pre code { background: transparent; border: 0; padding: 0; color: inherit; font-size: inherit; }
pre.diff span { display: block; margin: 0 -16px; padding: 0 16px; }
pre.diff .add { background: var(--add-bg); color: var(--add-fg); }
pre.diff .del { background: var(--del-bg); color: var(--del-fg); }
pre.diff .ell { color: var(--fg-subtle); }

/* ---- Tables ---- */
table { border-collapse: separate; border-spacing: 0; width: 100%; margin: 14px 0 20px; font-size: 0.9em; background: var(--bg-elev);
  border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; }
th, td { border-bottom: 1px solid var(--border); padding: 9px 14px; text-align: left; vertical-align: top; }
th + th, td + td { border-left: 1px solid var(--border); }
th { font: 500 11px/1.2 var(--font-mono); letter-spacing: 0.04em; text-transform: uppercase; color: var(--fg-subtle); background: var(--bg-alt); }
tr:last-child td { border-bottom: 0; }
tr.role td { background: var(--bg-alt); font: 500 11px/1.2 var(--font-mono); letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--accent); padding: 7px 14px; }
tr.role td strong { font-weight: 500; }
tr.generated td { color: var(--fg-subtle); }
td code { font-size: 0.92em; }

/* ---- Collapsibles ---- */
details { border: 1px solid var(--border); border-radius: var(--radius-md); padding: 10px 16px; margin: 12px 0 26px; background: var(--bg-elev);
  transition: border-color 120ms cubic-bezier(0.2, 0, 0, 1); }
details:hover { border-color: var(--border-strong); }
details[open] { padding-bottom: 6px; }
summary { cursor: pointer; font: 500 12px/1 var(--font-mono); letter-spacing: 0.04em; text-transform: uppercase; color: var(--fg-subtle); }
summary::marker { color: var(--accent); }
details pre { margin-top: 12px; }

/* ---- Badges and banners ---- */
.badge { display: inline-flex; align-items: center; gap: 6px; font: 500 10.5px/1 var(--font-mono); letter-spacing: 0.04em;
  text-transform: uppercase; padding: 4px 8px; border-radius: var(--radius-sm); margin-right: 10px; vertical-align: 2px; white-space: nowrap; }
.badge.blocker { background: var(--badge-error-bg); color: var(--badge-error-fg); }
.badge.shouldfix { background: var(--badge-warning-bg); color: var(--badge-warning-fg); }
.badge.consider { background: var(--badge-info-bg); color: var(--badge-info-fg); }
.badge.fyi { background: var(--badge-neutral-bg); color: var(--badge-neutral-fg); }
.banner { border: 1px solid var(--border); border-left: 3px solid; border-radius: var(--radius-md); padding: 10px 16px; max-width: none; }
.banner.ok { background: var(--banner-ok-bg); border-left-color: var(--success); color: var(--banner-ok-fg); }
.banner.bad { background: var(--banner-bad-bg); border-left-color: var(--error); color: var(--banner-bad-fg); }
ol.index { padding-left: 1.4em; }
ol.index li::marker { font-family: var(--font-mono); color: var(--fg-subtle); }
footer { max-width: 1040px; margin: 0 auto; padding: 0 24px 40px; color: var(--fg-subtle); font: 400 12px/1.5 var(--font-mono); }
@media (max-width: 640px) { :root { --size: 16px; } article { padding: 24px 16px 60px; } .strip { padding: 10px 16px; gap: 12px; } }
</style></head><body>
<div class="strip">
  <span class="mark"><b>$</b>mt.c<span class="cursor"></span></span>
  <span class="sep">//</span><span>review-map</span>
  <span class="sep">//</span><span>__DATE__</span>
</div>
<article id="out"></article>
<footer>facts in tables and hunks come from the diff // prose is the model's reading</footer>
<script id="src" type="application/json">__MD__</script>
<script>__MARKED__</script>
<script>__PURIFY__</script>
<script>__MAIN__</script>
</body></html>
"""

# Raw string: the backslashes below are JavaScript escapes, passed through as is.
MAIN_JS = r"""
const md = JSON.parse(document.getElementById('src').textContent);
marked.setOptions({ gfm: true, breaks: false });
const out = document.getElementById('out');
// The Markdown quotes untrusted diffs and PR text: never insert it unsanitized.
// Styles are forbidden too: the CSP allows inline styles, so raw HTML could restyle the page.
out.innerHTML = DOMPurify.sanitize(marked.parse(md), { FORBID_TAGS: ['style'], FORBID_ATTR: ['style'] });

// Diff coloring per line.
for (const block of document.querySelectorAll('pre > code.language-diff')) {
  block.parentElement.classList.add('diff');
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
  block.innerHTML = block.textContent.replace(/\n$/, '').split('\n').map(l => {
    const cls = l.startsWith('+') ? 'add' : l.startsWith('-') ? 'del' : l.trim() === '...' ? 'ell' : 'ctx';
    return '<span class="' + cls + '">' + (esc(l) || ' ') + '</span>';
  }).join('');
}

// Footprint: bold single-cell rows are role headers; rows under "Generated" are muted.
for (const table of out.querySelectorAll('table')) {
  let generated = false;
  for (const row of table.querySelectorAll('tbody tr')) {
    const first = row.cells[0];
    const isRole = first && first.querySelector('strong') && [...row.cells].slice(1).every(c => !c.textContent.trim());
    if (isRole) { row.classList.add('role'); generated = /generated/i.test(first.textContent); }
    else if (generated) row.classList.add('generated');
  }
}

// Review notes: severity badges and the blocker banner.
const sev = { 'blocker': 'blocker', 'should fix': 'shouldfix', 'consider': 'consider', 'fyi': 'fyi' };
for (const strong of out.querySelectorAll('li > strong')) {
  const key = strong.textContent.trim().toLowerCase().replace(/:$/, '');
  if (!sev[key]) continue;
  const badge = document.createElement('span');
  badge.className = 'badge ' + sev[key];
  badge.textContent = strong.textContent.replace(/:$/, '');
  strong.replaceWith(badge);
  const next = badge.nextSibling;
  if (next && next.nodeType === 3) next.textContent = next.textContent.replace(/^\s*:\s*/, '');
}
for (const h of out.querySelectorAll('h2')) {
  if (/review notes/i.test(h.textContent)) {
    const p = h.nextElementSibling;
    if (p && p.tagName === 'P') p.classList.add('banner', /^no blockers/i.test(p.textContent) ? 'ok' : 'bad');
  }
  if (/key changes/i.test(h.textContent)) {
    const ol = h.nextElementSibling;
    if (ol && ol.tagName === 'OL') ol.classList.add('index');
  }
}
"""


def inline_js(code):
    """Make JS safe inside <script>: no sequence may end or re-enter script data.

    Both sequences only occur inside string or regex literals in the vendored
    files, where \\x3C is an equivalent escape for '<'.
    """
    return re.sub(r"<(?=/script|!--)", r"\\x3C", code, flags=re.IGNORECASE)


def csp_hash(code):
    return "'sha256-" + base64.b64encode(hashlib.sha256(code.encode("utf-8")).digest()).decode() + "'"


scripts = {
    "__MARKED__": inline_js((VENDOR / "marked.min.js").read_text(encoding="utf-8")),
    "__PURIFY__": inline_js((VENDOR / "purify.min.js").read_text(encoding="utf-8")),
    "__MAIN__": MAIN_JS,
}
csp = ("default-src 'none'; script-src " + " ".join(csp_hash(c) for c in scripts.values())
       + "; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'")

title = next((line[2:].strip() for line in md.splitlines() if line.startswith("# ")), "Review map")
# JSON with every '<' escaped cannot close the data <script>, whatever its case.
md_json = json.dumps(md).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
values = {
    "__CSP__": csp,
    "__TITLE__": html.escape(title),
    "__DATE__": datetime.date.today().isoformat(),
    "__MD__": md_json,
    **scripts,
}
# One pass, so a placeholder that appears inside a substituted value is never expanded.
page = re.sub("|".join(map(re.escape, values)), lambda m: values[m.group(0)], PAGE)
with open(dst, "w", encoding="utf-8") as handle:
    handle.write(page)
print(dst)
