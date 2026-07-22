#!/usr/bin/env python3
"""Build johnplustools.com: a home page plus one page per tool, sharing one shell.

The site is JohnPlusTools; the tools live inside it. Every page gets the same
topbar, the same dropdown and the same content geometry, generated from the
constants in this file, so the pages cannot drift apart. That matters: John's
objection to an earlier version was that moving between pages felt like moving
between two different sites.

One page per tool rather than one document holding them all, because the tools
carry bare element rules (the Debate Builder styles button/input/select, Speaking
Topics styles nav/footer/h2/li) that would leak into each other if merged, and
because a combined page would grow past half a megabyte as tools are added.

    src/<slug>.html   John's tools, verbatim. Never hand-edit.
    (the home page is generated from the TOOLS registry below)
    index.html        GENERATED
    tools/<slug>.html GENERATED

    python3 build.py
    python3 build.py ~/Downloads/debate-builder.html    refresh a source first

Everything injected is fenced in jpt: markers and stripped before re-adding, so
the build re-runs cleanly over a previous result.
"""
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / 'src'
OUT_TOOLS = ROOT / 'tools'
HOME_OUT = ROOT / 'index.html'

I = ('fill="none" stroke="currentColor" stroke-linecap="round" '
     'stroke-linejoin="round" aria-hidden="true"')


def svg(body, w=2):
    return f'<svg viewBox="0 0 24 24" {I} stroke-width="{w}">{body}</svg>'


SPANNER = svg('<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 '
              '7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>')
# Two speech bubbles, the front one shaded. Both currentColor, so the overlap
# seam is invisible and the shading inverts by itself on an accent background.
BUBBLES = (f'<svg viewBox="0 0 24 24" {I} stroke-width="1.9">'
           '<path d="M14.6 3H4.3A1.8 1.8 0 0 0 2.5 4.8v5.9a1.8 1.8 0 0 0 1.8 1.8h.8v3.1l3.3-3.1'
           'h6.2a1.8 1.8 0 0 0 1.8-1.8V4.8A1.8 1.8 0 0 0 14.6 3z"/>'
           '<path d="M20.2 9.6h-6.1A1.6 1.6 0 0 0 12.5 11.2v3.6a1.6 1.6 0 0 0 1.6 1.6h3.6l3 2.7'
           'v-2.7h.5a1.6 1.6 0 0 0 1.3-1.6v-3.6a1.6 1.6 0 0 0-1.6-1.6z" '
           'fill="currentColor" stroke="currentColor"/></svg>')
# Speaking Topics: a question mark inside a bubble, distinct from the debate pair.
ASKING = (f'<svg viewBox="0 0 24 24" {I} stroke-width="1.9">'
          '<path d="M20.5 4.9v8.6a1.9 1.9 0 0 1-1.9 1.9H9.1L4.6 19.4v-3.9a1.9 1.9 0 0 1-1.9-1.9V4.9'
          'A1.9 1.9 0 0 1 4.6 3h14a1.9 1.9 0 0 1 1.9 1.9z"/>'
          '<path d="M9.5 8.1a2.3 2.3 0 0 1 4.5.8c0 1.5-2.3 2.3-2.3 2.3" stroke-width="1.9"/>'
          '<circle cx="11.7" cy="13.2" r="1.05" fill="currentColor" stroke="none"/></svg>')
BOOK = svg('<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>'
           '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>')
HOME_I = svg('<path d="M3 9.5 12 3l9 6.5V20a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 20z"/>'
             '<path d="M9.5 21.5v-7h5v7"/>')
PLAY = svg('<polygon points="5 3 19 12 5 21 5 3"/>')
SAVE = svg('<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
           '<polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>')
CLOCK = svg('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>')
DOWNLOAD = svg('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
               '<polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>')
EYE = svg('<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>')
ARROW = svg('<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>')
CHEV = svg('<polyline points="6 9 12 15 18 9"/>')
EXT = svg('<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
          '<polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>')
GRID = svg('<rect x="3" y="3" width="7.5" height="7.5" rx="1.6"/>'
           '<rect x="13.5" y="3" width="7.5" height="7.5" rx="1.6"/>'
           '<rect x="3" y="13.5" width="7.5" height="7.5" rx="1.6"/>'
           '<rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.6"/>')
SHUFFLE = svg('<polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/>'
              '<polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/>'
              '<line x1="4" y1="4" x2="9" y2="9"/>')
