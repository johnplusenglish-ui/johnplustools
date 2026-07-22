#!/usr/bin/env python3
"""Regenerate the landing page's preview screenshots of the Debate Builder.

Writes assets/debate-builder-{light,dark}.png by seeding the real tool with a
sample debate and photographing it in headless Chrome. Run after build.py when
the tool's look changes:

    python3 make_preview.py

Needs Google Chrome and a local server; it starts and stops its own.
"""
import http.server
import pathlib
import shutil
import socketserver
import subprocess
import threading

ROOT = pathlib.Path(__file__).parent
# Shoot the BUILT page, not src/, so the preview shows what a visitor actually
# gets: the tool with the site's nav and header around it. Run build.py first.
SRC = ROOT / 'tools' / 'debate-builder.html'
ASSETS = ROOT / 'assets'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
PORT = 8931

SEED = """
<script>
/* preview-seed: temporary, written by make_preview.py, never committed */
(function () {
  function go() {
    try {
      var d = state.debates[state.debates.length - 1];
      d.title    = 'AI IN THE CLASSROOM';
      d.question = 'Should schools ban AI tools, or teach students to use them well?';
      d.task     = 'Take a position, defend it for two minutes, then answer one objection.';
      d.bubbles  = ['banning it','the gap widens','assessment','thinking time'];
      renderDebate();
      renderSidebar();
      document.documentElement.setAttribute('data-theme', '__THEME__');
    } catch (e) { console.error('seed failed', e); }
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


def main():
    if not shutil.which(CHROME) and not pathlib.Path(CHROME).exists():
        raise SystemExit(f'make_preview: Chrome not found at {CHROME}')
    if not SRC.exists():
        raise SystemExit(f'make_preview: {SRC} missing. Run build.py first.')
    ASSETS.mkdir(exist_ok=True)
    base = SRC.read_text(encoding='utf-8')
    httpd = serve()
    try:
        for theme in ('light', 'dark'):
            tmp = ROOT / f'_pv-{theme}.html'
            i = base.lower().rfind('</body>')
            tmp.write_text(base[:i] + SEED.replace('__THEME__', theme) + base[i:], encoding='utf-8')
            raw = ROOT / f'_pv-{theme}.png'
            subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                            '--force-device-scale-factor=2', '--window-size=1280,600',
                            f'--screenshot={raw}', '--virtual-time-budget=7000',
                            f'http://127.0.0.1:{PORT}/_pv-{theme}.html'],
                           check=True, capture_output=True)
            out = ASSETS / f'debate-builder-{theme}.png'
            subprocess.run(['sips', '-Z', '1100', str(raw), '--out', str(out)],
                           check=True, capture_output=True)
            tmp.unlink(); raw.unlink()
            print(f'  wrote {out.relative_to(ROOT)}  ({out.stat().st_size:,} bytes)')
    finally:
        httpd.shutdown()


if __name__ == '__main__':
    main()
