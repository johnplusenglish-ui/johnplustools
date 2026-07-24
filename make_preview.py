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
}

# Something that must be on screen afterwards, as proof the seed actually took.
PROOF = {
    'debate-builder': 'AI IN THE CLASSROOM',
    'speaking-topics': 'deck',
    'role-plays': 'Student A',
}

WRAPPER = """
<script>
/* preview-seed: temporary, written by make_preview.py, never committed */
(function () {
  function go() {
    try {
__SEED__
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
    seeded = WRAPPER.replace('__SEED__', SEEDS[slug]).replace('__THEME__', theme)
    i = build.sole_position(base, '</body>', 'the preview seed')
    tmp = ROOT / f'_pv-{slug}-{theme}.html'
    tmp.write_text(base[:i] + seeded + base[i:], encoding='utf-8')
    url = f'http://127.0.0.1:{PORT}/{tmp.name}'
    try:
        # Prove the seed ran before photographing. It once silently shot an
        # unseeded page after an element it clicked had been renamed.
        dom = subprocess.run([CHROME, '--headless', '--disable-gpu', '--dump-dom',
                              '--virtual-time-budget=8000', url],
                             check=True, capture_output=True, text=True).stdout
        if 'PREVIEW-OK' not in dom:
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