USERS = svg('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
            '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>')
MAXIMISE = svg('<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/>'
               '<line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>')

FAVICON = ("<link rel=\"icon\" href=\"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' "
           "viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2' stroke-linecap='round' "
           "stroke-linejoin='round'><path d='M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 "
           "0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 "
           "7.94-7.94l-3.76 3.76z'/></svg>\">")

SITE = 'John + Tools'
HOME_TITLE = f'{SITE} · free teaching tools for English classrooms'
HOME_DESC = ('Free browser tools for English teachers, by John of JohnPlusEnglish. '
             'No sign-up, nothing to install.')

# ── The tools ────────────────────────────────────────────────────────────────
TOOLS = [
    {
        'slug': 'debate-builder',
        'name': 'Debate Builder',
        'icon': BUBBLES,
        'tagline': 'Build a speaking debate, then run it from the front of the room.',
        'desc': ('Write the question, set the task, and pick a level. The phrase bank swaps '
                 'to match, so B1 gets different language from C2. When the lesson starts, go '
                 'full-screen and run the timer without leaving the page.'),
        'meta': ('Build a speaking debate, set the level and phrase bank, then run it '
                 'full-screen with a timer.'),
        'features': [
            (PLAY, 'Presentation mode',
             'Full-screen prompts, arrow keys to step, space to start the timer. Click a prompt to spotlight it.'),
            (SAVE, 'Saved debate bank',
             'Keep every debate you build and search it later. Back up to a file.'),
            (CLOCK, 'Built-in timer',
             'Set the minutes, start it from the keyboard, keep the room moving.'),
            (DOWNLOAD, 'Export and print',
             'PNG, PDF or straight to the printer if you want it on paper.'),
        ],
        'shot': '/assets/debate-builder-light.png',
        'shot_dark': '/assets/debate-builder-dark.png',
        'shot_alt': ('The Debate Builder in use: a debate titled AI in the classroom, with the '
                     'question, four prompt circles and the C2 phrase bank down the left.'),
    },
    {
        'slug': 'speaking-topics',
        'name': 'Speaking Topics',
        'icon': ASKING,
        'tagline': 'A thousand conversation questions, sorted and ready to put on screen.',
        'desc': ('Fifty topics, each with five personal and five thought-provoking questions at '
                 'two levels. Pick a topic, switch between simple and advanced, and put a single '
                 'question on the screen when you want the room looking the same way.'),
        'meta': ('A thousand conversation questions across fifty topics, at two levels, with a '
                 'timer and a random student picker.'),
        'features': [
            (GRID, 'Fifty topics, two levels',
             'Five personal and five thought-provoking questions each. Switch simple to advanced in a click.'),
            (MAXIMISE, 'Focus mode',
             'One question, full screen, big enough to read from the back of the room.'),
            (USERS, 'Random student picker',
             'Keep your class list and pull a name out of it. Saved in your browser.'),
            (SHUFFLE, 'Random topic and roulette',
             'Stuck for a warm-up? Spin for a topic, or a single question at random.'),
        ],
        'shot': '/assets/speaking-topics-light.png',
        'shot_dark': '/assets/speaking-topics-dark.png',
        'shot_alt': ('Speaking Topics in use: a grid of topics, with a deck of conversation '
                     'questions and a timer below.'),
    },
]

BY_SLUG = {t['slug']: t for t in TOOLS}


def url(slug):
    return f'/{slug}'


# ── Shared chrome ────────────────────────────────────────────────────────────

def brand(current):
    """Topbar brand, doubling as the pop-out switcher. `current` is a slug or 'home'."""
    items = [f'''<a class="pm-item" role="menuitem" href="/" data-nav="home"{
        ' aria-current="true"' if current == 'home' else ''}>
        <span class="pm-ico">{HOME_I}</span>Home</a>''']
    for t in TOOLS:
        items.append(f'''<a class="pm-item" role="menuitem" href="{url(t['slug'])}" data-nav="{t['slug']}"{
            ' aria-current="true"' if current == t['slug'] else ''}>
        <span class="pm-ico">{t['icon']}</span>{t['name']}</a>''')
    items = '\n      '.join(items)
    return f'''<!-- jpt:brand -->
  <div class="brand-wrap">
    <button class="st-brand" id="brandBtn" aria-haspopup="true" aria-expanded="false" aria-controls="toolsMenu">
      <span class="brand-icon">{SPANNER}</span>
      <span class="brand-title"><span class="k">JohnPlusEnglish</span><span class="b">Tools</span></span>
      <span class="brand-chev">{CHEV}</span>
    </button>
    <div class="popmenu" id="toolsMenu" role="menu" aria-labelledby="brandBtn" hidden>
      <div class="pm-label">Go to</div>
      {items}
      <div class="pm-sep"></div>
      <a class="pm-item" role="menuitem" href="https://johnplusdictionary.com" target="_blank" rel="noopener">
        <span class="pm-ico">{BOOK}</span>JohnPlusDictionary<span class="pm-ext">{EXT}</span></a>
    </div>
  </div>
  <!-- /jpt:brand -->'''


