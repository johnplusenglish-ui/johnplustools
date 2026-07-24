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
import json
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
# Speaking Topics: a talk bubble with three dots (conversation), distinct from
# the debate's two shaded bubbles.
ASKING = (f'<svg viewBox="0 0 24 24" {I} stroke-width="1.9">'
          '<path d="M21 11.5a8.5 8.5 0 0 1-12.2 7.6L3 21l1.9-5.8A8.5 8.5 0 1 1 21 11.5z"/>'
          '<circle cx="8.2" cy="11.5" r="1.05" fill="currentColor" stroke="none"/>'
          '<circle cx="12" cy="11.5" r="1.05" fill="currentColor" stroke="none"/>'
          '<circle cx="15.8" cy="11.5" r="1.05" fill="currentColor" stroke="none"/></svg>')
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
        'slug': 'role-plays',
        'name': 'Role Plays',
        'icon': USERS,
        'tagline': 'Two role cards, one scenario. Hand them out and let students act.',
        'desc': ('A hundred pair role plays grouped by setting: café, restaurant, airport, '
                 'job interview, doctor and twenty more. Each setting carries the same scene '
                 'at four CEFR levels (B1, B2, C1, C2), so you can pitch the same situation '
                 'to any class you teach.'),
        'meta': ('A hundred pair role plays for English speaking practice, grouped by setting '
                 'and pitched at B1, B2, C1 and C2.'),
        'features': [
            (USERS, 'Two cards, one scenario',
             'Student A and Student B side by side, each with their own situation to work from.'),
            (GRID, 'Twenty-five settings',
             'Café, restaurant, airport, job interview, doctor and more. Each setting carries the same scene at B1, B2, C1 and C2.'),
            (BOOK, 'Search across the lot',
             'Type a keyword and every role and scenario searches at once.'),
        ],
        'shot': '/assets/role-plays-light.png',
        'shot_dark': '/assets/role-plays-dark.png',
        'shot_alt': ('Role Plays in use: two cards on screen labelled Student A and Student B, '
                     'each with a role and a short description.'),
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
            (CLOCK, 'Built-in timer',
             'Time each answer or the whole round, right from the toolbar.'),
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

/* The brand is the site's name; John wants it prominent, so the bar is sized
   around it rather than the other way about. --jpt-bar is the single source of
   truth: the tools pin their sidebars to it. */
:root{--jpt-bar:68px}
.stopbar{position:sticky;top:0;z-index:40;background:var(--card);
  border-bottom:1px solid var(--line);padding:0 24px;height:var(--jpt-bar);flex-shrink:0;
  display:flex;align-items:center;gap:14px}
.st-brand{display:inline-flex;align-items:center;gap:10px;text-decoration:none;
  color:var(--ink);line-height:1}
.st-brand .brand-icon{color:var(--accent);width:29px;height:29px;display:inline-flex;flex-shrink:0}
.st-brand .brand-icon svg{width:29px;height:29px}
.st-brand .brand-title{display:inline-flex;flex-direction:column;justify-content:center;gap:2px;line-height:1}
.brand-title{gap:3px}
.brand-title .k{font-size:10.5px;letter-spacing:.17em;text-transform:uppercase;color:var(--accent);font-weight:700}
.brand-title .b{font-size:20px;font-weight:800;letter-spacing:-.02em}
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
.brand-chev svg{width:16px;height:16px}
button.st-brand[aria-expanded="true"] .brand-chev{transform:rotate(180deg)}
.popmenu{position:absolute;top:calc(100% + 6px);left:0;z-index:60;min-width:246px;
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
.shell{min-height:calc(100vh - var(--jpt-bar))}
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
  .stopbar{padding:0 14px;gap:8px}
  button.st-brand{padding:6px;margin-left:-6px}
  .popmenu{min-width:210px}
  /* Collapse the topbar's labelled button to its icon rather than shrinking the
     brand. font-size:0 hides the text node, which no selector can reach. */
  .stopbar .btn{font-size:0;gap:0;padding:9px 11px}
  .stopbar .btn svg{width:17px;height:17px}
}
@media print{.tool-head,.popmenu,.stopbar{display:none!important}}
@media (prefers-reduced-motion:reduce){.popmenu{animation:none}}
/* Download-icon dropdown, shared by the tools. */
.icon-action{width:36px;height:36px;border-radius:999px;border:1px solid var(--soft-line);
  background:transparent;color:var(--muted);display:inline-flex;align-items:center;
  justify-content:center;cursor:pointer;transition:background .12s,color .12s,border-color .12s}
.icon-action:hover,.icon-action[aria-expanded="true"]{background:var(--soft);color:var(--accent);border-color:var(--accent)}
.icon-action svg{width:16px;height:16px;display:block}
.exp-wrap{position:relative;display:inline-flex}
.exp-menu{left:auto;right:0;min-width:190px}
/* Sidebar collapse handle, shared by every tool that has a sidebar, so the
   chevron on the divider looks and behaves the same everywhere. */
.app{--jpt-side-w:302px}
.app.side-collapsed{--jpt-side-w:0px}
.jpt-side-handle{position:fixed;top:152px;left:max(15px,var(--jpt-side-w));
  transform:translateX(-50%);z-index:39;margin:0;width:30px;height:30px;border-radius:999px;
  background:var(--card);border:1px solid var(--line);box-shadow:0 1px 4px rgba(15,27,45,.10);
  color:var(--muted);display:inline-flex;align-items:center;justify-content:center;cursor:pointer;
  transition:left .22s ease,background .12s,color .12s,border-color .12s}
[data-theme="dark"] .jpt-side-handle{box-shadow:0 1px 4px rgba(0,0,0,.35)}
.jpt-side-handle:hover{background:var(--soft);color:var(--accent);border-color:var(--accent)}
.jpt-side-handle:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.jpt-side-handle svg{width:15px;height:15px;transition:transform .22s ease}
.app.side-collapsed .jpt-side-handle svg{transform:rotate(180deg)}
@media (max-width:900px){.jpt-side-handle{display:none}}
@media print{.jpt-side-handle{display:none!important}}
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


PRESENT_BTN = (
    '<!-- jpt:present -->\n  <button class="btn" onclick="openFocusMode()" title="Present">\n'
    '    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<polygon points="5 3 19 12 5 21 5 3"/></svg>\n    Present\n  </button>\n  <!-- /jpt:present -->')

DOWNLOAD_I = svg('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
                 '<polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>')
FILE_I = svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
             '<polyline points="14 2 14 8 20 8"/>')
IMG_I = svg('<rect x="3" y="3" width="18" height="18" rx="2"/>'
            '<circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>')
PRINTER_I = svg('<polyline points="6 9 6 2 18 2 18 9"/>'
                '<path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>'
                '<rect x="6" y="14" width="12" height="8" rx="1"/>')


def export_menu(items, mid, title):
    """Reusable download-icon dropdown. items: list of (label, icon, onclick_js)."""
    lis = ''.join(
        '<a class="pm-item" role="menuitem" href="#" onclick="' + a + ';return false;">'
        '<span class="pm-ico">' + ic + '</span>' + lb + '</a>'
        for lb, ic, a in items)
    return ('<div class="exp-wrap">'
            '<button class="icon-action" id="' + mid + 'Btn" aria-haspopup="true" '
            'aria-expanded="false" aria-controls="' + mid + 'Menu" title="' + title + '" '
            'aria-label="' + title + '">' + DOWNLOAD_I + '</button>'
            '<div class="popmenu exp-menu" id="' + mid + 'Menu" role="menu" hidden>'
            '<div class="pm-label">Save</div>' + lis + '</div></div>')


SPEAKING_MENU = export_menu([
    ('Save as PNG', IMG_I, 'jptExportPNG()'),
    ('Save as PDF', FILE_I, 'exportPDF()'),
], 'jptSpk', 'Save this topic')

# Same rotate-ccw glyph as the timer's own reset button, so the two "undo"
# actions on this toolbar read as one family.
QUESTIONS_RESET_BTN = (
    '<button class="icon-action" onclick="jptQuestionsReset()" '
    'title="Reset all edited questions to the base wording" '
    'aria-label="Reset all edited questions to the base wording">'
    + svg('<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>')
    + '</button>')

DEBATE_MENU = export_menu([
    ('Save as PNG', IMG_I, 'exportPNG()'),
    ('Save as PDF', FILE_I, 'exportPDF()'),
    ('Print', PRINTER_I, 'window.print()'),
], 'jptDeb', 'Save this debate')

EXPORT_MENU_JS = """<!-- jpt:exportmenu -->
<script>
(function () {
  Array.prototype.forEach.call(document.querySelectorAll('.exp-wrap'), function (wrap) {
    var btn = wrap.querySelector('.icon-action'), menu = wrap.querySelector('.exp-menu');
    if (!btn || !menu) return;
    function close(){ if(menu.hidden) return; menu.hidden = true; btn.setAttribute('aria-expanded','false'); }
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (menu.hidden) { menu.hidden = false; btn.setAttribute('aria-expanded','true'); } else close();
    });
    menu.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('[role=menuitem]')) close(); });
    document.addEventListener('click', function (e) { if (!menu.hidden && !wrap.contains(e.target)) close(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !menu.hidden) { close(); btn.focus(); } });
  });
})();
</script>
<!-- /jpt:exportmenu -->
"""

