#!/usr/bin/env python3
"""Build index.html for johnplustools.com from the Debate Builder.

The homepage *is* the tool. Rather than hand-editing a merged copy (which would
drift every time John edits his own file), this takes his tool verbatim and
splices the site chrome into it: the JohnPlusTools brand, a Tools nav at the top
of the sidebar, and a link across to the dictionary.

    python3 build.py                 # from src/debate-builder.html
    python3 build.py ~/Downloads/debate-builder.html   # and refresh src/ too

Everything it injects is marked with jpt: comments, so it is easy to see what is
the site's and what is John's, and it re-runs cleanly over its own output.
"""
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / 'src' / 'debate-builder.html'
OUT = ROOT / 'index.html'

ICON = ('fill="none" stroke="currentColor" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true"')

SPANNER = (f'<svg viewBox="0 0 24 24" {ICON} stroke-width="2">'
           '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 '
           '7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>')

# John's own mark for the Debate Builder, reused on the nav item.
PROMPTS = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
           'stroke-linecap="round" aria-hidden="true">'
           '<circle cx="4.6" cy="6" r="2.1"/><line x1="10" y1="6" x2="21" y2="6"/>'
           '<circle cx="4.6" cy="12" r="2.1" fill="currentColor"/><line x1="10" y1="12" x2="21" y2="12"/>'
           '<circle cx="4.6" cy="18" r="2.1"/><line x1="10" y1="18" x2="21" y2="18"/></svg>')

BOOK = (f'<svg viewBox="0 0 24 24" {ICON} stroke-width="2">'
        '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>'
        '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>')

FAVICON = ("<link rel=\"icon\" href=\"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' "
           "viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='2' stroke-linecap='round' "
           "stroke-linejoin='round'><path d='M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 "
           "0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 "
           "7.94-7.94l-3.76 3.76z'/></svg>\">")

TITLE = '<title>John + Tools · free teaching tools for English classrooms</title>'

DESC = ('<meta name="description" content="Free browser tools for English teachers, by John of '
        'JohnPlusEnglish. First tool: the Debate Builder. No sign-up, nothing to install.">')

# The site is JohnPlusTools. The Debate Builder is a tool inside it, named in the
# sidebar and over the main pane, never in the brand.
BRAND = f'''<!-- jpt:brand -->
  <a href="/" class="st-brand">
    <span class="brand-icon">{SPANNER}</span>
    <span class="brand-title"><span class="k">JohnPlusEnglish</span><span class="b">Tools</span></span>
  </a>
  <!-- /jpt:brand -->'''

HEAD = f'''<!-- jpt:toolhead -->
      <div class="tool-head">
        <span class="th-icon">{PROMPTS}</span>
        <div class="th-text">
          <h1>Debate Builder</h1>
          <p>Build a speaking debate, then run it from the front of the room.</p>
        </div>
      </div>
      <!-- /jpt:toolhead -->
      '''

NAV = f'''<!-- jpt:toolsnav -->
    <div class="tools-nav">
      <div class="jt-label">Tools</div>
      <a class="tool-item active" href="/" aria-current="page">
        <span class="ti-icon">{PROMPTS}</span>
        <span class="ti-name">Debate Builder</span>
      </a>
    </div>
    <!-- /jpt:toolsnav -->
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
.tools-nav{padding:14px 16px 12px;border-bottom:1px solid var(--line)}
.jt-label{font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--muted);font-weight:700;margin-bottom:9px}
.tool-item{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:11px;
  border:1px solid transparent;text-decoration:none;color:var(--ink);
  transition:background .12s,border-color .12s}
.tool-item:hover{background:var(--soft)}
.tool-item.active{background:var(--soft);border-color:var(--accent)}
.ti-icon{width:28px;height:28px;border-radius:8px;flex-shrink:0;display:grid;place-items:center;
  background:var(--soft);border:1px solid var(--soft-line);color:var(--accent)}
.tool-item.active .ti-icon{background:var(--accent);border-color:var(--accent);color:#fff}
.ti-icon svg{width:15px;height:15px;display:block}
.ti-name{font-size:13.5px;font-weight:600;letter-spacing:-.01em}
/* Names the tool inside the site, so the page reads JohnPlusTools first. */
.tool-head{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.th-icon{width:38px;height:38px;border-radius:11px;flex-shrink:0;display:grid;place-items:center;
  background:var(--soft);border:1px solid var(--soft-line);color:var(--accent)}
.th-icon svg{width:20px;height:20px;display:block}
.th-text h1{font-size:19px;font-weight:700;letter-spacing:-.02em;margin:0;line-height:1.2}
.th-text p{font-size:12.5px;color:var(--muted);margin:2px 0 0;line-height:1.4}
@media print{.tool-head{display:none}}
@media (max-width:900px){.th-text p{display:none}}
.side-foot{padding:10px 12px 12px;border-top:1px solid var(--line);flex-shrink:0}
.side-foot a{display:flex;align-items:center;gap:8px;text-decoration:none;font-size:12.5px;
  font-weight:600;color:var(--muted);padding:8px 10px;border-radius:10px;transition:.12s}
.side-foot a:hover{background:var(--soft);color:var(--accent)}
.side-foot a svg{width:15px;height:15px;flex-shrink:0}
@media (max-width:900px){.tools-nav{padding:12px 14px 10px}}
/* /jpt:chrome */
'''