THEME_BTN = ('<!-- jpt:themebtn -->\n'
             '  <button class="icon-btn" id="jptThemeBtn" title="Light / dark" '
             'aria-label="Toggle light or dark theme">\n'
             '    <svg id="jptThemeIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
             '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>\n'
             '  </button>\n  <!-- /jpt:themebtn -->')

# Set before first paint so there is no flash. Same key as the Debate Builder,
# so the preference is shared across every page.
THEME_BOOT = ('<!-- jpt:themeboot -->\n<script>(function(){var t;try{t=localStorage.getItem'
              "('jpe_debate_theme')}catch(e){}if(!t)t=window.matchMedia('(prefers-color-scheme:dark)')"
              ".matches?'dark':'light';document.documentElement.setAttribute('data-theme',t)})();"
              '</script>\n<!-- /jpt:themeboot -->')


def tool_head(t):
    return f'''<!-- jpt:toolhead -->
      <div class="tool-head">
        <span class="th-icon">{t['icon']}</span>
        <div class="th-text">
          <h1>{t['name']}</h1>
          <p>{t['tagline']}</p>
        </div>
      </div>
      <!-- /jpt:toolhead -->
      '''


CHROME_CSS = '''
/* jpt:chrome */
/* Site furniture. Identical on every page, so nothing shifts between them. */
:root{
  --bg:#f4f3ec; --card:#ffffff; --ink:#0f1b2d; --muted:#6b7686;
  --line:#eceadf; --accent:#2563eb; --accent-deep:#1d4ed8;
  --soft:#eceffc; --soft-line:#dde3f8;
  --shadow-card:0 1px 2px rgba(20,30,60,.04),0 20px 44px -28px rgba(30,50,110,.35);
}
[data-theme="dark"]{
  --bg:#0f1728; --card:#16213a; --ink:#eef2fb; --muted:#93a0bb;
  --line:#26324c; --accent:#5b8def; --accent-deep:#93b4f6;
  --soft:#1d2b46; --soft-line:#2b3c5c;
  --shadow-card:0 1px 2px rgba(0,0,0,.2),0 20px 44px -28px rgba(0,0,0,.7);
}

.stopbar{position:sticky;top:0;z-index:40;background:var(--card);
  border-bottom:1px solid var(--line);padding:0 22px;height:56px;flex-shrink:0;
  display:flex;align-items:center;gap:14px}
.st-brand{display:inline-flex;align-items:center;gap:10px;text-decoration:none;
  color:var(--ink);line-height:1}
.st-brand .brand-icon{color:var(--accent);width:22px;height:22px;display:inline-flex;flex-shrink:0}
.st-brand .brand-icon svg{width:22px;height:22px}
.st-brand .brand-title{display:inline-flex;flex-direction:column;justify-content:center;gap:2px;line-height:1}
.brand-title .k{font-size:9.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:700}
.brand-title .b{font-size:15px;font-weight:700;letter-spacing:-.01em}
.grow{flex:1}
.icon-btn{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;
  border-radius:999px;background:transparent;border:none;cursor:pointer;color:var(--muted);
  transition:background .12s,color .12s}
.icon-btn svg{width:18px;height:18px;display:block}
.icon-btn:hover{background:var(--soft);color:var(--accent)}

.brand-wrap{position:relative;display:inline-flex}
button.st-brand{background:none;border:none;cursor:pointer;font-family:inherit;
  padding:6px 8px;margin-left:-8px;border-radius:11px;transition:background .12s}
button.st-brand:hover{background:var(--soft)}
.brand-chev{color:var(--muted);display:inline-flex;margin-left:2px;transition:transform .18s ease}
.brand-chev svg{width:14px;height:14px}
button.st-brand[aria-expanded="true"] .brand-chev{transform:rotate(180deg)}
.popmenu{position:absolute;top:calc(100% + 8px);left:0;z-index:60;min-width:246px;
  background:var(--card);border:1px solid var(--line);border-radius:14px;padding:7px;
  box-shadow:0 12px 40px -12px rgba(15,27,45,.28),0 2px 8px rgba(15,27,45,.06);
  animation:pmIn .14s ease}
[data-theme="dark"] .popmenu{box-shadow:0 12px 40px -12px rgba(0,0,0,.6)}
.popmenu[hidden]{display:none}
@keyframes pmIn{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
.pm-label{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);
  font-weight:700;padding:6px 10px 7px}
.pm-item{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:10px;
  text-decoration:none;color:var(--ink);font-size:13.5px;font-weight:600;transition:background .12s}
.pm-item:hover,.pm-item:focus-visible{background:var(--soft);color:var(--accent);outline:none}
.pm-item[aria-current="true"]{background:var(--soft);color:var(--accent)}
.pm-ico{width:18px;height:18px;flex-shrink:0;color:var(--accent);display:inline-flex}
.pm-ico svg{width:18px;height:18px}
.pm-ext{margin-left:auto;color:var(--muted);display:inline-flex}
.pm-ext svg{width:13px;height:13px}
.pm-sep{height:1px;background:var(--line);margin:6px 4px}

/* Content geometry. Identical on the home page and every tool page. */
.shell{min-height:calc(100vh - 56px)}
.main-inner{padding:20px 24px 40px;max-width:1180px;margin:0 auto}
.tool-head{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.th-icon{width:38px;height:38px;border-radius:11px;flex-shrink:0;display:grid;place-items:center;
  background:var(--soft);border:1px solid var(--soft-line);color:var(--accent)}
.th-icon svg{width:20px;height:20px;display:block}
.th-text h1{font-size:19px;font-weight:700;letter-spacing:-.02em;margin:0;line-height:1.2}
.th-text p{font-size:12.5px;color:var(--muted);margin:2px 0 0;line-height:1.4}

@media (max-width:900px){.th-text p{display:none}}
/* The brand is a button with padding and a chevron, wider than a plain mark.
   Left full width it pushes the topbar actions off a phone screen. */
@media (max-width:700px){
  .stopbar{padding:0 14px;gap:10px}
  button.st-brand{padding:6px;margin-left:-6px}
  .brand-title .k{display:none}
  .brand-title .b{font-size:14px}
  .popmenu{min-width:210px}
}
@media print{.tool-head,.popmenu,.stopbar{display:none!important}}
@media (prefers-reduced-motion:reduce){.popmenu{animation:none}}
/* /jpt:chrome */
'''