SPEAKING_PNG_JS = """<!-- jpt:speakingpng -->
<script>
(function () {
  window.jptExportPNG = function () {
    if (typeof currentTopicIdx==='undefined' || currentTopicIdx===null){ alert('Pick a topic first.'); return; }
    var t = topics[currentTopicIdx], data = t[currentLevel];
    function render(){
      var SC=2, W=860, PAD=56, colW=W-PAD*2, LH=25;
      var c=document.createElement('canvas'), x=c.getContext('2d');
      function F(px,w){ x.font=(w||'400')+' '+px+'px Outfit,-apple-system,BlinkMacSystemFont,sans-serif'; }
      function wrap(txt,maxw){ var ws=txt.split(' '),ls=[],cur=''; for(var i=0;i<ws.length;i++){ var tt=cur?cur+' '+ws[i]:ws[i]; if(x.measureText(tt).width>maxw&&cur){ls.push(cur);cur=ws[i];}else cur=tt; } if(cur)ls.push(cur); return ls; }
      var rows=[];
      rows.push({k:'title',text:t.name});
      rows.push({k:'sub',text:currentLevel.charAt(0).toUpperCase()+currentLevel.slice(1)+' level'});
      function section(label,color,qs,start){
        rows.push({k:'section',text:label,color:color});
        qs.forEach(function(q,i){
          F(17,'700'); var num=String(start+i), numW=x.measureText(num).width+14;
          F(17,'400'); rows.push({k:'q',num:num,numW:numW,lines:wrap(q,colW-numW),color:color});
        });
      }
      section('PERSONAL','#2563eb',data.personal,1);
      section('THOUGHT-PROVOKING','#6b7686',data.thought,6);
      rows.push({k:'foot',text:'johnplustools.com'});
      var Y=PAD;
      rows.forEach(function(r){
        if(r.k==='title'){r.y=Y;Y+=42;}
        else if(r.k==='sub'){r.y=Y;Y+=34;}
        else if(r.k==='section'){Y+=16;r.y=Y;Y+=28;}
        else if(r.k==='q'){r.y=Y;Y+=r.lines.length*LH+12;}
        else if(r.k==='foot'){Y+=22;r.y=Y;Y+=24;}
      });
      var H=Y+PAD-12;
      c.width=W*SC; c.height=H*SC; x.scale(SC,SC);
      x.fillStyle='#ffffff'; x.fillRect(0,0,W,H);
      x.textBaseline='alphabetic';
      rows.forEach(function(r){
        if(r.k==='title'){ F(30,'800'); x.fillStyle='#0f1b2d'; x.fillText(r.text,PAD,r.y+30); }
        else if(r.k==='sub'){ F(14,'500'); x.fillStyle='#6b7686'; x.fillText(r.text,PAD,r.y+16); }
        else if(r.k==='section'){ x.fillStyle=r.color;
          x.beginPath(); x.arc(PAD+4,r.y+8,4,0,Math.PI*2); x.fill();
          F(12.5,'700'); if('letterSpacing' in x) x.letterSpacing='2px';
          x.fillText(r.text,PAD+16,r.y+13); if('letterSpacing' in x) x.letterSpacing='0px';
        }
        else if(r.k==='q'){ F(17,'700'); x.fillStyle=r.color; x.fillText(r.num,PAD,r.y+17);
          F(17,'400'); x.fillStyle='#0f1b2d';
          r.lines.forEach(function(ln,i){ x.fillText(ln,PAD+r.numW,r.y+17+i*LH); });
        }
        else if(r.k==='foot'){ F(12,'600'); x.fillStyle='#98a1b0'; x.fillText(r.text,PAD,r.y+12); }
      });
      c.toBlob(function(b){
        var a=document.createElement('a');
        a.href=URL.createObjectURL(b);
        a.download=t.name.replace(/[^a-z0-9]+/gi,'-').toLowerCase().replace(/^-|-$/g,'')+'-'+currentLevel+'.png';
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(function(){ URL.revokeObjectURL(a.href); },1500);
      },'image/png');
    }
    if(document.fonts&&document.fonts.ready) document.fonts.ready.then(render); else render();
  };
})();
</script>
<!-- /jpt:speakingpng -->
"""


TIMER_HTML = (
    '<div class="timer" id="jptTimerBox">'
    '<input class="tm" id="jptTmInput" type="text" inputmode="numeric" value="02:00" '
    'aria-label="Timer length" title="Type a length (2 or 2:30) and press Enter to start" '
    'onfocus="jptTmFocus()" onkeydown="jptTmKey(event)" onblur="jptTmApply()">'
    '<button onclick="jptTmToggle()" id="jptTmBtn" title="Start / pause"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="7 4 20 12 7 20 7 4"/></svg></button>'
    '<button onclick="jptTmReset()" title="Reset" aria-label="Reset timer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg></button></div>')

TIMER_JS = """<!-- jpt:timerjs -->
<script>
/* Self-contained MM:SS timer, modelled on the Debate Builder's: type a length,
   Enter starts it, the input shows the countdown. Namespaced so it does not
   touch the tool's own (now removed) preset timer. */
(function () {
  var total = 120, remaining = 120, running = false, iv = null;
  function fmt(s){var n=s<0;s=Math.abs(s);return (n?'-':'')+String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}
  function parse(str){str=String(str).trim().replace(/\s*min(ute)?s?$/i,'');if(!str)return null;var t;
    if(str.indexOf(':')>=0){var pp=str.split(':');var m=parseInt(pp[0],10)||0;var sc=parseInt(pp[1],10)||0;if(sc>59)return null;t=m*60+sc;}
    else{var mn=parseFloat(str);if(!isFinite(mn))return null;t=Math.round(mn*60);}
    if(!isFinite(t)||t<=0)return null;return Math.min(t,99*60+59);}
  function box(){return document.getElementById('jptTimerBox');}
  function paint(){var input=document.getElementById('jptTmInput');if(!input)return;
    var txt=fmt(remaining);if(document.activeElement!==input)input.value=txt;
    var warn=remaining<=60&&remaining>0,over=remaining<=0;
    box().classList.toggle('warn',warn);box().classList.toggle('over',over);
    var bar=document.getElementById('jptTmBar');
    if(bar){bar.classList.toggle('on',running||remaining<total||over);
      bar.classList.toggle('warn',warn);bar.classList.toggle('over',over);
      document.getElementById('jptTmBarFill').style.width=(over?100:Math.max(0,Math.min(1,remaining/total))*100)+'%';}
    var _P='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="7 4 20 12 7 20 7 4"/></svg>';
    var _PA='<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="4.5" width="4" height="15" rx="1"/><rect x="14" y="4.5" width="4" height="15" rx="1"/></svg>';
    document.getElementById('jptTmBtn').innerHTML=running?_PA:_P;}
  window.jptTmFocus=function(){if(running)window.jptTmToggle();var el=document.getElementById('jptTmInput');requestAnimationFrame(function(){el.select();});};
  window.jptTmApply=function(){var el=document.getElementById('jptTmInput');var v=parse(el.value);if(v===null){paint();return false;}total=v;remaining=v;paint();return true;};
  window.jptTmKey=function(e){if(e.key==='Enter'){e.preventDefault();if(window.jptTmApply()&&!running)window.jptTmToggle();e.target.blur();}else if(e.key==='Escape'){e.preventDefault();paint();e.target.blur();}};
  window.jptTmToggle=function(){running=!running;clearInterval(iv);if(running)iv=setInterval(function(){remaining--;paint();},1000);paint();};
  window.jptTmReset=function(){remaining=total;running=false;clearInterval(iv);paint();};
  paint();
})();
</script>
<!-- /jpt:timerjs -->
"""



SIDE_JS = """<!-- jpt:sidejs -->
<script>
(function () {
  var app = document.getElementById('app'), btn = document.getElementById('jptSideToggle');
  if (!app || !btn) return;
  var KEY = 'jpt_speaking_side_collapsed';
  function apply(c){ app.classList.toggle('side-collapsed', c);
    btn.setAttribute('aria-expanded', c ? 'false' : 'true');
    var lbl = (c ? 'Show' : 'Hide') + ' the topic list';
    btn.title = lbl; btn.setAttribute('aria-label', lbl); }
  window.jptToggleSide = function(){ var c = !app.classList.contains('side-collapsed');
    apply(c); try { localStorage.setItem(KEY, c ? '1' : '0'); } catch(e){} };
  var saved; try { saved = localStorage.getItem(KEY); } catch(e){}
  if (saved === '1') apply(true);
})();
</script>
<!-- /jpt:sidejs -->
"""


PHRASES_JS = """<!-- jpt:phrasesjs -->
<script>
(function () {
  var KEY = 'jpt_speaking_phrases_v3', LKEY = 'jpt_speaking_phrase_level';
  var DEFAULTS = {
    simple: ["I think\u2026", "For me, \u2026", "I'd say\u2026", "In my case, \u2026",
      "I like it because\u2026", "The main reason is\u2026", "For example, \u2026", "It depends.",
      "To be honest, \u2026", "I'm not sure, but\u2026", "That's a good point.", "I feel the same way."],
    advanced: ["I suppose it comes down to\u2026", "There are two sides to this.",
      "I can see it both ways.", "It's not that simple, really.", "If I'm being honest, \u2026",
      "It depends on how you look at it.", "That said, \u2026", "At the end of the day, \u2026",
      "There's a case for both.", "It's a bit of a grey area.", "What matters most to me is\u2026",
      "I'd rather not generalise, but\u2026"]
  };
  var data, cur;
  function clone(o){ return { simple:o.simple.slice(), advanced:o.advanced.slice() }; }
  function load(){ try { var r = localStorage.getItem(KEY); if (r) { var o = JSON.parse(r);
    if (o && o.simple && o.advanced) return o; } } catch(e){} return clone(DEFAULTS); }
  function save(){ try { localStorage.setItem(KEY, JSON.stringify(data)); } catch(e){} }
  function esc(x){ return String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function render(){
    var el = document.getElementById('jptPhraseList'); if (!el) return;
    el.innerHTML = data[cur].map(function (p, i) {
      return '<div class="ph-row"><span class="ph-text" contenteditable="true" data-i="' + i + '">'
        + esc(p) + '</span><button class="ph-x" data-i="' + i + '" title="Remove" aria-label="Remove phrase">\u00d7</button></div>';
    }).join('');
    Array.prototype.forEach.call(document.querySelectorAll('.ph-flip-btn'), function (b) {
      b.classList.toggle('on', b.dataset.lvl === cur);
    });
  }
  window.jptPhraseFlip = function (lvl) { cur = (lvl === 'advanced') ? 'advanced' : 'simple';
    try { localStorage.setItem(LKEY, cur); } catch(e){} render(); };
  window.jptPhraseAdd = function () { data[cur].push(''); save(); render();
    var r = document.querySelectorAll('#jptPhraseList .ph-text'); var last = r[r.length-1]; if (last) last.focus(); };
  window.jptPhrasesReset = function () { if (!confirm('Reset the phrases to the defaults?')) return; data = clone(DEFAULTS); save(); render(); };
  document.addEventListener('input', function (e) {
    var t = e.target; if (t && t.classList && t.classList.contains('ph-text')) { data[cur][+t.dataset.i] = t.textContent; save(); }
  });
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.ph-x'); if (b) { data[cur].splice(+b.dataset.i, 1); save(); render(); }
  });
  data = load();
  try { cur = localStorage.getItem(LKEY) === 'advanced' ? 'advanced' : 'simple'; } catch(e){ cur = 'simple'; }
  render();
})();
</script>
<!-- /jpt:phrasesjs -->
"""

QUESTIONS_JS = """<!-- jpt:questionsjs -->
<script>
(function () {
  var QKEY = 'jpt_speaking_questions_v1';
  var over = {};
  try {
    var raw = localStorage.getItem(QKEY);
    if (raw) over = JSON.parse(raw) || {};
  } catch (e) { over = {}; }
  window.jptQEsc = function (s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  };
  window.jptQOverride = function (topicIdx, level, cat, i, base) {
    var k = topicIdx + ':' + level + ':' + cat + ':' + i;
    return Object.prototype.hasOwnProperty.call(over, k) ? over[k] : base;
  };
  window.jptQSave = function (topicIdx, level, cat, i, base, text) {
    var k = topicIdx + ':' + level + ':' + cat + ':' + i;
    text = text.trim();
    if (!text || text === base) { delete over[k]; } else { over[k] = text; }
    try { localStorage.setItem(QKEY, JSON.stringify(over)); } catch (e) {}
  };
  window.jptQuestionsReset = function () {
    if (!confirm('Reset all edited questions back to the original wording?')) return;
    over = {};
    try { localStorage.removeItem(QKEY); } catch (e) {}
    if (typeof renderDeck === 'function' && typeof currentTopicIdx !== 'undefined' && currentTopicIdx !== null) renderDeck();
  };
})();
</script>
<!-- /jpt:questionsjs -->
"""


def drop(html, tag):
    return re.sub(rf'<!-- {tag} -->.*?<!-- /{tag} -->\n?\s*', '', html, flags=re.S)


