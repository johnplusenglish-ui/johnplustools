#!/usr/bin/env python3
"""Build johnplustools.com as a single-page shell around John's Debate Builder.

The site is JohnPlusTools; the Debate Builder is its first tool. Both the home
view and the tool live in ONE document and share one topbar and sidebar, so
moving between them is a class toggle, not a page load. That is deliberate:
two separate pages felt like two different sites.

    index.html   generated. Serves both / and /debate-builder.
    src/debate-builder.html   John's tool, verbatim. Never hand-edit.
    src/home.html             the home view fragment, {{SLOT}} placeholders

    python3 build.py                 rebuild from src/
    python3 build.py ~/Downloads/debate-builder.html   and refresh src/ first

Everything injected is fenced in jpt: markers and stripped before re-adding, so
the build re-runs cleanly over a previous result.
"""
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / 'src' / 'debate-builder.html'
HOME_TPL = ROOT / 'src' / 'home.html'
OUT = ROOT / 'index.html'

TOOL_URL = '/debate-builder'

I = ('fill="none" stroke="currentColor" stroke-linecap="round" '
     'stroke-linejoin="round" aria-hidden="true"')


def svg(body, w=2):
    return f'<svg viewBox="0 0 24 24" {I} stroke-width="{w}">{body}</svg>'


SPANNER = svg('<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 '
              '7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>')
# John's own mark for the Debate Builder.
PROMPTS = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
           'stroke-linecap="round" aria-hidden="true">'
           '<circle cx="4.6" cy="6" r="2.1"/><line x1="10" y1="6" x2="21" y2="6"/>'
           '<circle cx="4.6" cy="12" r="2.1" fill="currentColor"/><line x1="10" y1="12" x2="21" y2="12"/>'
           '<circle cx="4.6" cy="18" r="2.1"/><line x1="10" y1="18" x2="21" y2="18"/></svg>')
BOOK = svg('<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>'
           '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>')