def drop(html, tag):
    """Remove a previously injected block, so the build is re-runnable."""
    return re.sub(rf'<!-- {tag} -->.*?<!-- /{tag} -->\n?\s*', '', html, flags=re.S)


def build(html):
    # Strip anything a previous run (or the old back-link injector) added.
    for tag in ('jpt:brand', 'jpt:toolsnav', 'jpt:sidefoot', 'jpt:toolhead',
                'jpt:debateslabel', 'jpt:backlink'):
        html = drop(html, tag)
    html = re.sub(r'/\* jpt:chrome \*/.*?/\* /jpt:chrome \*/\n?', '', html, flags=re.S)

    # Head
    html = re.sub(r'<title>.*?</title>', TITLE, html, count=1, flags=re.S)
    if 'name="description"' not in html:
        html = html.replace(TITLE, TITLE + '\n' + DESC, 1)
    if 'rel="icon"' not in html:
        html = html.replace(TITLE, TITLE + '\n' + FAVICON, 1)

    # Brand: replace the tool's own non-linking brand with one that points home.
    brand = re.search(r'<a href="#" class="st-brand".*?</a>', html, re.S)
    if not brand:
        raise SystemExit('build: could not find the brand link to replace')
    html = html[:brand.start()] + BRAND + html[brand.end():]

    # Sidebar: nav above the search, dictionary link pinned at the bottom.
    if '<aside>' not in html:
        raise SystemExit('build: could not find <aside>')
    html = html.replace('<aside>\n    <div class="side-top">',
                        '<aside>\n    ' + NAV + '<div class="side-top">', 1)
    html = html.replace('<div class="side-list" id="sideList"></div>\n  </aside>',
                        '<div class="side-list" id="sideList"></div>\n    ' + FOOT + '</aside>', 1)

    # Label the debate controls, so they read as belonging to the selected tool
    # rather than to the site.
    label = ('<!-- jpt:debateslabel --><div class="jt-label" style="margin-bottom:9px">'
             'Debates</div><!-- /jpt:debateslabel -->\n        ')
    before = '<div class="side-top">\n      <div class="searchwrap">'
    if before not in html:
        raise SystemExit('build: could not find the sidebar search to label')
    html = html.replace(before, '<div class="side-top">\n      ' + label + '<div class="searchwrap">', 1)

    # Name the tool over the main pane. Must go FIRST inside #cardHome: exitPresent
    # appends the card back with appendChild, so anything after it lands out of order.
    home = '<div class="main-inner" id="cardHome">'
    if home not in html:
        raise SystemExit('build: could not find #cardHome')
    html = html.replace(home, home + '\n      ' + HEAD, 1)

    # Styles
    html = html.replace('</style>', CSS + '</style>', 1)
    return html


def main():
    if len(sys.argv) > 1:
        incoming = pathlib.Path(sys.argv[1]).expanduser()
        # Refuse a built page as input. It would overwrite the pristine source
        # with output, and there would be no clean copy left to rebuild from.
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

    for label, needle in [('brand', 'jpt:brand'), ('tools nav', 'jpt:toolsnav'),
                          ('side foot', 'jpt:sidefoot'), ('tool head', 'jpt:toolhead'),
                          ('debates label', 'jpt:debateslabel')]:
        assert out.count(f'<!-- {needle} -->') == 1, f'{label} not injected exactly once'
    for fn in ('renderDebate', 'enterPresent', 'paintSpot', 'setCardEditable'):
        assert f'function {fn}' in out, f'lost {fn} during build'
    assert 'c2_debate_bank_v1' in out, 'lost the debate store key'
    for dash in ('—', '–'):
        assert dash not in CSS + BRAND + NAV + FOOT + HEAD + TITLE + DESC, \
            'dash crept into injected copy'
    # The site is JohnPlusTools; the tool is named in the sidebar and main pane only.
    assert '<span class="b">Tools</span>' in out, 'brand should read Tools, not the tool name'
    # The tool header must precede the card, or exitPresent reorders the pane.
    assert out.index('jpt:toolhead') < out.index('id="debateCard"'), 'tool head is after the card'

    print(f'  wrote {OUT.relative_to(ROOT)}  ({len(out):,} bytes)')


if __name__ == '__main__':
    main()