MENU_JS = '''<!-- jpt:menujs -->
<script>
/* Pop-out switcher. The only navigation on the site. */
(function () {
  var btn = document.getElementById('brandBtn');
  var menu = document.getElementById('toolsMenu');
  if (!btn || !menu) return;
  function close() { if (menu.hidden) return; menu.hidden = true; btn.setAttribute('aria-expanded', 'false'); }
  function open()  { menu.hidden = false; btn.setAttribute('aria-expanded', 'true'); }
  btn.addEventListener('click', function (e) { e.stopPropagation(); menu.hidden ? open() : close(); });
  document.addEventListener('click', function (e) {
    if (!menu.hidden && !menu.contains(e.target) && e.target !== btn) close();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !menu.hidden) { close(); btn.focus(); }
  });
})();
</script>
<!-- /jpt:menujs -->
'''

THEME_JS = '''<!-- jpt:themejs -->
<script>
/* Theme toggle for pages whose tool does not bring its own. Shares the Debate
   Builder's key so the preference carries across the whole site. */
(function () {
  var root = document.documentElement;
  var btn = document.getElementById('jptThemeBtn');
  var icon = document.getElementById('jptThemeIcon');
  if (!btn || !icon) return;
  var SUN = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/>'
          + '<line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>'
          + '<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/>'
          + '<line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>'
          + '<line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>';
  var MOON = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
  function now(){ return root.getAttribute('data-theme')
      || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); }
  function paint(){ icon.innerHTML = now() === 'dark' ? SUN : MOON; }
  paint();
  btn.addEventListener('click', function () {
    var next = now() === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('jpe_debate_theme', next); } catch (e) {}
    paint();
  });
})();
</script>
<!-- /jpt:themejs -->
'''


