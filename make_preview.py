#!/usr/bin/env python3
"""Regenerate the home page's preview screenshots of each tool.

Writes assets/<slug>-{light,dark}.png by seeding the built page with realistic
content and photographing it in headless Chrome. Run after build.py whenever a
tool's look changes:

    python3 make_preview.py            all tools
    python3 make_preview.py debate-builder

Shoots the BUILT page, not src/, so the preview shows what a visitor actually
gets, site chrome included. Needs Google Chrome; it starts its own server.
"""
import http.server
import pathlib
import re
import shutil
import socketserver
import subprocess
import sys
import threading

import build

ROOT = pathlib.Path(__file__).parent
ASSETS = ROOT / 'assets'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
PORT = 8931

# Per-tool seeding, so each preview shows the tool in use rather than empty.
# Each must leave the page in its "photograph me" state.
SEEDS = {
    'debate-builder': """
      var d = state.debates[state.debates.length - 1];
      d.title    = 'AI IN THE CLASSROOM';
      d.question = 'Should schools ban AI tools, or teach students to use them well?';
      d.task     = 'Take a position, defend it for two minutes, then answer one objection.';
      d.bubbles  = ['banning it','the gap widens','assessment','thinking time'];
      state.currentId = d.id;
      renderDebate();
      renderSidebar();
      if (!document.getElementById('debateCard')) throw new Error('no debate card');
    """,
    'speaking-topics': """
      selectTopic(0);
      if (!document.getElementById('deck').children.length) throw new Error('deck is empty');
    """,
    'role-plays': """
      rpSelect(2);
      if (document.getElementById('rpView').style.display === 'none') throw new Error('role-plays view is hidden');
    """,
    'vocab-matching': """
      vmLoadSet(1);
      vmSetMode('play');
      if (!document.querySelectorAll('.vm-cell').length) throw new Error('play columns empty');
    """,
    'gap-fill': """
      gfLoadStarter(4);
      gfSetMode('print');
      if (!document.querySelectorAll('.gf-print-blank').length) throw new Error('gap-fill print empty');
    """,
    'spin-wheel': """
      swNewWheel();
      document.getElementById('swNameInput').value = 'Class names (example)';
      swOnNameInput(document.getElementById('swNameInput'));
      document.getElementById('swTextarea').value = 'Alex\\nSam\\nJordan\\nTaylor\\nCasey\\nMorgan\\nRiley\\nQuinn';
      swOnTextareaInput();
      if (!document.querySelectorAll('.sw-label-text').length) throw new Error('wheel has no labels');
    """,
}

# Something that must be on screen afterwards, as proof the seed actually took.
PROOF = {
    'debate-builder': 'AI IN THE CLASSROOM',
    'speaking-topics': 'deck',
    'role-plays': 'Student A',
    'vocab-matching': 'boarding pass',
    'gap-fill': 'Word bank',
    'spin-wheel': 'Riley',
}

def _hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return '#%02x%02x%02x' % tuple(max(0, min(255, round(c))) for c in rgb)


def _blend(hex_color, target_rgb, amount):
    """hex_color shifted toward target_rgb by amount (0-1)."""
    r1, g1, b1 = _hex_to_rgb(hex_color)
    r2, g2, b2 = target_rgb
    return _rgb_to_hex((r1 + (r2 - r1) * amount, g1 + (g2 - g1) * amount, b1 + (b2 - b1) * amount))


# Each gallery card now tags its screenshot with its own PALETTE colour
# instead of the site's default blue, so the accent stripe / badge / preview
# read as one thing. --accent and --soft aren't separate hand-picked colours
# in CHROME_CSS, so a straight swap would leave the wash the wrong hue; both
# are derived here from the same PALETTE fill instead, same relationship the
# real blue tokens have to each other (light theme washes toward white, dark
# theme toward the dark card colour, which is what made the default palette
# read as blue everywhere in the first place).
_WHITE, _BLACK = (255, 255, 255), (0, 0, 0)
_DARK_CARD, _DARK_BG = (0x16, 0x21, 0x3a), (0x0f, 0x17, 0x28)