def strip_marks(html):
    for tag in ('jpt:brand', 'jpt:toolsnav', 'jpt:sidefoot', 'jpt:toolhead', 'jpt:debateslabel',
                'jpt:homeview', 'jpt:router', 'jpt:backlink', 'jpt:menujs', 'jpt:themejs',
                'jpt:themebtn', 'jpt:themeboot', 'jpt:strip',
                'jpt:present', 'jpt:timerjs', 'jpt:export', 'jpt:exportjs',
                'jpt:exportmenu', 'jpt:speakingpng', 'jpt:sidejs', 'jpt:phrasesjs', 'jpt:questionsjs',
                'jpt:seed'):
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
aside{top:var(--jpt-bar);height:calc(100vh - var(--jpt-bar))}
.app{min-height:calc(100vh - var(--jpt-bar))}

/* ── Sidebar, restyled to match Speaking Topics ────────────────────────
   Debates grouped by level into collapsible sections with coloured caps
   headers (B1 orange, B2 green, C1 blue, C2 purple, so the level is
   readable at a glance without a per-item badge). Each item drops the
   level badge and just carries its title + date/prompt count. */
.lvl-filter{display:none}
.side-list{padding:2px 10px 16px}
.side-group{margin-bottom:6px}
.side-group-toggle{display:flex;align-items:center;gap:8px;cursor:pointer;width:100%;
  padding:7px 10px;border-radius:9px;background:transparent;transition:background .12s}
.side-group-toggle:hover{background:var(--soft)}
.side-group-name{flex:1;font-size:11px;letter-spacing:.13em;text-transform:uppercase;
  font-weight:700;color:var(--accent)}
/* Level scale kept in the blue family (John's call — no orange/green/purple):
   B1 lightest → C2 deepest, matching LEVEL_COLOURS below. Shifted up in
   luminance for dark mode so all four still read on the navy background. */