def script_spans(html):
    return [(m.start(), m.end()) for m in re.finditer(r'<script[^>]*>.*?</script>', html, re.S)]


def sole_position(html, needle, what):
    """Position of `needle`, ignoring any inside a <script>.

    Speaking Topics builds a whole printable HTML document inside a JS string,
    so its source contains a </head> and a </body> that are not the page's.
    Replacing blindly injected tags into that string and shattered the script.
    """
    spans = script_spans(html)
    hits = [m.start() for m in re.finditer(re.escape(needle), html)
            if not any(a <= m.start() < b for a, b in spans)]
    if len(hits) != 1:
        raise SystemExit(f'build: expected exactly one {needle} outside a script '
                         f'for {what}, found {len(hits)}')
    return hits[0]


def inject_before(html, needle, payload, what):
    i = sole_position(html, needle, what)
    return html[:i] + payload + html[i:]


def drop(html, tag):
    return re.sub(rf'<!-- {tag} -->.*?<!-- /{tag} -->\n?\s*', '', html, flags=re.S)


def strip_marks(html):
    for tag in ('jpt:brand', 'jpt:toolsnav', 'jpt:sidefoot', 'jpt:toolhead', 'jpt:debateslabel',
                'jpt:homeview', 'jpt:router', 'jpt:backlink', 'jpt:menujs', 'jpt:themejs',
                'jpt:themebtn', 'jpt:themeboot', 'jpt:strip'):
        html = drop(html, tag)
    html = re.sub(r'/\* jpt:chrome \*/.*?/\* /jpt:chrome \*/\n?', '', html, flags=re.S)
    html = re.sub(r'/\* jpt:speaking \*/.*?/\* /jpt:speaking \*/\n?', '', html, flags=re.S)
    return html


def head_bits(html, title, desc, extra_css):
    html = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', html, count=1, flags=re.S)
    html = re.sub(r'<meta\s+name="description"[^>]*>\n?', '', html)
    inject = (f'<meta name="description" content="{desc}">\n'
              f'<meta name="color-scheme" content="light dark">\n{FAVICON}\n{THEME_BOOT}\n')
    html = html.replace(f'<title>{title}</title>', f'<title>{title}</title>\n{inject}', 1)
    html = inject_before(html, '</head>', f'<style>{CHROME_CSS}{extra_css}</style>\n', 'the stylesheet')
    return html


def need(html, needle, what):
    if needle not in html:
        raise SystemExit(f'build: could not find {what}')
    return html


# ── Per-tool CSS ─────────────────────────────────────────────────────────────

DEBATE_CSS = '''
/* jpt:speaking */
/* (shared block name; this page's extras) */
.jt-label{font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--muted);font-weight:700;margin-bottom:9px}
/* The collapse handle rides the divider between the sidebar and the content.
   Fixed, so it stays on that line while the page scrolls, and it tracks the
   sidebar width. max() keeps it fully on screen once collapsed, where centring
   on a zero-width divider would cut it in half. */
.app{--jpt-side-w:302px}
.app.side-collapsed{--jpt-side-w:0px}
#sideToggle{
  position:fixed;top:140px;left:max(15px,var(--jpt-side-w));
  transform:translateX(-50%);z-index:39;margin:0;
  width:30px;height:30px;border-radius:999px;
  background:var(--card);border:1px solid var(--line);
  box-shadow:0 1px 4px rgba(15,27,45,.10);
  transition:left .22s ease,background .12s,color .12s,border-color .12s;
}
[data-theme="dark"] #sideToggle{box-shadow:0 1px 4px rgba(0,0,0,.35)}
#sideToggle:hover{background:var(--soft);color:var(--accent);border-color:var(--accent)}
#sideToggle:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:900px){#sideToggle{display:none}}
@media print{#sideToggle{display:none!important}}
/* /jpt:speaking */
'''