def accent_vars_css(fill, theme):
    if theme == 'dark':
        accent = _blend(fill, _WHITE, 0.28)
        accent_deep = _blend(fill, _WHITE, 0.45)
        soft = _blend(fill, _DARK_CARD, 0.82)
        soft_line = _blend(fill, _DARK_BG, 0.62)
    else:
        accent = fill
        accent_deep = _blend(fill, _BLACK, 0.16)
        soft = _blend(fill, _WHITE, 0.92)
        soft_line = _blend(fill, _WHITE, 0.82)
    # --level/--level-ink: the Debate Builder's own colour, independent of
    # --accent (its bubbles and phrase bank are levelled blue "on John's
    # call", not accent-linked). Same fill, so it still reads as the one
    # colour on screen; harmless no-op on every other tool, since none of
    # them define --level in the first place.
    return (f"documentElement.style.setProperty('--accent','{accent}');"
            f"documentElement.style.setProperty('--accent-deep','{accent_deep}');"
            f"documentElement.style.setProperty('--soft','{soft}');"
            f"documentElement.style.setProperty('--soft-line','{soft_line}');"
            f"documentElement.style.setProperty('--level','{accent}');"
            f"documentElement.style.setProperty('--level-ink','#fff');")


WRAPPER = """
<script>
/* preview-seed: temporary, written by make_preview.py, never committed */
(function () {
  function go() {
    try {
      var documentElement = document.documentElement;
__SEED__
      /* After the seed, not before: some tools' own render functions
         (e.g. the Debate Builder's applyLevelColour) set colour custom
         properties themselves as a side effect of rendering, and would
         clobber an earlier override right back to blue. */
__ACCENT_VARS__
      document.documentElement.setAttribute('data-theme', '__THEME__');
      document.title = 'PREVIEW-OK';
    } catch (e) { console.error('seed failed', e); document.title = 'PREVIEW-FAILED'; }
  }
  if (document.readyState === 'complete') go();
  else window.addEventListener('load', go);
})();
</script>
"""


def serve():
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(ROOT), **kw)
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    httpd.allow_reuse_address = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def shoot(slug, theme, httpd):
    page = ROOT / 'tools' / f'{slug}.html'
    if not page.exists():
        raise SystemExit(f'make_preview: {page} missing. Run build.py first.')
    base = page.read_text(encoding='utf-8')
    fill = build.PALETTE[build.BY_SLUG[slug]['accent']]['fill']
    seeded = (WRAPPER.replace('__ACCENT_VARS__', accent_vars_css(fill, theme))
                      .replace('__SEED__', SEEDS[slug]).replace('__THEME__', theme))
    i = build.sole_position(base, '</body>', 'the preview seed')
    tmp = ROOT / f'_pv-{slug}-{theme}.html'
    tmp.write_text(base[:i] + seeded + base[i:], encoding='utf-8')
    url = f'http://127.0.0.1:{PORT}/{tmp.name}'
    try:
        # Prove the seed ran before photographing. It once silently shot an
        # unseeded page after an element it clicked had been renamed.
        # Checking for the bare 'PREVIEW-OK' string is not enough: the
        # wrapper's own <script> text contains that literal substring
        # regardless of whether it ever executed, since --dump-dom
        # serialises script source verbatim. Check for the rendered
        # <title> tag specifically, plus the tool's own PROOF text.
        dom = subprocess.run([CHROME, '--headless', '--disable-gpu', '--dump-dom',
                              '--virtual-time-budget=8000', url],
                             check=True, capture_output=True, text=True).stdout
        if '<title>PREVIEW-OK</title>' not in dom or PROOF[slug] not in dom:
            raise SystemExit(f'make_preview: the seed for {slug} did not run. '
                             f'The preview would be of an empty tool.')
        raw = ROOT / f'_pv-{slug}-{theme}.png'
        subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                        '--force-device-scale-factor=2', '--window-size=1280,600',
                        f'--screenshot={raw}', '--virtual-time-budget=8000', url],
                       check=True, capture_output=True)
        out = ASSETS / f'{slug}-{theme}.png'
        subprocess.run(['sips', '-Z', '1100', str(raw), '--out', str(out)],
                       check=True, capture_output=True)
        raw.unlink()
        print(f'  wrote {out.relative_to(ROOT)}  ({out.stat().st_size:,} bytes)')
    finally:
        tmp.unlink(missing_ok=True)


def main():
    if not pathlib.Path(CHROME).exists() and not shutil.which(CHROME):
        raise SystemExit(f'make_preview: Chrome not found at {CHROME}')
    wanted = sys.argv[1:] or [t['slug'] for t in build.TOOLS]
    for slug in wanted:
        if slug not in SEEDS:
            raise SystemExit(f'make_preview: no seed defined for {slug}. '
                             f'Known: {", ".join(SEEDS)}')
    ASSETS.mkdir(exist_ok=True)
    httpd = serve()
    try:
        for slug in wanted:
            for theme in ('light', 'dark'):
                shoot(slug, theme, httpd)
    finally:
        httpd.shutdown()


if __name__ == '__main__':
    main()