HOME = svg('<path d="M3 9.5 12 3l9 6.5V20a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 20z"/>'
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

FAVICON = ("<link rel=\"icon\" href=\"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' "
           "viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2' stroke-linecap='round' "
           "stroke-linejoin='round'><path d='M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 "
           "0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 "
           "7.94-7.94l-3.76 3.76z'/></svg>\">")

TITLE = '<title>John + Tools · free teaching tools for English classrooms</title>'
TOOL_TITLE = 'Debate Builder · John + Tools'
DESC = ('<meta name="description" content="Free browser tools for English teachers, by John of '
        'JohnPlusEnglish. First tool: the Debate Builder. No sign-up, nothing to install.">')

# Brand doubles as the pop-out switcher.
BRAND = f'''<!-- jpt:brand -->
  <div class="brand-wrap">
    <button class="st-brand" id="brandBtn" aria-haspopup="true" aria-expanded="false" aria-controls="toolsMenu">
      <span class="brand-icon">{SPANNER}</span>
      <span class="brand-title"><span class="k">JohnPlusEnglish</span><span class="b">Tools</span></span>
      <span class="brand-chev">{CHEV}</span>
    </button>
    <div class="popmenu" id="toolsMenu" role="menu" aria-labelledby="brandBtn" hidden>
      <div class="pm-label">Go to</div>
      <a class="pm-item" role="menuitem" href="/" data-view="home">
        <span class="pm-ico">{HOME}</span>Home</a>
      <a class="pm-item" role="menuitem" href="{TOOL_URL}" data-view="tool">
        <span class="pm-ico">{PROMPTS}</span>Debate Builder</a>
      <div class="pm-sep"></div>
      <a class="pm-item" role="menuitem" href="https://johnplusdictionary.com" target="_blank" rel="noopener">
        <span class="pm-ico">{BOOK}</span>JohnPlusDictionary<span class="pm-ext">{EXT}</span></a>
    </div>
  </div>
  <!-- /jpt:brand -->'''

NAV = f'''<!-- jpt:toolsnav -->
    <div class="tools-nav">
      <div class="jt-label">Tools</div>
      <a class="tool-item" href="/" data-view="home">
        <span class="ti-icon">{HOME}</span><span class="ti-name">Home</span>
      </a>
      <a class="tool-item" href="{TOOL_URL}" data-view="tool">
        <span class="ti-icon">{PROMPTS}</span><span class="ti-name">Debate Builder</span>
      </a>
    </div>
    <!-- /jpt:toolsnav -->
    '''

TOOL_HEAD = f'''<!-- jpt:toolhead -->
      <div class="tool-head">
        <span class="th-icon">{PROMPTS}</span>
        <div class="th-text">
          <h1>Debate Builder</h1>
          <p>Build a speaking debate, then run it from the front of the room.</p>
        </div>
      </div>
      <!-- /jpt:toolhead -->
      '''

FOOT = f'''<!-- jpt:sidefoot -->
    <div class="side-foot">
      <a href="https://johnplusdictionary.com" target="_blank" rel="noopener">
        {BOOK}JohnPlusDictionary
      </a>
    </div>
    <!-- /jpt:sidefoot -->
  '''

CSS = '''
/* jpt:chrome */
/* Site furniture spliced in by build.py. Not part of the tool. */

/* Brand as a pop-out switcher */
.brand-wrap{position:relative;display:inline-flex}
button.st-brand{background:none;border:none;cursor:pointer;font-family:inherit;
  padding:6px 8px;margin-left:-8px;border-radius:11px;transition:background .12s}
button.st-brand:hover{background:var(--soft)}
.brand-chev{color:var(--muted);display:inline-flex;margin-left:2px;transition:transform .18s ease}
.brand-chev svg{width:14px;height:14px}
button.st-brand[aria-expanded="true"] .brand-chev{transform:rotate(180deg)}
.popmenu{position:absolute;top:calc(100% + 8px);left:0;z-index:60;min-width:236px;
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

/* The tool's .btn was written for <button>. The home view uses <a class="btn">,
   which the UA underlines and whose icons have no size without this. */
a.btn{text-decoration:none}
.btn svg{width:14px;height:14px;flex-shrink:0}
.btn.big svg{width:15px;height:15px}

/* Sidebar nav */
.tools-nav{padding:14px 16px 12px;border-bottom:1px solid var(--line)}
.jt-label{font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--muted);font-weight:700;margin-bottom:9px}
.tool-item{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:11px;
  border:1px solid transparent;text-decoration:none;color:var(--ink);margin-bottom:3px;
  transition:background .12s,border-color .12s}
.tool-item:hover{background:var(--soft)}
.tool-item.active{background:var(--soft);border-color:var(--accent)}
.ti-icon{width:28px;height:28px;border-radius:8px;flex-shrink:0;display:grid;place-items:center;
  background:var(--soft);border:1px solid var(--soft-line);color:var(--accent)}
.tool-item.active .ti-icon{background:var(--accent);border-color:var(--accent);color:#fff}
.ti-icon svg{width:15px;height:15px;display:block}
.ti-name{font-size:13.5px;font-weight:600;letter-spacing:-.01em}

/* The tool's own sidebar controls, shown only while the tool is open. */
#debatesSection{display:flex;flex-direction:column;flex:1;min-height:0}
#debatesSection[hidden]{display:none}

/* margin-top:auto keeps this pinned to the bottom on the home view, where the
   debates section is hidden and nothing else pushes it down. */
.side-foot{padding:10px 12px 12px;border-top:1px solid var(--line);flex-shrink:0;margin-top:auto}
.side-foot a{display:flex;align-items:center;gap:8px;text-decoration:none;font-size:12.5px;
  font-weight:600;color:var(--muted);padding:8px 10px;border-radius:10px;transition:.12s}
.side-foot a:hover{background:var(--soft);color:var(--accent)}
.side-foot a svg{width:15px;height:15px;flex-shrink:0}

/* Named tool header, identical rhythm in both views so nothing jumps. */
.tool-head{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.th-icon{width:38px;height:38px;border-radius:11px;flex-shrink:0;display:grid;place-items:center;
  background:var(--soft);border:1px solid var(--soft-line);color:var(--accent)}
.th-icon svg{width:20px;height:20px;display:block}
.th-text h1{font-size:19px;font-weight:700;letter-spacing:-.02em;margin:0;line-height:1.2}
.th-text p{font-size:12.5px;color:var(--muted);margin:2px 0 0;line-height:1.4}

/* Views */
.view[hidden]{display:none}
.view{animation:viewIn .18s ease}
@keyframes viewIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.jpt-toolonly[hidden]{display:none}

/* Home view panel */
.panel{background:var(--card);border:1px solid var(--line);border-radius:18px;
  padding:30px 32px;box-shadow:var(--shadow-card)}
.panel-head{display:flex;align-items:flex-start;gap:16px;margin-bottom:20px}
.panel-icon{width:48px;height:48px;border-radius:13px;flex-shrink:0;background:var(--soft);
  border:1px solid var(--soft-line);color:var(--accent);display:grid;place-items:center}
.panel-icon svg{width:24px;height:24px}
.panel h2{font-size:1.5rem;font-weight:700;letter-spacing:-.025em;line-height:1.15;margin:0}
.panel .tagline{font-size:.93rem;color:var(--muted);margin-top:4px}
.panel .lede{font-size:1rem;color:var(--ink);max-width:62ch;margin-bottom:24px;font-weight:400;
  line-height:1.65}
.split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.08fr);
  gap:32px;align-items:start;margin-bottom:28px}
.features{display:grid;gap:15px;grid-template-columns:1fr}
.feature{display:flex;gap:11px;align-items:flex-start}
.feature .fi{color:var(--accent);flex-shrink:0;margin-top:2px;display:inline-flex}
.feature .fi svg{width:17px;height:17px}
.feature h3{font-size:.88rem;font-weight:700;letter-spacing:-.01em;margin-bottom:1px}
.feature p{font-size:.84rem;color:var(--muted);line-height:1.5}
.preview{display:block;text-decoration:none;color:inherit;border:1px solid var(--line);
  border-radius:12px;overflow:hidden;background:var(--bg);box-shadow:var(--shadow-card);
  transition:border-color .16s,transform .16s}
.preview:hover{border-color:var(--accent);transform:translateY(-2px)}
.preview:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.pv-bar{display:flex;align-items:center;gap:5px;padding:0 10px;height:26px;
  background:var(--card);border-bottom:1px solid var(--line)}
.pv-bar i{width:7px;height:7px;border-radius:999px;background:var(--line);flex-shrink:0}
[data-theme="dark"] .pv-bar i{background:var(--soft-line)}
/* Background image, not <img>, so only the theme in use is downloaded. */
.pv-shot{display:block;aspect-ratio:1100/515;
  background-image:url("/assets/debate-builder-light.png");
  background-size:cover;background-position:top center;background-repeat:no-repeat}
[data-theme="dark"] .pv-shot{background-image:url("/assets/debate-builder-dark.png")}
.pv-cap{display:flex;align-items:center;gap:6px;padding:9px 12px;font-size:12px;
  font-weight:600;color:var(--muted);background:var(--card);border-top:1px solid var(--line)}
.pv-cap svg{width:13px;height:13px;flex-shrink:0}
.preview:hover .pv-cap{color:var(--accent)}
.panel-actions{display:flex;gap:10px;flex-wrap:wrap;align-items:center;
  padding-top:22px;border-top:1px solid var(--line)}
.panel-actions .note{font-size:12.5px;color:var(--muted);font-weight:500}

@media (max-width:900px){
  .tools-nav{padding:12px 14px 10px}
  .th-text p{display:none}
  .split{grid-template-columns:1fr;gap:24px}
  .panel{padding:22px 18px;border-radius:16px}
  .popmenu{min-width:210px}
}
/* The brand is a button with padding and a chevron, so it is wider than the
   plain mark it replaced. Left full width it pushes Present off a phone
   screen, so drop the kicker line and tighten the bar. */
@media (max-width:700px){
  .stopbar{padding:0 14px;gap:10px}
  button.st-brand{padding:6px;margin-left:-6px}
  .brand-title .k{display:none}
  .brand-title .b{font-size:14px}
}
@media print{.tool-head,.tools-nav,.side-foot,.popmenu{display:none!important}}
@media (prefers-reduced-motion:reduce){.view,.popmenu{animation:none}}
/* /jpt:chrome */
'''

ROUTER = '''<!-- jpt:router -->
<script>
/* One document, two views. Switching is a class toggle plus a pushState, so
   moving between the site and the tool never reloads or reflows the shell. */
(function () {
  var ROUTES = { '/': 'home', '/debate-builder': 'tool', '/index.html': 'home' };
  var TITLES = {
    home: 'John + Tools \\u00b7 free teaching tools for English classrooms',
    tool: 'Debate Builder \\u00b7 John + Tools'
  };
  var PATHS = { home: '/', tool: '/debate-builder' };

  var homeView = document.getElementById('homeView');
  var toolView = document.getElementById('cardHome');
  var debates  = document.getElementById('debatesSection');
  var menu     = document.getElementById('toolsMenu');
  var brandBtn = document.getElementById('brandBtn');
  var current  = null;

  function setView(name, push) {
    if (name !== 'home' && name !== 'tool') name = 'home';
    if (name === current) return;
    current = name;
    var tool = name === 'tool';

    toolView.hidden = !tool;
    homeView.hidden = tool;
    if (debates) debates.hidden = !tool;
    // Tool-only topbar actions (help, Present) have no meaning on the home view.
    Array.prototype.forEach.call(document.querySelectorAll('.jpt-toolonly'),
      function (el) { el.hidden = !tool; });

    Array.prototype.forEach.call(document.querySelectorAll('[data-view]'), function (el) {
      var on = el.dataset.view === name;
      if (el.classList.contains('tool-item')) el.classList.toggle('active', on);
      if (el.getAttribute('role') === 'menuitem') el.setAttribute('aria-current', String(on));
      if (on && el.classList.contains('tool-item')) el.setAttribute('aria-current', 'page');
      else if (el.classList.contains('tool-item')) el.removeAttribute('aria-current');
    });

    document.title = TITLES[name];
    if (push && window.history && history.pushState) {
      history.pushState({ view: name }, '', PATHS[name]);
    }
    window.scrollTo(0, 0);
  }

  /* Any link carrying data-view routes in-page instead of loading. */
  document.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('[data-view]') : null;
    if (!a || a.target === '_blank') return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;   // let people open tabs
    e.preventDefault();
    closeMenu();
    setView(a.dataset.view, true);
  });

  window.addEventListener('popstate', function () {
    setView(ROUTES[location.pathname] || 'home', false);
  });

  /* Pop-out menu */
  function openMenu() {
    menu.hidden = false;
    brandBtn.setAttribute('aria-expanded', 'true');
  }
  function closeMenu() {
    if (menu.hidden) return;
    menu.hidden = true;
    brandBtn.setAttribute('aria-expanded', 'false');
  }
  brandBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    if (menu.hidden) openMenu(); else closeMenu();
  });
  document.addEventListener('click', function (e) {
    if (!menu.hidden && !menu.contains(e.target) && e.target !== brandBtn) closeMenu();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !menu.hidden) { closeMenu(); brandBtn.focus(); }
  });

  /* The tool binds global shortcuts (N, P, T, /). They must not fire while the
     home view is showing. Capture runs before the tool's bubble-phase handler
     whatever the registration order. */
  document.addEventListener('keydown', function (e) {
    if (current === 'tool') return;
    if (e.key === 'Escape' || e.metaKey || e.ctrlKey || e.altKey) return;
    var t = e.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    e.stopPropagation();
  }, true);

  setView(ROUTES[location.pathname] || 'home', false);
  if (window.history && history.replaceState) {
    history.replaceState({ view: current }, '', PATHS[current]);
  }
})();
</script>
<!-- /jpt:router -->
'''


def drop(html, tag):
    """Remove a previously injected block, so the build re-runs cleanly."""
    return re.sub(rf'<!-- {tag} -->.*?<!-- /{tag} -->\n?\s*', '', html, flags=re.S)


def home_view():
    tpl = HOME_TPL.read_text(encoding='utf-8')
    for key, val in {
        'SPANNER': SPANNER, 'PROMPTS': PROMPTS, 'PLAY': PLAY, 'SAVE': SAVE,
        'CLOCK': CLOCK, 'DOWNLOAD': DOWNLOAD, 'EYE': EYE, 'ARROW': ARROW,
        'TOOL_URL': TOOL_URL,
    }.items():
        tpl = tpl.replace('{{' + key + '}}', val)
    left = re.findall(r'\{\{(\w+)\}\}', tpl)
    if left:
        raise SystemExit(f'build: home template has unfilled slots: {sorted(set(left))}')
    return '<!-- jpt:homeview -->\n      ' + tpl.strip() + '\n      <!-- /jpt:homeview -->\n      '


def need(html, needle, what):
    if needle not in html:
        raise SystemExit(f'build: could not find {what}')
    return html


def build(html):
    for tag in ('jpt:brand', 'jpt:toolsnav', 'jpt:sidefoot', 'jpt:toolhead',
                'jpt:debateslabel', 'jpt:homeview', 'jpt:router', 'jpt:backlink'):
        html = drop(html, tag)
    html = re.sub(r'/\* jpt:chrome \*/.*?/\* /jpt:chrome \*/\n?', '', html, flags=re.S)
    html = html.replace('<div id="debatesSection">\n    ', '').replace(' class="jpt-toolonly"', '')

    # Head
    html = re.sub(r'<title>.*?</title>', TITLE, html, count=1, flags=re.S)
    if 'name="description"' not in html:
        html = html.replace(TITLE, TITLE + '\n' + DESC, 1)
    if 'rel="icon"' not in html:
        html = html.replace(TITLE, TITLE + '\n' + FAVICON, 1)

    # Brand becomes the pop-out switcher.
    brand = re.search(r'<a href="#" class="st-brand".*?</a>', html, re.S)
    if not brand:
        raise SystemExit('build: could not find the brand link to replace')
    html = html[:brand.start()] + BRAND + html[brand.end():]

    # Mark the tool-only topbar actions so the router can hide them on home.
    for fn in ('showHelp()', 'enterPresent()'):
        pat = re.compile(r'<button class="(btn|icon-btn)"(\s+onclick="' + re.escape(fn) + '")')
        html, n = pat.subn(r'<button class="\1 jpt-toolonly"\2', html, count=1)
        if not n:
            raise SystemExit(f'build: could not tag the {fn} button')

    # Sidebar: nav on top, the tool's own controls wrapped so they can be hidden.
    html = need(html, '<aside>', '<aside>')
    html = html.replace('<aside>\n    <div class="side-top">',
                        '<aside>\n    ' + NAV + '<div id="debatesSection">\n    <div class="side-top">', 1)
    html = html.replace('<div class="side-list" id="sideList"></div>\n  </aside>',
                        '<div class="side-list" id="sideList"></div>\n    </div>\n    ' + FOOT + '</aside>', 1)

    label = ('<!-- jpt:debateslabel --><div class="jt-label" style="margin-bottom:9px">'
             'Debates</div><!-- /jpt:debateslabel -->\n        ')
    before = '<div class="side-top">\n      <div class="searchwrap">'
    html = need(html, before, 'the sidebar search to label')
    html = html.replace(before, '<div class="side-top">\n      ' + label + '<div class="searchwrap">', 1)

    # Home view as a sibling of the tool's pane, and the tool's own header.
    # TOOL_HEAD must be the FIRST child of #cardHome: exitPresent puts the card
    # back with appendChild, so anything after it lands out of order.
    home = '<div class="main-inner" id="cardHome">'
    html = need(html, home, '#cardHome')
    html = html.replace(home, home_view() + '<div class="main-inner view" id="cardHome">'
                        + '\n      ' + TOOL_HEAD, 1)

    html = html.replace('</style>', CSS + '</style>', 1)
    html = html.replace('</body>', ROUTER + '</body>', 1)
    return html


def main():
    if len(sys.argv) > 1:
        incoming = pathlib.Path(sys.argv[1]).expanduser()
        if '<!-- jpt:brand -->' in incoming.read_text(encoding='utf-8'):
            raise SystemExit(
                f'build: {incoming} is already a built page, not the tool.\n'
                f'       Pass John\'s own file (~/Downloads/debate-builder.html), '
                f'or run with no argument to rebuild from src/.')
        SRC.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(incoming, SRC)
        print(f'  src updated from {incoming}')

    if not SRC.exists():
        raise SystemExit(f'build: no source at {SRC}. Pass the tool path once to seed it.')

    out = build(SRC.read_text(encoding='utf-8'))
    OUT.write_text(out, encoding='utf-8')

    for what, tag in [('brand', 'jpt:brand'), ('tools nav', 'jpt:toolsnav'),
                      ('side foot', 'jpt:sidefoot'), ('tool head', 'jpt:toolhead'),
                      ('debates label', 'jpt:debateslabel'), ('home view', 'jpt:homeview'),
                      ('router', 'jpt:router')]:
        assert out.count(f'<!-- {tag} -->') == 1, f'{what} not injected exactly once'
    for fn in ('renderDebate', 'enterPresent', 'paintSpot', 'setCardEditable'):
        assert f'function {fn}' in out, f'lost {fn} during build'
    assert 'c2_debate_bank_v1' in out, 'lost the debate store key'
    assert len(re.findall(r'class="[^"]*\bjpt-toolonly\b', out)) == 2, \
        'the help and Present buttons should be tagged tool-only'
    assert out.count('id="debatesSection"') == 1, 'debates section not wrapped'
    # The site is JohnPlusTools; the tool is named in the sidebar and main pane only.
    assert '<span class="b">Tools</span>' in out, 'brand should read Tools, not the tool name'
    assert out.index('jpt:toolhead') < out.index('id="debateCard"'), 'tool head is after the card'
    assert out.index('jpt:homeview') < out.index('id="cardHome"'), 'home view is after the tool pane'
    for dash in ('—', '–'):
        assert dash not in CSS + BRAND + NAV + FOOT + TOOL_HEAD + ROUTER + TITLE + DESC, \
            'dash crept into injected copy'
        assert dash not in HOME_TPL.read_text(encoding='utf-8'), 'dash in the home template'

    print(f'  wrote {OUT.relative_to(ROOT)}  ({len(out):,} bytes)  home + tool in one page')


if __name__ == '__main__':
    main()