SPEAKING_CSS = '''
/* jpt:speaking */
/* Map the tool's own palette onto the site tokens. Its CSS keeps referring to
   its variable names; they now resolve to the site's, so it picks up both
   themes without touching a single one of its rules. */
:root{
  --cream:var(--bg);
  --border:var(--line);
  --sky:var(--accent);
  --sky-light:var(--soft);
  --radius:14px;
  --shadow-sm:0 1px 3px rgba(20,30,60,.06);
  --shadow-md:0 4px 12px rgba(20,30,60,.08);
}
[data-theme="dark"]{
  --shadow-sm:0 1px 3px rgba(0,0,0,.35);
  --shadow-md:0 4px 12px rgba(0,0,0,.45);
  /* Decorative accents, lifted so they stay legible on the dark card. */
  --sun:#f0b866; --sea:#4fd8bd; --coral:#ff8585; --lavender:#b391dd; --mint:#7ae2b4;
  --sand:#2a2418;
}
/* Its layout sat on a full-width page; inside the shell it uses the site's
   content geometry instead, so it lines up with the other pages. */
body{background:var(--bg);color:var(--ink)}
.controls,.main{max-width:none;margin:0;padding-left:0;padding-right:0}
.main{margin-top:22px}
/* Its overlays sit above the topbar, as the Debate Builder's presentation does. */
.focus-overlay,.roulette-overlay{z-index:200}
/* /jpt:speaking */
'''


# ── Page builders ────────────────────────────────────────────────────────────

def build_debate(html, t):
    html = strip_marks(html)
    html = head_bits(html, f"{t['name']} · {SITE}", t['meta'], DEBATE_CSS)

    m = re.search(r'<a href="#" class="st-brand".*?</a>', html, re.S)
    if not m:
        raise SystemExit('build: debate builder brand not found')
    html = html[:m.start()] + brand(t['slug']) + html[m.end():]

    label = ('<!-- jpt:debateslabel --><div class="jt-label" style="margin-bottom:9px">'
             'Debates</div><!-- /jpt:debateslabel -->\n        ')
    before = '<div class="side-top">\n      <div class="searchwrap">'
    html = need(html, before, 'the sidebar search to label')
    html = html.replace(before, '<div class="side-top">\n      ' + label + '<div class="searchwrap">', 1)

    # Must be the FIRST child of #cardHome: exitPresent puts the card back with
    # appendChild, so anything after it leaves the pane reordered on the way out.
    home = '<div class="main-inner" id="cardHome">'
    html = need(html, home, '#cardHome')
    html = html.replace(home, home + '\n      ' + tool_head(t), 1)

    html = inject_before(html, '</body>', MENU_JS, 'the menu script')
    return html


def build_speaking(html, t):
    html = strip_marks(html)
    html = head_bits(html, f"{t['name']} · {SITE}", t['meta'], SPEAKING_CSS)

    # Strip the tool's own site chrome: its nav, its page header, its footer.
    for pat, what in [(r'<div class="topnav">.*?</div>\s*</div>\s*', 'its top nav'),
                      (r'<div class="page-header">.*?</div>\s*(?=<div class="controls">)', 'its page header'),
                      (r'<footer>.*?</footer>\s*', 'its footer')]:
        html, n = re.subn(pat, '', html, count=1, flags=re.S)
        if not n:
            raise SystemExit(f'build: could not strip {what} from {t["slug"]}')

    # Wrap its content in the site's shell so the geometry matches every page.
    opened = ('<header class="stopbar">\n' + brand(t['slug'])
              + '\n  <div class="grow"></div>\n  ' + THEME_BTN + '\n</header>\n\n'
              '<div class="shell">\n  <main>\n    <div class="main-inner">\n      '
              + tool_head(t) + '\n')
    html = need(html, '<div class="controls">', 'its controls block')
    html = html.replace('<div class="controls">', opened + '<div class="controls">', 1)

    # Close the shell before the overlays, which belong at body level.
    close_at = '<div class="focus-overlay"'
    html = need(html, close_at, 'the focus overlay')
    html = html.replace(close_at, '    </div>\n  </main>\n</div>\n\n' + close_at, 1)

    html = inject_before(html, '</body>', MENU_JS + THEME_JS, 'the page scripts')
    return html


BUILDERS = {'debate-builder': build_debate, 'speaking-topics': build_speaking}