.side-group.lvl-B1 .side-group-name{color:#6b8cd6}
.side-group.lvl-B2 .side-group-name{color:#3b6ec4}
.side-group.lvl-C1 .side-group-name{color:#2563eb}
.side-group.lvl-C2 .side-group-name{color:#1e3a8a}
[data-theme="dark"] .side-group.lvl-B1 .side-group-name{color:#b8d4f7}
[data-theme="dark"] .side-group.lvl-B2 .side-group-name{color:#8fb3e8}
[data-theme="dark"] .side-group.lvl-C1 .side-group-name{color:#5b8def}
[data-theme="dark"] .side-group.lvl-C2 .side-group-name{color:#7ba4de}
.side-group-chevron{font-size:9px;color:var(--muted);transition:transform .18s ease}
.side-group.open .side-group-chevron{transform:rotate(180deg)}
.side-group-body{display:none;padding:2px 0 4px}
.side-group.open .side-group-body{display:block}
/* Item styling — brought in line with Speaking Topics' .topic-btn (padding,
   radius, spacing, font weight/size) so the two sidebars read as one family.
   Also normalises the delete affordance's position to fit the tighter row. */
.side-item{padding:8px 11px;border-radius:10px;margin-bottom:2px}
.side-item.active{background:var(--soft);border-color:var(--accent)}
.side-item .title{font-size:13.5px;font-weight:600;letter-spacing:-.01em;
  text-transform:capitalize}
.side-item .del{top:6px;right:4px;font-size:12px}
/* /jpt:speaking */
'''

SPEAKING_CSS = '''
/* jpt:speaking */
/* Map the tool's palette onto the site tokens. Its own CSS keeps referring to
   its variable names, so it inherits both themes without editing its rules. */
:root{
  --cream:var(--bg); --border:var(--line); --sky:var(--accent); --sky-light:var(--soft);
  --radius:14px;
  --shadow-sm:0 1px 3px rgba(20,30,60,.06);
  --shadow-md:0 4px 12px rgba(20,30,60,.08);
}
[data-theme="dark"]{
  --shadow-sm:0 1px 3px rgba(0,0,0,.35);
  --shadow-md:0 4px 12px rgba(0,0,0,.45);
  --sun:#f0b866; --sea:#4fd8bd; --coral:#ff8585; --lavender:#b391dd; --mint:#7ae2b4;
  --sand:#2a2418;
}
body{background:var(--bg);color:var(--ink);margin:0}
/* John dislikes the monospace the tool used for labels and numbers. Put every
   one of them back on the site font. */
.section-label,.deck-level-pill,.deck-section-label,.q-num,.timer-display,
.deck-counter,.sr-topic,.focus-topic,.focus-type,.focus-counter,
.roulette-topic,.topic-group-count{
  font-family:"Outfit",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}

/* John's call: no purple accent on Thought-provoking (was var(--lavender)
   throughout), and no divider line between questions. */
.label-thought{color:var(--muted)}
.dot-thought{background:var(--muted)}
.q-item.thought .q-num{color:var(--muted)}
.focus-type.thought{background:var(--soft);color:var(--muted)}
.q-item{border-bottom:none}
/* flex:1 so the text span fills the whole row after the number, leaving no
   gap of empty .q-item space that would cross the question out instead of
   focusing it to edit — the two click zones need a hard edge between them. */
.q-text{cursor:text;border-radius:6px;padding:1px 4px;margin:-1px -4px;flex:1;min-width:0}
.q-text:focus{outline:none;background:var(--soft);box-shadow:inset 0 0 0 1px var(--soft-line)}

/* ── Shell, matching the Debate Builder ──────────────────────────────── */
.app{display:grid;grid-template-columns:var(--jpt-side-w,302px) 1fr;
  min-height:calc(100vh - var(--jpt-bar));transition:grid-template-columns .22s ease}
.app.side-collapsed > aside{border-right:none;overflow:hidden;opacity:0;pointer-events:none}
.app > aside{background:var(--card);border-right:1px solid var(--line);display:flex;
  flex-direction:column;overflow-y:auto;position:sticky;top:var(--jpt-bar);
  height:calc(100vh - var(--jpt-bar))}
main{overflow:visible;min-width:0}
.side-top{padding:16px 16px 12px;border-bottom:1px solid var(--line);
  position:sticky;top:0;background:var(--card);z-index:2}
.side-list{padding:10px 10px 16px}
.jt-label{font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--muted);font-weight:700;margin-bottom:9px}

/* ── Search: the first thing in the sidebar ──────────────────────────── */
.search-wrap{position:relative;margin-bottom:10px}
.search-input{width:100%;font-family:inherit;font-size:14px;padding:9px 12px 9px 34px;
  border-radius:999px;border:1px solid var(--soft-line);background:var(--bg);
  color:var(--ink);outline:none;transition:border-color .15s}
.search-input:focus{border-color:var(--accent)}
.search-input::placeholder{color:var(--muted)}
.search-wrap::before{content:"";position:absolute;left:12px;top:50%;width:14px;height:14px;
  transform:translateY(-50%);pointer-events:none;opacity:.55;
  background:currentColor;color:var(--muted);
  -webkit-mask:var(--search-ico) center/14px no-repeat;mask:var(--search-ico) center/14px no-repeat}
.search-results{margin-top:10px;display:none;background:transparent;border:none;
  box-shadow:none;position:static;max-height:none;overflow:visible;border-radius:0}
.search-results.show{display:block}
.sr-count{padding:2px 2px 8px;font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  font-weight:700;color:var(--muted)}
/* Stacked, not side by side: at 302px a nowrap label leaves the question a
   one-word column. */
.sr-item{display:block;padding:9px 11px;border-radius:10px;border:1px solid transparent;
  border-bottom:none;cursor:pointer;margin-bottom:3px;transition:background .12s,border-color .12s}
.sr-item:hover{background:var(--soft);border-color:var(--soft-line)}
.sr-topic{display:block;min-width:0;white-space:normal;padding-top:0;font-family:inherit;
  font-size:10px;letter-spacing:.11em;text-transform:uppercase;font-weight:700;
  color:var(--accent);margin-bottom:3px}
.sr-q{display:block;font-size:13px;line-height:1.5;color:var(--ink)}
.sr-item mark{background:var(--soft);color:var(--accent);font-weight:700;
  border-radius:4px;padding:0}

/* ── Level toggle, as filter pills ───────────────────────────────────── */
.level-toggle{display:flex;gap:5px;background:transparent;border:none;padding:0}
.level-btn{font-family:inherit;font-size:11.5px;font-weight:700;letter-spacing:.03em;
  padding:5px 12px;border-radius:999px;cursor:pointer;
  border:1px solid var(--soft-line);background:var(--card);color:var(--muted);
  transition:background .12s,color .12s,border-color .12s}
.level-btn:hover{color:var(--accent);border-color:var(--accent)}
.level-btn.on{background:var(--accent);border-color:var(--accent);color:#fff}

/* ── Topic list down the sidebar ─────────────────────────────────────── */
#topicGrid{display:block}
.topic-group{margin-bottom:6px;background:transparent;border:none;box-shadow:none}
.topic-group-toggle{display:flex;align-items:center;gap:8px;cursor:pointer;width:100%;
  padding:7px 10px;border-radius:9px;background:transparent;border:none;box-shadow:none;
  transition:background .12s}
.topic-group-toggle:hover{background:var(--soft);box-shadow:none}
.topic-group.open .topic-group-toggle{border-radius:9px;border:none}
.topic-group-name{flex:1;font-size:11px;letter-spacing:.13em;text-transform:uppercase;
  font-weight:700;color:var(--accent)}
.topic-group-count{display:none}
.topic-group-chevron{font-size:9px;color:var(--muted);transition:transform .18s ease}
.topic-group.open .topic-group-chevron{transform:rotate(180deg)}
.topic-group-body{display:none;padding:2px 0 8px;background:transparent;border:none;
  border-radius:0}
.topic-group.open .topic-group-body{display:block}
.topic-grid{display:flex;flex-direction:column;gap:2px}
.topic-btn{display:flex;align-items:center;gap:8px;width:100%;text-align:left;
  font-family:inherit;font-size:13.5px;
  font-weight:600;letter-spacing:-.01em;padding:8px 11px;border-radius:10px;cursor:pointer;
  border:1px solid transparent;background:transparent;color:var(--ink);
  transition:background .12s,border-color .12s}
.topic-btn svg{flex-shrink:0;width:15px;height:15px}
/* Same TOPIC_ICONS markup as the sidebar, sized/coloured for the question
   card's header instead (this used to be one hardcoded chat-bubble icon). */
.deck-topic svg{width:18px;height:18px;flex-shrink:0;color:var(--sky)}
.topic-btn:hover{background:var(--soft)}
.topic-btn.active,.topic-btn.on,.topic-btn[aria-pressed="true"]{
  background:var(--soft);border-color:var(--accent);color:var(--accent)}

/* ── Main pane ───────────────────────────────────────────────────────── */
.main-inner{padding:20px 24px 40px;max-width:1180px;margin:0 auto}
.toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:18px;
  padding-bottom:14px;border-bottom:1px solid var(--line)}
.toolbar .status{font-size:11px;color:var(--muted);letter-spacing:.14em;
  text-transform:uppercase;font-weight:700;margin-right:auto}
.action-btn{font-family:inherit;font-size:13px;font-weight:600;padding:8px 14px;
  border-radius:999px;cursor:pointer;display:inline-flex;align-items:center;gap:7px;
  background:transparent;color:var(--muted);border:1px solid var(--soft-line);
  transition:background .12s,color .12s,border-color .12s;white-space:nowrap}
.action-btn:hover{background:var(--soft);color:var(--accent);border-color:var(--accent)}
.action-btn svg{width:14px;height:14px;flex-shrink:0}

/* Present button (topbar), matching the Debate Builder's. The chrome media
   query collapses .stopbar .btn to its icon on a phone. */
.btn{font-family:inherit;font-size:13px;font-weight:600;padding:8px 14px;border-radius:999px;
  border:1px solid transparent;background:var(--accent);color:#fff;cursor:pointer;
  display:inline-flex;align-items:center;gap:7px;white-space:nowrap;transition:background .15s}
.btn:hover{background:var(--accent-deep)}
.btn svg{width:14px;height:14px;flex-shrink:0}

/* Timer, a typed MM:SS control like the Debate Builder's, not preset pills. */
.timer{display:inline-flex;align-items:center;gap:2px;padding:3px 4px 3px 12px;
  border:1px solid var(--soft-line);border-radius:999px;background:var(--card)}
.timer .tm{font-family:inherit;font-size:14px;font-weight:700;font-variant-numeric:tabular-nums;
  letter-spacing:.04em;width:58px;text-align:center;padding:2px 0;background:transparent;
  border:none;outline:none;color:var(--ink)}
.timer .tm:focus{background:var(--soft);color:var(--accent);border-radius:8px}
.timer.warn .tm{color:#c2740c}
.timer.over .tm{color:#c14343}
.timer button{width:28px;height:28px;border-radius:999px;border:none;background:transparent;
  color:var(--muted);display:inline-flex;align-items:center;justify-content:center;
  cursor:pointer;transition:background .12s,color .12s}
.timer button svg{width:15px;height:15px;display:block}
/* The deck card's tool row is empty now that its buttons moved. */
.deck-toolbar:empty{display:none}
.timer button:hover{background:var(--soft);color:var(--accent)}
/* A mouse click left a big focus ring on play, so it dwarfed the reset. Drop it
   for pointer focus; keep a ring for keyboard users. */
.timer button:focus{outline:none}
.timer button:focus-visible{outline:2px solid var(--accent);outline-offset:1px}

/* The long progress bar under the toolbar, like the Debate Builder's: fills red
   once time is up rather than vanishing to nothing. Hidden until the timer is
   armed. */
.jpt-tmbar{height:4px;border-radius:999px;background:var(--line);overflow:hidden;
  margin:-4px 0 18px;opacity:0;transition:opacity .25s}
.jpt-tmbar.on{opacity:1}
.jpt-tmbar span{display:block;height:100%;width:100%;background:var(--accent);
  border-radius:999px;transition:width .95s linear,background .3s}
.jpt-tmbar.warn span{background:#c2740c}
.jpt-tmbar.over span{background:#c14343;animation:jptTmPulse 1.1s ease-in-out infinite}
@keyframes jptTmPulse{0%,100%{opacity:1}50%{opacity:.55}}

/* Questions */
.placeholder{background:var(--card);border:1px dashed var(--line);border-radius:16px;
  padding:48px 24px;text-align:center;color:var(--muted);font-size:.95rem}
.deck{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
/* Questions no longer span the full width: they share the pane with an editable
   Useful phrases panel, the way the Debate Builder has its phrase bank. */
.deck-row{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:18px;align-items:start}
.deck-col{min-width:0}
/* Bring the tool's own Simple/Advanced toggle onto the same register as the
   phrases panel's star flipper: same border, same transparent-vs-ink colours,
   same height (padding matches, line-height stands in for the star icon's
   13px box), so the two toggles read as one family across the two cards. */
.deck-level-toggle{border:1.5px solid var(--soft-line);border-radius:9px}
.deck-level-pill{background:transparent;color:var(--muted);padding:5px 12px;line-height:13px}
.deck-level-pill.on{background:var(--ink);color:var(--card)}
.phrases-panel{background:var(--card);border:1px solid var(--line);border-radius:16px;
  padding:16px 16px 14px;box-shadow:var(--shadow-card);
  position:sticky;top:calc(var(--jpt-bar) + 18px)}
/* min-height matches .deck-topic's rendered height (icon + 1.2rem bold text),
   so this row centres on the same line as .deck-header's: both toggles then
   land at an identical offset from their card's top instead of the flipper
   sitting 2-3px higher (its own row has nothing taller than it to centre on). */
.ph-head{display:flex;align-items:center;gap:8px;margin-bottom:14px;min-height:31px}
.ph-flip{display:inline-flex;flex-shrink:0;border:1.5px solid var(--soft-line);border-radius:9px;
  overflow:hidden}
.ph-flip-btn{font-family:inherit;padding:5px 10px;border:none;background:transparent;
  color:var(--muted);cursor:pointer;display:inline-flex;align-items:center;gap:3px;
  transition:background .12s,color .12s}
.ph-flip-btn+.ph-flip-btn{border-left:1.5px solid var(--soft-line)}
.ph-flip-btn:hover{color:var(--ink)}
.ph-flip-btn.on{background:var(--ink);color:var(--card)}
.ph-flip-btn svg{width:13px;height:13px;display:block}
/* Alternate the phrases by colour, like the debate phrase bank. */
.ph-row:nth-of-type(even) .ph-text{color:var(--accent)}
.ph-title{flex:1;font-size:11px;letter-spacing:.14em;text-transform:uppercase;font-weight:700;color:var(--muted)}
.ph-reset{font-family:inherit;font-size:11px;font-weight:700;color:var(--muted);background:transparent;
  border:none;cursor:pointer;padding:2px 5px;border-radius:6px}
.ph-reset:hover{color:var(--accent);background:var(--soft)}
.ph-list{display:flex;flex-direction:column;gap:2px}
.ph-row{display:flex;align-items:flex-start;gap:4px;border-radius:9px}
.ph-row:hover{background:var(--soft)}
.ph-text{flex:1;font-size:13.5px;line-height:1.5;color:var(--ink);font-style:italic;
  padding:5px 8px;border-radius:8px;outline:none;cursor:text;min-width:0}
.ph-text:focus{background:var(--bg);box-shadow:inset 0 0 0 1px var(--soft-line);font-style:normal}
.ph-text:empty::before{content:'New phrase\2026';color:var(--muted);font-style:normal}
.ph-x{opacity:0;flex-shrink:0;width:22px;height:26px;border:none;background:transparent;
  color:var(--muted);cursor:pointer;border-radius:6px;font-size:16px;line-height:1}
.ph-row:hover .ph-x{opacity:.55}
.ph-x:hover{opacity:1;color:#c14343}
.ph-add{margin-top:7px;width:100%;font-family:inherit;font-size:12.5px;font-weight:600;
  color:var(--accent);background:transparent;border:1px dashed var(--soft-line);
  border-radius:9px;padding:8px;cursor:pointer;transition:.12s}
.ph-add:hover{background:var(--soft);border-color:var(--accent)}
.ph-note{margin:10px 2px 0;font-size:11px;line-height:1.5;color:var(--muted)}
@media (max-width:900px){.deck-row{grid-template-columns:1fr}.phrases-panel{position:static}}
.deck-nav{display:flex;align-items:center;gap:10px;margin-top:18px}
.deck-counter{font-size:11px;letter-spacing:.14em;text-transform:uppercase;
  font-weight:700;color:var(--muted);margin:0 auto}
.nav-btn{font-family:inherit;font-size:13px;font-weight:600;padding:8px 14px;
  border-radius:999px;cursor:pointer;background:transparent;color:var(--muted);
  border:1px solid var(--soft-line);transition:.12s}
.nav-btn:hover{background:var(--soft);color:var(--accent);border-color:var(--accent)}
.nav-btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.nav-btn.primary:hover{background:var(--accent-deep);color:#fff}

/* Student picker, as a card */
.name-picker{background:var(--card);border:1px solid var(--line);border-radius:16px;
  padding:20px 22px;margin-top:22px;box-shadow:var(--shadow-card)}
.name-picker-title{font-size:11px;letter-spacing:.14em;text-transform:uppercase;
  font-weight:700;color:var(--muted)}
.name-input{font-family:inherit;font-size:14px;padding:9px 13px;border-radius:999px;
  border:1px solid var(--soft-line);background:var(--bg);color:var(--ink);outline:none}
.name-input:focus{border-color:var(--accent)}
.name-add-btn,.name-pick-btn{font-family:inherit;font-weight:700;cursor:pointer;
  border-radius:999px;border:1px solid transparent;background:var(--accent);color:#fff}
.name-add-btn{font-size:13px;padding:9px 18px}
.name-pick-btn{font-size:13px;padding:10px 18px;background:transparent;color:var(--accent);
  border-color:var(--accent);width:100%;display:inline-flex;align-items:center;
  justify-content:center;gap:7px}
.name-pick-btn:hover{background:var(--accent);color:#fff}
.name-add-btn:hover{background:var(--accent-deep)}

/* Overlays sit above the topbar, as the Debate Builder's presentation does. */
.focus-overlay,.roulette-overlay{z-index:200}

@media (max-width:900px){
  .app{grid-template-columns:1fr}
  aside{position:static;height:auto;max-height:46vh;border-right:none;
    border-bottom:1px solid var(--line)}
  .main-inner{padding:16px 14px 34px}
  .deck{grid-template-columns:1fr}
}
/* /jpt:speaking */
'''


# Seed debates for the Debate Builder — one-shot, only ever runs if the user
# has no meaningful debates yet. Level-adjusted (B1 concrete/personal → C2
# nuanced/abstract), four per level, matching the tool's own shape (5-bubble
# option set with a framing question and a "choose two" task). The bank field
# is filled in by the tool's own migrate() at load, so it's omitted here.
_DEBATES = []
def _dbt(level, title, question, task, bubbles):
    _DEBATES.append({'level': level, 'title': title, 'question': question,
                      'task': task, 'bubbles': bubbles})

# B1 — everyday, concrete, personal preference
_dbt('B1', 'FREE TIME',
     'How do people spend their free time?',
     'Which two are best for you?',
     ['watching TV', 'playing sports', 'meeting friends',
      'using social media', 'reading books'])
_dbt('B1', 'HEALTHY EATING',
     'What makes a meal healthy?',
     'Which two matter most?',
     ['lots of vegetables', 'small portions', 'no sugar',
      'cooked at home', 'plenty of water'])
_dbt('B1', 'LEARNING ENGLISH',
     'How do people improve their English?',
     'Which two work best?',
     ['watching films', 'speaking every day', 'reading books',
      'using apps', 'studying grammar'])
_dbt('B1', 'A GOOD HOLIDAY',
     'What makes a good holiday?',
     'Which two matter most?',
     ['sunny weather', 'good food', 'cheap prices',
      'safe places', 'exciting activities'])

# B2 — broader social themes, some abstraction
_dbt('B2', 'SOCIAL MEDIA',
     'Why do people use social media so much?',
     'Which two are the strongest reasons?',
     ['staying in touch', 'fear of missing out', 'entertainment',
      'work and business', 'sharing photos'])
_dbt('B2', 'WORK-LIFE BALANCE',
     'What makes it hard to switch off from work?',
     'Which two are hardest to fix?',
     ['emails on our phones', 'long working hours', 'financial pressure',
      'loving the job', 'fear of losing it'])
_dbt('B2', 'CITY LIVING',
     'Why do so many people move to cities?',
     'Which two matter most?',
     ['better jobs', 'easier transport', 'more entertainment',
      'better healthcare', 'meeting new people'])
_dbt('B2', 'LEARNING A NEW SKILL',
     'What stops adults from learning something new?',
     'Which two are hardest to overcome?',
     ['no time', 'feeling too old', 'no money',
      'fear of failing', 'no clear reason to'])

# C1 — nuanced, analytical
_dbt('C1', 'TRUST IN THE NEWS',
     'Why has it become harder to trust the news?',
     'Which two damage trust the most?',
     ['bias in reporting', 'noise on social media', 'deepfakes and AI',
      'political interference', 'anyone can publish'])
_dbt('C1', 'MONEY AND HAPPINESS',
     'How much does money really buy happiness?',
     'Which two matter most?',
     ['it pays for security', 'it buys free time', 'it opens experiences',
      'it protects against illness', 'only up to a point'])
_dbt('C1', 'THE FUTURE OF WORK',
     'How will work change over the next twenty years?',
     'Which two shifts are most likely?',
     ['AI replacing tasks', 'remote work by default', 'four-day weeks',
      'growth of the gig economy', 'later retirement'])
_dbt('C1', 'MODERN RELATIONSHIPS',
     'Why are people delaying marriage?',
     'Which two are the strongest reasons?',
     ['prioritising careers', 'financial worries', 'dating-app culture',
      'changing values', 'watching others divorce'])

# C2 — philosophical, high abstraction
_dbt('C2', 'FREEDOM OF SPEECH',
     'Where should the line on free speech be drawn?',
     'Which two, if any, should genuinely be limited?',
     ['incitement to violence', 'hate speech against groups',
      'health misinformation', 'offensive humour', 'criticism of institutions'])
_dbt('C2', 'AI AND CREATIVITY',
     'Can AI ever be genuinely creative?',
     'Which two arguments are strongest?',
     ['copying is not creating', 'novelty from randomness',
      'humans invented the tool', 'art needs intention',
      'we can’t define creativity ourselves'])
_dbt('C2', 'INHERITED INEQUALITY',
     'What most entrenches inequality across generations?',
     'Which two are hardest to break?',
     ['unequal schooling', 'inherited wealth', 'social networks',
      'housing costs', 'expectations from birth'])
_dbt('C2', 'THE ATTENTION ECONOMY',
     'What have we lost by trading our attention for free services?',
     'Which two losses matter most?',
     ['depth of thought', 'meaningful conversation', 'patience with boredom',
      'the capacity to be alone', 'privacy of the mind'])

SEED_DEBATES = _DEBATES


# ── Page builders ────────────────────────────────────────────────────────────

def build_debate(html, t):
    html = strip_marks(html)
    html = head_bits(html, f"{t['name']} · {SITE}", t['meta'], DEBATE_CSS)

    m = re.search(r'<a href="#" class="st-brand".*?</a>', html, re.S)
    if not m:
        raise SystemExit('build: debate builder brand not found')
    html = html[:m.start()] + brand(t['slug']) + html[m.end():]

    label = ('<!-- jpt:debateslabel --><div class="jt-label" style="margin-bottom:9px">'
             'Debate bank</div><!-- /jpt:debateslabel -->\n        ')
    before = '<div class="side-top">\n      <div class="searchwrap">'
    html = need(html, before, 'the sidebar search to label')
    html = html.replace(before, '<div class="side-top">\n      ' + label + '<div class="searchwrap">', 1)

    # Must be the FIRST child of #cardHome: exitPresent puts the card back with
    # appendChild, so anything after it leaves the pane reordered on the way out.
    # Give John's collapse chevron the shared handle class so it matches the
    # other tools' sidebars exactly.
    html = html.replace('class="side-toggle" id="sideToggle"',
                        'class="side-toggle jpt-side-handle" id="sideToggle"', 1)

    home = '<div class="main-inner" id="cardHome">'
    html = need(html, home, '#cardHome')
    html = html.replace(home, home + '\n      ' + tool_head(t), 1)

    # Null-guard withExportButton: #pngBtn/#pdfBtn no longer exist once the three
    # export buttons become one download menu, and it would throw on null.
    html = html.replace('const btn = document.getElementById(id);',
                        'const btn = document.getElementById(id) || {};', 1)

    # Level colours: monochromatic blue scale (John's call, was orange/green/
    # blue/purple). Drives the sidebar headers via the CSS above and the tool's
    # phrases panel, level tag, and bubble colouring via this object. Kept in
    # sync with the .side-group.lvl-* CSS above so the sidebar and the tool's
    # main pane agree on which shade of blue each level is.
    lvl_old_re = re.compile(r'const LEVEL_COLOURS = \{.*?\};', re.S)
    lvl_new = ('const LEVEL_COLOURS = {\n'
               "  B1: {light:'#6b8cd6', dark:'#b8d4f7'},\n"
               "  B2: {light:'#3b6ec4', dark:'#8fb3e8'},\n"
               "  C1: {light:'#2563eb', dark:'#5b8def'},\n"
               "  C2: {light:'#1e3a8a', dark:'#7ba4de'}\n"
               '};')
    html, n = lvl_old_re.subn(lvl_new, html, count=1)
    if not n:
        raise SystemExit('build: could not find LEVEL_COLOURS in debate-builder')

    # Reshape the sidebar list to match Speaking Topics: coloured-caps section
    # per level (B1/B2/C1/C2), collapsible, most-recent debate first inside
    # each. Level chips overhead (still rendered into a hidden div — the tool
    # writes into #lvlFilter which the CSS in DEBATE_CSS hides). Search bar
    # still bypasses the grouping and shows a flat list of matches.
    render_re = re.compile(
        r'function renderSidebar\(\) \{.*?`\)\.join\(\'\'\);\s*\}\s*\n',
        re.S)
    render_new = '''function renderSidebar() {
  const list = document.getElementById('sideList');
  const q = document.getElementById('search').value.trim().toLowerCase();
  let items = [...state.debates];
  if (q) items = items.filter(d =>
    (d.title + ' ' + d.question + ' ' + d.task + ' ' + d.bubbles.join(' ')).toLowerCase().includes(q)
  );
  if (!items.length) {
    list.innerHTML = `<div class="empty-list">${q ? 'Nothing matches that.' : 'No debates yet. Click + New.'}</div>`;
    return;
  }
  // Sidebar titles show as Title Case regardless of typed case: the tool's
  // main .debate-title has text-transform:uppercase, so users often type
  // titles in caps to match what they see there. Lowercasing here + CSS
  // text-transform:capitalize on .title normalises both "FREE TIME" and
  // "free time" to display "Free Time" — matches Speaking Topics' item look
  // without touching stored data.
  const itemHtml = d => `<div class="side-item ${d.id === state.currentId ? 'active' : ''}" onclick="selectDebate('${d.id}')">
    <div class="title">${escapeHtml((d.title || 'Untitled').toLowerCase())}</div>
    <button class="del" onclick="event.stopPropagation();deleteDebate('${d.id}')" title="Delete">${'✕'}</button>
  </div>`;
  if (q) {
    items.sort((a,b) => b.updated - a.updated);
    list.innerHTML = items.map(itemHtml).join('');
    return;
  }
  const openKey = 'c2_debate_open_levels';
  let open;
  try { open = new Set(JSON.parse(localStorage.getItem(openKey) || 'null') || LEVEL_ORDER); }
  catch(e) { open = new Set(LEVEL_ORDER); }
  const byLevel = {};
  items.forEach(d => { (byLevel[d.level] = byLevel[d.level] || []).push(d); });
  Object.values(byLevel).forEach(arr => arr.sort((a,b) => b.updated - a.updated));
  list.innerHTML = LEVEL_ORDER.filter(l => byLevel[l] && byLevel[l].length).map(l => `
    <div class="side-group lvl-${l} ${open.has(l) ? 'open' : ''}">
      <div class="side-group-toggle" onclick="toggleSideGroup('${l}')">
        <span class="side-group-name">Level ${l}</span>
        <span class="side-group-chevron">${'▼'}</span>
      </div>
      <div class="side-group-body">${byLevel[l].map(itemHtml).join('')}</div>
    </div>
  `).join('');
}
function toggleSideGroup(level) {
  const key = 'c2_debate_open_levels';
  let open;
  try { open = new Set(JSON.parse(localStorage.getItem(key) || 'null') || LEVEL_ORDER); }
  catch(e) { open = new Set(LEVEL_ORDER); }
  if (open.has(level)) open.delete(level); else open.add(level);
  try { localStorage.setItem(key, JSON.stringify([...open])); } catch(e) {}
  renderSidebar();
}
'''
    html, n = render_re.subn(render_new, html, count=1)
    if not n:
        raise SystemExit('build: could not rewrite renderSidebar in debate-builder')

    # Replace Export PNG / Export PDF / Print with the shared download dropdown.
    three_re = (r'<button class="btn ghost tiny" onclick="exportPNG\(\)" id="pngBtn">Export PNG</button>\s*'
                r'<button class="btn ghost tiny" onclick="exportPDF\(\)" id="pdfBtn">Export PDF</button>\s*'
                r'<button class="btn ghost tiny" onclick="window\.print\(\)">Print</button>')
    html, n = re.subn(three_re, lambda m: DEBATE_MENU, html, count=1)
    if n != 1:
        raise SystemExit('build: could not find the debate export buttons to replace')

    # First-time seed: 16 pre-populated debates (see SEED_DEBATES). Guarded by a
    # localStorage flag so we never re-seed. Also only seeds if the tool's own
    # boot produced its default single "NEW DEBATE" (or nothing) — as soon as
    # John (or a student) has real work, we leave it alone.
    seed_json = json.dumps(SEED_DEBATES, ensure_ascii=False)
    seed_script = ('<!-- jpt:seed --><script>(function(){\n'
                    "var FLAG='jpt_debate_seeded_v1';\n"
                    'if (localStorage.getItem(FLAG)) return;\n'
                    'var isDefault = state.debates.length === 1\n'
                    '  && state.debates[0].title === "NEW DEBATE"\n'
                    '  && Array.isArray(state.debates[0].bubbles)\n'
                    '  && state.debates[0].bubbles[0] === "option one";\n'
                    'if (state.debates.length && !isDefault) {\n'
                    '  localStorage.setItem(FLAG, "1"); return;\n'
                    '}\n'
                    'var seeds = ' + seed_json + ';\n'
                    'var now = Date.now();\n'
                    'state.debates = seeds.map(function(d,i){\n'
                    '  return Object.assign({}, d,\n'
                    '    {id:"d_seed_"+d.level+"_"+i, updated: now - i*1000});\n'
                    '});\n'
                    'state.debates.forEach(migrate);\n'
                    'state.currentId = state.debates[0].id;\n'
                    'try { localStorage.setItem(STORE, JSON.stringify(state)); } catch(e){}\n'
                    'localStorage.setItem(FLAG, "1");\n'
                    'if (typeof renderSidebar === "function") renderSidebar();\n'
                    'if (typeof renderDebate === "function") renderDebate();\n'
                    'if (typeof renderLevelFilter === "function") renderLevelFilter();\n'
                    '})();</script><!-- /jpt:seed -->')
    html = inject_before(html, '</body>', MENU_JS + EXPORT_MENU_JS + seed_script, 'the menu scripts')
    return html


# Feather icons (MIT, feathericons.com), inner markup only — svg() adds the
# shared viewBox/stroke attributes. Only the ~50 actually used ship here, not
# the full set.
FEATHER = {
  'user': '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  'briefcase': '<rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
  'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  'camera': '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>',
  'navigation': '<polygon points="3 11 22 2 13 21 11 13 3 11"/>',
  'coffee': '<path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/>',
  'heart': '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>',
  'smartphone': '<rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>',
  'book-open': '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
  'home': '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
  'share-2': '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>',
  'dollar-sign': '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
  'droplet': '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>',
  'film': '<rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/>',
  'activity': '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
  'radio': '<circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/>',
  'message-circle': '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
  'sunrise': '<path d="M17 18a5 5 0 0 0-10 0"/><line x1="12" y1="2" x2="12" y2="9"/><line x1="4.22" y1="10.22" x2="5.64" y2="11.64"/><line x1="1" y1="18" x2="3" y2="18"/><line x1="21" y1="18" x2="23" y2="18"/><line x1="18.36" y1="11.64" x2="19.78" y2="10.22"/><line x1="23" y1="22" x2="1" y2="22"/><polyline points="8 6 12 2 16 6"/>',
  'trending-up': '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
  'smile': '<circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>',
  'scissors': '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.12" y2="15.88"/><line x1="14.47" y1="14.48" x2="20" y2="20"/><line x1="8.12" y1="8.12" x2="12" y2="12"/>',
  'shield': '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  'feather': '<path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"/><line x1="16" y1="8" x2="2" y2="22"/><line x1="17.5" y1="15" x2="9" y2="15"/>',
  'award': '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>',
  'anchor': '<circle cx="12" cy="5" r="3"/><line x1="12" y1="22" x2="12" y2="8"/><path d="M5 12H2a10 10 0 0 0 20 0h-3"/>',
  'clock': '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  'cloud': '<path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>',
  'rotate-ccw': '<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>',
  'compass': '<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>',
  'shopping-bag': '<path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>',
  'truck': '<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
  'moon': '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
  'umbrella': '<path d="M23 12a11.05 11.05 0 0 0-22 0zm-5 7a3 3 0 0 1-6 0v-7"/>',
  'map-pin': '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
  'sliders': '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
  'lock': '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  'cpu': '<rect x="4" y="4" width="16" height="16" rx="2" ry="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>',
  'alert-triangle': '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  'repeat': '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
  'help-circle': '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  'image': '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
  'music': '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  'book': '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  'check-circle': '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
  'search': '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  'globe': '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
  'trending-down': '<polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/>',
  'thumbs-up': '<path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>',
  'gift': '<polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><line x1="12" y1="22" x2="12" y2="7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>',
  'flag': '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>',
  'sun': '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
  'sunset': '<path d="M17 18a5 5 0 0 0-10 0"/><line x1="12" y1="9" x2="12" y2="2"/><line x1="4.22" y1="10.22" x2="5.64" y2="11.64"/><line x1="1" y1="18" x2="3" y2="18"/><line x1="21" y1="18" x2="23" y2="18"/><line x1="18.36" y1="11.64" x2="19.78" y2="10.22"/><line x1="23" y1="22" x2="1" y2="22"/><polyline points="16 5 12 9 8 5"/>',
  'star': '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
  'pen-tool': '<path d="M12 19l7-7 3 3-7 7-3-3z"/><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/><path d="M2 2l7.586 7.586"/><circle cx="11" cy="11" r="2"/>',
  'target': '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
}

# One icon per topic, chosen so no two topics in the same sidebar group (see
# topicGroups in the tool's own JS) repeat an icon. Keyed by index into the
# tool's `topics` array, not by name, since that array is unlabelled JSON.
TOPIC_ICON_NAMES = {
    0: 'user', 1: 'briefcase', 2: 'users', 3: 'camera', 4: 'navigation',
    5: 'coffee', 6: 'heart', 7: 'smartphone', 8: 'book-open', 9: 'home',
    10: 'share-2', 11: 'dollar-sign', 12: 'droplet', 13: 'film', 14: 'activity',
    15: 'radio', 16: 'message-circle', 17: 'sunrise', 18: 'trending-up', 19: 'smile',
    20: 'scissors', 21: 'shield', 22: 'feather', 23: 'award', 24: 'anchor',
    25: 'clock', 26: 'cloud', 27: 'rotate-ccw', 28: 'compass', 29: 'shopping-bag',
    30: 'truck', 31: 'moon', 32: 'umbrella', 33: 'map-pin', 34: 'sliders',
    35: 'lock', 36: 'cpu', 37: 'alert-triangle', 38: 'repeat', 39: 'help-circle',
    40: 'image', 41: 'music', 42: 'book', 43: 'check-circle', 44: 'search',
    45: 'globe', 46: 'trending-down', 47: 'thumbs-up', 48: 'gift', 49: 'flag',
    # Added by build.py, not present in John's source. See NEW_TOPICS below.
    50: 'sun',       # Mental Health — Health, Nature & Travel
    51: 'heart',     # Love, Dating & Marriage — You & Your Life
    52: 'heart',     # Volunteering & Charity — Work, Money & Education (heart
                     # reused: it's already Love in a different sidebar group;
                     # within Work/Money/Education itself, still unique)
    53: 'sunset',    # Retirement & Later Life — Work, Money & Education
    54: 'star',      # Space & Exploration — Technology & The Future
    55: 'pen-tool',  # Art & Design — Culture, Language & Ideas
    56: 'target',    # Advertising & Marketing — Society & The World
}


# Two topics John asked for on top of his shipped 50, added at build time so
# src/speaking-topics.html stays a clean mirror of his Downloads copy. If he
# ever adds these himself in a future Downloads refresh, remove them here
# (and their entries in TOPIC_ICON_NAMES + the topicGroups patches below).
NEW_TOPICS = [
    {
        "name": "Mental Health",
        "emoji": "\U0001F9D8",
        "simple": {
            "personal": [
                "How do you usually deal with stress?",
                "What helps you relax after a long day?",
                "Do you talk about your feelings with people close to you?",
                "What's something small that always lifts your mood?",
                "When you're feeling low, what tends to help?",
            ],
            "thought": [
                "Is it easier to talk about mental health today than it used to be?",
                "Should schools teach children about mental health?",
                "Is exercise good for the mind as well as the body?",
                "Are social media and mental health connected?",
                "Is it better to keep your problems to yourself or share them?",
            ],
        },
        "advanced": {
            "personal": [
                "What's the healthiest habit you've built for looking after your mind, and what made it stick?",
                "When was the last time you felt genuinely burnt out, and how did you find your way back?",
                "How do you tell the difference between a bad day and something more serious?",
                "What do you do that you know isn't good for your mental health, but you do anyway?",
                "Who in your life do you turn to when things feel heavy?",
            ],
            "thought": [
                "Has the language we now use around mental health helped, or has it made ordinary struggles look like illness?",
                "To what extent are our mental health problems the result of the way society is structured rather than of individual weakness?",
                "Should employers be legally required to protect their staff's mental wellbeing?",
                "Are apps and self-help books a real solution, or a distraction from getting proper help?",
                "Is happiness a reasonable goal, or should we aim for something else instead?",
            ],
        },
    },
    {
        "name": "Love, Dating & Marriage",
        "emoji": "\U0001F495",
        "simple": {
            "personal": [
                "What do you look for in a partner?",
                "Do you believe in love at first sight?",
                "What's the most romantic thing anyone has done for you?",
                "Where's a good place for a first date?",
                "How did your parents or grandparents meet?",
            ],
            "thought": [
                "Is marriage still important today?",
                "Do you think online dating works?",
                "Is a big age gap in a relationship a problem?",
                "Should couples live together before they marry?",
                "What makes a relationship last?",
            ],
        },
        "advanced": {
            "personal": [
                "What's a lesson about love you had to learn the hard way?",
                "How have your ideas about relationships changed as you've got older?",
                "What's the difference between someone you can date and someone you can build a life with?",
                "When have you had to compromise in a relationship, and did you feel it was worth it?",
                "Is there a small gesture from someone you love that means more to you than any grand romantic act?",
            ],
            "thought": [
                "Has dating culture become too transactional, or is that just realism about what people actually want?",
                "To what extent is the idea of 'the one' a myth we tell ourselves?",
                "How is technology reshaping what it means to be in a relationship?",
                "Is marriage a genuinely useful institution today, or a leftover from a very different society?",
                "Can two people who want completely different lives ever really make it work?",
            ],
        },
    },
    {
        "name": "Volunteering & Charity",
        "emoji": "\U0001F49D",
        "simple": {
            "personal": [
                "Have you ever done any volunteer work?",
                "Do you give money to charity?",
                "What kind of causes are important to you?",
                "Would you volunteer abroad?",
                "What's the best way to help someone in need?",
            ],
            "thought": [
                "Why do people volunteer?",
                "Should students do volunteer work at school?",
                "Is it better to give time or money to charity?",
                "Do charities do more good than governments?",
                "Should famous people give more to charity?",
            ],
        },
        "advanced": {
            "personal": [
                "What's the most rewarding thing you've ever done for someone else with no expectation of anything in return?",
                "If you had a whole year off and enough money to live on, which cause would you give that year to?",
                "Have you ever seen a charity change someone's life close to you?",
                "Why do we help strangers we'll never meet again?",
                "When was the last time a small act of kindness stayed with you?",
            ],
            "thought": [
                "Are charities a genuine force for good, or a sign that the state has abandoned its responsibilities?",
                "To what extent does volunteering benefit the volunteer more than the people they're trying to help?",
                "Should the wealthy be legally obliged to give a percentage of their income to charity?",
                "Is public giving, the kind that gets talked about on social media, still generosity, or is it self-promotion?",
                "Can a society that relies on food banks and charity really call itself a fair one?",
            ],
        },
    },
    {
        "name": "Retirement & Later Life",
        "emoji": "\U0001F334",
        "simple": {
            "personal": [
                "At what age would you like to retire?",
                "What do you plan to do after you stop working?",
                "Do you know anyone who's retired and happy?",
                "Where would you like to live in your old age?",
                "What are you saving up for?",
            ],
            "thought": [
                "Is 65 too young or too old to retire?",
                "Should older people keep working if they can?",
                "Do young people take care of their parents enough?",
                "Is old age respected in your country?",
                "Are people afraid of getting old?",
            ],
        },
        "advanced": {
            "personal": [
                "When you picture yourself at 70, what does a good day look like?",
                "What have you seen a parent or grandparent do in retirement that you'd want to copy, or avoid?",
                "Is there a skill or hobby you're saving for later in life, and why haven't you started already?",
                "How much of your identity is tied to your job, and what happens when that's gone?",
                "If you could freeze time at any age, would you? Which one?",
            ],
            "thought": [
                "Should the retirement age keep rising as we live longer, or is that the state quietly moving the goalposts?",
                "To what extent are we responsible for our parents' care in old age, and where does the state come in?",
                "Is retirement even a coherent idea any more in an economy where careers keep changing?",
                "Are we living longer lives, or just slower deaths?",
                "Has society decided that old age is a problem to be managed rather than a stage to be respected?",
            ],
        },
    },
    {
        "name": "Space & Exploration",
        "emoji": "\U0001F680",
        "simple": {
            "personal": [
                "Are you interested in space?",
                "Would you go to space if you could?",
                "Do you look at the stars at night?",
                "What do you know about the moon landing?",
                "Have you ever been to a planetarium?",
            ],
            "thought": [
                "Should governments spend money on space?",
                "Do you think there's life on other planets?",
                "Will humans live on Mars one day?",
                "Are space missions worth the risk?",
                "Why are people so fascinated by space?",
            ],
        },
        "advanced": {
            "personal": [
                "If there were an eight-hour queue for a fifteen-minute trip to the edge of space, would you join it?",
                "When you look up at a clear night sky, what does it make you think about?",
                "What discovery about the universe has genuinely surprised you?",
                "Would you want to know for certain whether we're alone in the universe?",
                "Is there a science-fiction future you'd genuinely like to live in?",
            ],
            "thought": [
                "Should we be pouring resources into reaching Mars while we still can't feed everyone on Earth?",
                "Is space becoming another territory for the rich, or genuinely a new frontier for humanity?",
                "To what extent does exploring space help us understand ourselves?",
                "Should there be an international treaty stopping any one country claiming a piece of the moon?",
                "Has commercial spaceflight cheapened the whole idea of exploration?",
            ],
        },
    },
    {
        "name": "Art & Design",
        "emoji": "\U0001F3A8",
        "simple": {
            "personal": [
                "Do you enjoy visiting art galleries?",
                "What kind of art do you like?",
                "Can you draw or paint?",
                "Is there a famous artwork you love?",
                "Do you have any art in your home?",
            ],
            "thought": [
                "Is art important in schools?",
                "Should the government pay artists?",
                "Is a painting worth millions of pounds ever really worth that much?",
                "Do children make better art than adults?",
                "Is graffiti art or vandalism?",
            ],
        },
        "advanced": {
            "personal": [
                "Is there a piece of art that has moved you unexpectedly, and can you explain why?",
                "What role does good design play in your daily life, even in things you don't think of as designed?",
                "If you had to fill a room with one artist's work, whose would it be?",
                "Have you ever paid more for something purely because it was beautifully designed?",
                "Do you have a strong opinion about a particular style you love or can't stand, and where does that come from?",
            ],
            "thought": [
                "To what extent is the price of a work of art related to its artistic value, and to what extent is it just a game?",
                "Has good design become a luxury only the wealthy get to enjoy?",
                "Can something be genuinely beautiful without being useful, or is that a contradiction?",
                "Is AI-generated art really art, or does the human intention matter more than the result?",
                "Should offensive or provocative art be protected by law, or should communities have the right to remove it?",
            ],
        },
    },
    {
        "name": "Advertising & Marketing",
        "emoji": "\U0001F4E3",
        "simple": {
            "personal": [
                "Do adverts influence what you buy?",
                "What's an advert you remember from childhood?",
                "Have you ever bought something because of an ad?",
                "Are there any adverts you actually enjoy watching?",
                "Do you use ad blockers online?",
            ],
            "thought": [
                "Are there too many adverts everywhere?",
                "Should adverts for junk food be banned?",
                "Is it fair to show ads to children?",
                "Do celebrities in adverts really change our minds?",
                "Are online ads worse than TV ads?",
            ],
        },
        "advanced": {
            "personal": [
                "What's the most manipulative advert you can remember, and did it work on you?",
                "Is there a brand you'd genuinely defend to someone who criticised it, and what does that say about you?",
                "Have you ever caught yourself wanting something purely because you saw it in your feed?",
                "What does the advertising you see about you say about how algorithms think you are?",
                "Would you pay a small monthly fee for a version of the internet with no advertising at all?",
            ],
            "thought": [
                "Has advertising become so sophisticated that we can no longer meaningfully consent to being persuaded by it?",
                "Should political advertising follow the same truth-in-advertising rules as commercial advertising?",
                "To what extent does modern advertising create wants we would never otherwise have had?",
                "Is the attention economy quietly becoming a bigger threat to democracy than we realise?",
                "Should influencers who are paid to promote a product be legally obliged to make that as visible as a TV ad break?",
            ],
        },
    },
]


def build_speaking(html, t):
    html = strip_marks(html)
    html = head_bits(html, f"{t['name']} · {SITE}", t['meta'], SPEAKING_CSS)

    # Strip the tool's own site chrome.
    for pat, what in [(r'<div class="topnav">.*?</div>\s*</div>\s*', 'its top nav'),
                      (r'<div class="page-header">.*?</div>\s*(?=<div class="controls">)', 'its page header'),
                      (r'<footer>.*?</footer>\s*', 'its footer')]:
        html, n = re.subn(pat, '', html, count=1, flags=re.S)
        if not n:
            raise SystemExit(f'build: could not strip {what} from {t["slug"]}')

    # Pull the pieces out so they can be dealt back into the shell: what you
    # choose from goes in the sidebar, what you show the class goes in the main
    # pane. Same shape as the Debate Builder.
    def take(pattern, what):
        nonlocal html
        m = re.search(pattern, html, re.S)
        if not m:
            raise SystemExit(f'build: could not find {what} in {t["slug"]}')
        html = html[:m.start()] + html[m.end():]
        return m.group(0)

    # Taken out and not put back: the deck card renders its own level pills
    # right beside the questions, so a second set in the sidebar is noise.
    take(r'<div class="level-toggle">.*?</div>\s*(?=<div style="display:flex)', 'the level toggle')
    acts   = take(r'<div style="display:flex;gap:\.5rem;flex-wrap:wrap">.*?</div>\s*(?=</div>)', 'the action buttons')
    # Focus mode is now the topbar Present button; keep only Random topic here.
    acts = re.sub(r'<button class="action-btn" onclick="openFocusMode\(\)">.*?</button>', '', acts, count=1, flags=re.S)
    search = take(r'<div class="search-wrap">.*?</div>\s*</div>', 'the search box')
    grid   = take(r'<div id="topicGrid"></div>', 'the topic grid')
    holder = take(r'<div class="placeholder" id="placeholder">.*?</div>', 'the placeholder')
    deck   = take(r'<div class="deck" id="deck"></div>', 'the deck')
    # deck-nav has no nested divs, so one </div> closes it. Asking for two ran
    # on into the timer section and ate half of it.
    navrow = take(r'<div class="deck-nav" id="deckNav".*?</div>', 'the deck nav')
    timer  = take(r'<div class="timer-section">.*?</div>\s*</div>\s*</div>', 'the timer')
    # John asked for the student picker to go. Taken out and not put back.
    take(r'<div class="name-picker" id="namePicker">.*?</div>\s*</div>\s*(?=</div>)', 'the student picker')

    # Whatever is left of the old wrappers goes; the shell replaces them.
    html = re.sub(r'<div class="controls">\s*<div class="controls-top">\s*</div>\s*</div>', '', html, count=1, flags=re.S)
    html = re.sub(r'<div class="main">\s*</div>', '', html, count=1, flags=re.S)

    shell = f"""<header class="stopbar">
{brand(t['slug'])}
  <div class="grow"></div>
  {THEME_BTN}
  {PRESENT_BTN}
</header>

<div class="app" id="app">
  <aside>
    <div class="side-top">
      <div class="jt-label">Find a question</div>
      {search}
    </div>
    <div class="side-list">
      {grid}
    </div>
  </aside>
  <button class="jpt-side-handle" id="jptSideToggle" onclick="jptToggleSide()"
          title="Hide the topic list" aria-label="Hide the topic list" aria-expanded="true">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
  </button>

  <main>
    <div class="main-inner">
      {tool_head(t)}
      <div class="toolbar">
        <div class="status">Questions</div>
        {acts}
        {TIMER_HTML}
        {QUESTIONS_RESET_BTN}
        {SPEAKING_MENU}
      </div>
      <div class="jpt-tmbar" id="jptTmBar"><span id="jptTmBarFill"></span></div>
      <div class="deck-row">
        <div class="deck-col">
          {holder}
          {deck}
          {navrow}
        </div>
        <aside class="phrases-panel" aria-label="Useful phrases">
          <div class="ph-head">
            <span class="ph-title">Useful phrases</span>
            <div class="ph-flip" role="group" aria-label="Phrase level">
              <button class="ph-flip-btn on" data-lvl="simple" onclick="jptPhraseFlip('simple')" title="Simple" aria-label="Simple answers"><svg viewBox="0 0 24 24" fill="currentColor" stroke="none" aria-hidden="true"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26"/></svg></button>
              <button class="ph-flip-btn" data-lvl="advanced" onclick="jptPhraseFlip('advanced')" title="Advanced" aria-label="Advanced answers"><svg viewBox="0 0 24 24" fill="currentColor" stroke="none" aria-hidden="true"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26"/></svg><svg viewBox="0 0 24 24" fill="currentColor" stroke="none" aria-hidden="true"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26"/></svg></button>
            </div>
            <button class="ph-reset" onclick="jptPhrasesReset()" title="Reset to the defaults">Reset</button>
          </div>
          <div class="ph-list" id="jptPhraseList"></div>
          <button class="ph-add" onclick="jptPhraseAdd()">+ Add phrase</button>
          <p class="ph-note">Common ways to answer, across any topic. Edit them for your class.</p>
        </aside>
      </div>
    </div>
  </main>
</div>

"""
    marker = '<div class="focus-overlay"'
    i = sole_position(html, marker, 'the focus overlay')
    html = html[:i] + shell + html[i:]

    # The magnifying glass is a mask on .search-wrap::before, so the icon can
    # follow currentColor in both themes without another element in the markup.
    ico = ("<style>/* jpt:strip */:root{--search-ico:url(\"data:image/svg+xml,"
           "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
           "stroke='black' stroke-width='2.4' stroke-linecap='round'%3E%3Ccircle cx='11' cy='11' "
           "r='7'/%3E%3Cline x1='21' y1='21' x2='16.65' y2='16.65'/%3E%3C/svg%3E\")}"
           "/* /jpt:strip */</style>")
    html = inject_before(html, '</head>', ico, 'the search icon')

    # Declutter (John's call): keep only Export PDF on the deck card. Remove the
    # Reveal-mode, Roulette and Uncross-all buttons, which built the busy second
    # row of tools under every topic. Each is one `h += '<button ...>';` line in
    # renderDeck; revealMode stays false so the questions simply always show.
    for fn in ('toggleRevealMode', 'openRoulette', 'uncrossAll', 'exportPDF'):
        html, n = re.subn(
            r"h \+= '<button class=\"deck-tool-btn[^\n]*?onclick=\"" + fn + r"\(\)\"[^\n]*?</button>';\n?",
            '', html, count=1)
        if not n:
            raise SystemExit(f'build: could not remove the {fn} button from speaking-topics')

    # The topics used to sit above the questions; they are a list on the left now.
    # The picker is gone, but renderNames() still runs at boot and would write
    # to the absent #nameTags, throwing before buildTopicGrid(). Guard it.
    html = html.replace("var box = document.getElementById('nameTags');",
                        "var box = document.getElementById('nameTags');\n  if (!box) return;", 1)

    html = html.replace('Select a topic above to see the questions.',
                        'Pick a topic from the list, or search for a question.', 1)

    # Search placeholder still advertises the original 1,000. Compute the real
    # count from what the tool actually ships — 20 questions per topic, 57
    # topics after the additions above — so a future edit that changes either
    # the topic count or the questions-per-topic will surface here rather than
    # silently leaving the placeholder wrong.
    total_qs = 20 * (50 + len(NEW_TOPICS))
    old_placeholder = 'placeholder="Search all 1,000 questions..."'
    new_placeholder = f'placeholder="Search all {total_qs:,} questions..."'
    if old_placeholder not in html:
        raise SystemExit('build: could not find the search placeholder in speaking-topics')
    html = html.replace(old_placeholder, new_placeholder, 1)

    # A distinct icon per sidebar topic (John's call, over the tool's own
    # unused per-topic emoji field — see icons-never-emoji). buildTopicGrid()
    # runs at parse time as the tool's own script executes, before any script
    # this build appends, so the lookup table has to be defined inside that
    # same script, ahead of the call — hence splicing it in right before the
    # topics array rather than injecting it near </body>.
    topic_icons_js = 'var TOPIC_ICONS = ' + json.dumps(
        {i: svg(FEATHER[name]) for i, name in TOPIC_ICON_NAMES.items()}) + ';\n'
    if 'var topics = [' not in html:
        raise SystemExit('build: could not find the topics array in speaking-topics')
    html = html.replace('var topics = [', topic_icons_js + 'var topics = [', 1)

    # Append the extra topics (see NEW_TOPICS) just before the closing `];` of
    # the topics array. Anchor on `}];\n` immediately followed by
    # `var currentLevel` (unique — the tool has exactly one topics array), so
    # a future refresh of John's source won't quietly slip past this splice.
    new_topics_json = ','.join(json.dumps(t, ensure_ascii=False) for t in NEW_TOPICS)
    topics_end_re = re.compile(r'\}\](;\s*\n\s*var currentLevel)')
    html, n = topics_end_re.subn(r'},' + new_topics_json + r']\1', html, count=1)
    if not n:
        raise SystemExit('build: could not append the extra topics to the array')

    # Slot the new topic indices into their sidebar groups (see NEW_TOPICS).
    for old, new, group in (
        ('indices: [4, 6, 14, 22, 31]',
         'indices: [4, 6, 50, 14, 22, 31]', 'Health, Nature & Travel'),
        ('indices: [0, 2, 10, 19, 26, 27, 37, 38, 39]',
         'indices: [0, 2, 51, 10, 19, 26, 27, 37, 38, 39]', 'You & Your Life'),
        ('indices: [1, 8, 11, 23]',
         'indices: [1, 8, 11, 23, 52, 53]', 'Work, Money & Education'),
        ('indices: [7, 15, 35, 36, 18, 44]',
         'indices: [7, 15, 35, 36, 18, 44, 54]', 'Technology & The Future'),
        ('indices: [13, 16, 17, 24, 25, 33, 40, 41, 42, 43]',
         'indices: [13, 16, 17, 24, 25, 33, 40, 41, 42, 43, 55]', 'Culture, Language & Ideas'),
        ('indices: [12, 21, 28, 34, 45, 46, 47, 49]',
         'indices: [12, 21, 28, 34, 45, 46, 47, 49, 56]', 'Society & The World'),
    ):
        if old not in html:
            raise SystemExit(f'build: could not find the {group} indices in speaking-topics')
        html = html.replace(old, new, 1)
    if 'h += t.name;' not in html:
        raise SystemExit('build: could not find the topic button label in speaking-topics')
    html = html.replace('h += t.name;', "h += TOPIC_ICONS[i] + ' ' + t.name;", 1)

    # Carry the same icon onto the question card's own header, in place of the
    # single generic chat-bubble icon every topic used to share.
    deck_topic_re = r"h \+= '<span class=\"deck-topic\">.*?</svg> ' \+ t\.name \+ '</span>';"
    deck_topic_new = ("h += '<span class=\"deck-topic\">' + TOPIC_ICONS[currentTopicIdx] "
                       "+ ' ' + t.name + '</span>';")
    html, n = re.subn(deck_topic_re, deck_topic_new, html, count=1)
    if not n:
        raise SystemExit('build: could not find the question card topic icon in speaking-topics')

    # John's call: the shipped 1,000 questions are "the base" — make the text
    # editable per class, kept in localStorage, falling back to the original
    # wording. Overrides are sparse (only what's actually been edited), keyed
    # by topic/level/category/index, so nothing needs to duplicate the full
    # question set. See QUESTIONS_JS for jptQOverride/jptQEsc/jptQSave.
    personal_old = ("h += '<li class=\"q-item personal' + (revealMode ? ' hidden-q' : '') + '\">"
                    "<span class=\"q-num\">' + (i + 1) + '</span><span>' + q + '</span></li>';")
    personal_new = ("var qv = window.jptQOverride(currentTopicIdx, currentLevel, 'personal', i, q);\n"
                     "    h += '<li class=\"q-item personal' + (revealMode ? ' hidden-q' : '') + '\">"
                     "<span class=\"q-num\">' + (i + 1) + '</span><span class=\"q-text\" "
                     "contenteditable=\"true\" spellcheck=\"false\" data-cat=\"personal\" "
                     "data-qi=\"' + i + '\">' + window.jptQEsc(qv) + '</span></li>';")
    if personal_old not in html:
        raise SystemExit('build: could not find the personal question row in speaking-topics')
    html = html.replace(personal_old, personal_new, 1)

    thought_old = ("h += '<li class=\"q-item thought' + (revealMode ? ' hidden-q' : '') + '\">"
                   "<span class=\"q-num\">' + (i + 6) + '</span><span>' + q + '</span></li>';")
    thought_new = ("var qv = window.jptQOverride(currentTopicIdx, currentLevel, 'thought', i, q);\n"
                    "    h += '<li class=\"q-item thought' + (revealMode ? ' hidden-q' : '') + '\">"
                    "<span class=\"q-num\">' + (i + 6) + '</span><span class=\"q-text\" "
                    "contenteditable=\"true\" spellcheck=\"false\" data-cat=\"thought\" "
                    "data-qi=\"' + i + '\">' + window.jptQEsc(qv) + '</span></li>';")
    if thought_old not in html:
        raise SystemExit('build: could not find the thought-provoking question row in speaking-topics')
    html = html.replace(thought_old, thought_new, 1)

    handlers_old = """  deck.querySelectorAll('.q-item').forEach(function(item) {
    item.addEventListener('click', function() {
      if (this.classList.contains('hidden-q') && !this.classList.contains('revealed')) {
        this.classList.add('revealed');
      } else if (!this.classList.contains('hidden-q') || this.classList.contains('revealed')) {
        this.classList.toggle('crossed');
      }
    });
  });"""
    handlers_new = """  deck.querySelectorAll('.q-item').forEach(function(item) {
    item.addEventListener('click', function(e) {
      if (e.target.closest('.q-text')) return;
      if (this.classList.contains('hidden-q') && !this.classList.contains('revealed')) {
        this.classList.add('revealed');
      } else if (!this.classList.contains('hidden-q') || this.classList.contains('revealed')) {
        this.classList.toggle('crossed');
      }
    });
    var qt = item.querySelector('.q-text');
    if (!qt) return;
    qt.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') { e.preventDefault(); qt.blur(); }
    });
    qt.addEventListener('blur', function() {
      var cat = qt.getAttribute('data-cat');
      var qi = parseInt(qt.getAttribute('data-qi'), 10);
      var base = topics[currentTopicIdx][currentLevel][cat][qi];
      window.jptQSave(currentTopicIdx, currentLevel, cat, qi, base, qt.textContent);
    });
  });"""
    if handlers_old not in html:
        raise SystemExit('build: could not find the question click handlers in speaking-topics')
    html = html.replace(handlers_old, handlers_new, 1)

    html = re.sub(r'&family=JetBrains\+Mono:wght@[0-9;]+', '', html, count=1)

    html = inject_before(html, '</body>', MENU_JS + THEME_JS + TIMER_JS + EXPORT_MENU_JS + SPEAKING_PNG_JS + SIDE_JS + PHRASES_JS + QUESTIONS_JS, 'the page scripts')
    return html


def build_roleplays(html, t):
    """Wrap src/role-plays.html in the JPT shell.

    The source is built to fit the shell (already carries the .app/aside/main
    skeleton the other tools' shells build up to), so nothing gets stripped
    or diced up — just prepend the topbar, drop a tool-head badge inside
    .main-inner, wedge the side-collapse handle after </aside>, and add the
    site's shared theme/menu/side-collapse scripts before </body>.
    """
    html = strip_marks(html)
    html = head_bits(html, f"{t['name']} · {SITE}", t['meta'], '')

    inner = '<div class="main-inner">'
    if inner not in html:
        raise SystemExit('build: could not find .main-inner in role-plays')
    html = html.replace(inner, inner + '\n      ' + tool_head(t), 1)

    app = '<div class="app" id="app">'
    if app not in html:
        raise SystemExit('build: could not find .app in role-plays')
    topbar = (f'<header class="stopbar">\n{brand(t["slug"])}\n'
              f'  <div class="grow"></div>\n  {THEME_BTN}\n</header>\n\n')
    html = html.replace(app, topbar + app, 1)

    aside_close = '</aside>'
    if aside_close not in html:
        raise SystemExit('build: could not find </aside> in role-plays')
    handle = ('<button class="jpt-side-handle" id="jptSideToggle" onclick="jptToggleSide()"\n'
              '          title="Hide the scenario list" '
              'aria-label="Hide the scenario list" aria-expanded="true">\n'
              '    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
              '<polyline points="15 18 9 12 15 6"/></svg>\n  </button>\n')
    html = html.replace(aside_close, aside_close + '\n  ' + handle, 1)

    html = inject_before(html, '</body>', MENU_JS + THEME_JS + SIDE_JS + TIMER_JS, 'the page scripts')
    return html


BUILDERS = {'debate-builder': build_debate, 'speaking-topics': build_speaking,
            'role-plays': build_roleplays}


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
        # Count pm-items inside the brand dropdown only; the export menu reuses
        # the same class.
        brandmenu = re.search(r'id="toolsMenu".*?</div>\s*</div>', out, re.S)
        assert brandmenu and brandmenu.group(0).count('class="pm-item"') == len(TOOLS) + 2, \
            f"{t['slug']}: brand dropdown wrong size"
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