def home_page():
    cards = []
    for t in TOOLS:
        feats = '\n'.join(
            f'''            <div class="feature">
              <span class="fi">{ic}</span>
              <div><h3>{h}</h3><p>{p}</p></div>
            </div>''' for ic, h, p in t['features'])
        cards.append(f'''      <section class="panel">
        <div class="panel-head">
          <span class="panel-icon">{t['icon']}</span>
          <div>
            <h2>{t['name']}</h2>
            <div class="tagline">{t['tagline']}</div>
          </div>
        </div>
        <p class="lede">{t['desc']}</p>
        <div class="split">
          <div class="features">
{feats}
          </div>
          <a class="preview" href="{url(t['slug'])}" style="--shot:url('{t['shot']}');--shot-dark:url('{t['shot_dark']}')">
            <span class="pv-bar" aria-hidden="true"><i></i><i></i><i></i></span>
            <span class="pv-shot" role="img" aria-label="{t['shot_alt']}"></span>
            <span class="pv-cap">{EYE} Have a look inside</span>
          </a>
        </div>
        <div class="panel-actions">
          <a class="btn big" href="{url(t['slug'])}">{ARROW} Open {t['name']}</a>
          <span class="note">Free, no sign-up. Your work stays in your browser.</span>
        </div>
      </section>''')
    cards = '\n\n'.join(cards)
    count = f"{len(TOOLS)} tool" + ('s' if len(TOOLS) != 1 else '')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{HOME_TITLE}</title>
<meta name="description" content="{HOME_DESC}">
<meta name="color-scheme" content="light dark">
<meta property="og:title" content="{HOME_TITLE}">
<meta property="og:description" content="{HOME_DESC}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://johnplustools.com">
{FAVICON}
{THEME_BOOT}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--ink);
  font-family:"Outfit",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  line-height:1.6;-webkit-font-smoothing:antialiased}}
::selection{{background:var(--accent);color:#fff}}
a{{color:inherit}}
svg{{display:block}}
{CHROME_CSS}
a.btn{{text-decoration:none}}
.btn{{font-family:inherit;font-size:13px;font-weight:600;padding:8px 14px;border-radius:999px;
  border:1px solid transparent;background:var(--accent);color:#fff;cursor:pointer;
  display:inline-flex;align-items:center;gap:7px;white-space:nowrap;
  transition:background .15s}}
.btn:hover{{background:var(--accent-deep)}}
.btn svg{{width:14px;height:14px;flex-shrink:0}}
.btn.big{{font-size:14px;padding:11px 20px}}
.btn.big svg{{width:15px;height:15px}}
.count{{font-size:11px;color:var(--muted);letter-spacing:.14em;text-transform:uppercase;
  font-weight:700;margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid var(--line)}}
.panel{{background:var(--card);border:1px solid var(--line);border-radius:18px;
  padding:30px 32px;box-shadow:var(--shadow-card);margin-bottom:20px}}
.panel-head{{display:flex;align-items:flex-start;gap:16px;margin-bottom:20px}}
.panel-icon{{width:48px;height:48px;border-radius:13px;flex-shrink:0;background:var(--soft);
  border:1px solid var(--soft-line);color:var(--accent);display:grid;place-items:center}}
.panel-icon svg{{width:24px;height:24px}}
.panel h2{{font-size:1.5rem;font-weight:700;letter-spacing:-.025em;line-height:1.15;margin:0}}
.panel .tagline{{font-size:.93rem;color:var(--muted);margin-top:4px}}
.panel .lede{{font-size:1rem;color:var(--ink);max-width:62ch;margin-bottom:24px;line-height:1.65}}
.split{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.08fr);
  gap:32px;align-items:start;margin-bottom:28px}}
.features{{display:grid;gap:15px;grid-template-columns:1fr}}
.feature{{display:flex;gap:11px;align-items:flex-start}}
.feature .fi{{color:var(--accent);flex-shrink:0;margin-top:2px;display:inline-flex}}
.feature .fi svg{{width:17px;height:17px}}
.feature h3{{font-size:.88rem;font-weight:700;letter-spacing:-.01em;margin-bottom:1px}}
.feature p{{font-size:.84rem;color:var(--muted);line-height:1.5}}
.preview{{display:block;text-decoration:none;color:inherit;border:1px solid var(--line);
  border-radius:12px;overflow:hidden;background:var(--bg);box-shadow:var(--shadow-card);
  transition:border-color .16s,transform .16s}}
.preview:hover{{border-color:var(--accent);transform:translateY(-2px)}}
.preview:focus-visible{{outline:2px solid var(--accent);outline-offset:3px}}
.pv-bar{{display:flex;align-items:center;gap:5px;padding:0 10px;height:26px;
  background:var(--card);border-bottom:1px solid var(--line)}}
.pv-bar i{{width:7px;height:7px;border-radius:999px;background:var(--line);flex-shrink:0}}
[data-theme="dark"] .pv-bar i{{background:var(--soft-line)}}
/* Background image, not <img>, so only the theme in use is downloaded. */
.pv-shot{{display:block;aspect-ratio:1100/515;background-image:var(--shot);
  background-size:cover;background-position:top center;background-repeat:no-repeat}}
[data-theme="dark"] .pv-shot{{background-image:var(--shot-dark)}}
.pv-cap{{display:flex;align-items:center;gap:6px;padding:9px 12px;font-size:12px;
  font-weight:600;color:var(--muted);background:var(--card);border-top:1px solid var(--line)}}
.pv-cap svg{{width:13px;height:13px;flex-shrink:0}}
.preview:hover .pv-cap{{color:var(--accent)}}
.panel-actions{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;
  padding-top:22px;border-top:1px solid var(--line)}}
.panel-actions .note{{font-size:12.5px;color:var(--muted);font-weight:500}}
@media (max-width:900px){{
  .split{{grid-template-columns:1fr;gap:24px}}
  .panel{{padding:22px 18px;border-radius:16px}}
  .main-inner{{padding:16px 14px 34px}}
}}
</style>
</head>
<body>

<header class="stopbar">
{brand('home')}
  <div class="grow"></div>
  {THEME_BTN}
</header>

<div class="shell">
  <main>
    <div class="main-inner">

      <div class="tool-head">
        <span class="th-icon">{SPANNER}</span>
        <div class="th-text">
          <h1>Teaching tools</h1>
          <p>Small, focused tools for English classrooms. Nothing to install, no account to make.</p>
        </div>
      </div>

      <div class="count">{count}</div>

{cards}

    </div>
  </main>
</div>

{MENU_JS}{THEME_JS}
</body>
</html>
'''


def main():
    if len(sys.argv) > 1:
        incoming = pathlib.Path(sys.argv[1]).expanduser()
        text = incoming.read_text(encoding='utf-8')
        if '<!-- jpt:brand -->' in text:
            raise SystemExit(f'build: {incoming} is already a built page, not a tool source.')
        stem = incoming.stem.split(' (')[0]
        guess = {'debate-builder': 'debate-builder', 'speaking-questions': 'speaking-topics',
                 'speaking-topics': 'speaking-topics'}.get(stem)
        if not guess:
            raise SystemExit(f'build: do not know which tool {incoming.name} is. '
                             f'Known: {", ".join(BY_SLUG)}')
        shutil.copyfile(incoming, SRC / f'{guess}.html')
        print(f'  src/{guess}.html updated from {incoming.name}')

    OUT_TOOLS.mkdir(exist_ok=True)
    for t in TOOLS:
        src = SRC / f"{t['slug']}.html"
        if not src.exists():
            raise SystemExit(f'build: missing {src}')
        out = BUILDERS[t['slug']](src.read_text(encoding='utf-8'), t)
        dest = OUT_TOOLS / f"{t['slug']}.html"
        dest.write_text(out, encoding='utf-8')

        assert out.count('<!-- jpt:brand -->') == 1, f"{t['slug']}: brand not injected once"
        assert out.count('<!-- jpt:toolhead -->') == 1, f"{t['slug']}: tool head not injected once"
        assert '<span class="b">Tools</span>' in out, f"{t['slug']}: brand should read Tools"
        assert out.count('class="pm-item"') == len(TOOLS) + 2, f"{t['slug']}: dropdown wrong size"
        # Count the attribute on real menu links, not the CSS selector that
        # also contains the string.
        assert len(re.findall(r'<a class="pm-item"[^>]*aria-current="true"', out)) == 1, \
            f"{t['slug']}: current entry not marked exactly once"
        assert 'johnplusdictionary.com' in out, f"{t['slug']}: lost the dictionary link"
        for dash in ('—', '–'):
            assert dash not in CHROME_CSS + MENU_JS + THEME_JS + brand(t['slug']) + tool_head(t), \
                'dash crept into injected copy'
        print(f"  wrote tools/{t['slug']}.html  ({len(out):,} bytes)")

    home = home_page()
    HOME_OUT.write_text(home, encoding='utf-8')
    assert home.count('class="panel"') == len(TOOLS), 'home should show every tool'
    assert len(re.findall(r'<a class="pm-item"[^>]*aria-current="true"', home)) == 1, \
        'home not marked exactly once in its own dropdown'
    for dash in ('—', '–'):
        assert dash not in home, 'dash in the home page'
    print(f'  wrote index.html  ({len(home):,} bytes)  {len(TOOLS)} tools listed')


if __name__ == '__main__':
    main()
