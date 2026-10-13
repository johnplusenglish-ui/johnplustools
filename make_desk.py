#!/usr/bin/env python3
"""Build the private Teaching Desk page: tools/class-schedule.html.

Source of truth is ~/Downloads/class-schedule.html (John's local tool, no lock).
This script copies it, adds an unlock screen, and writes the result into the site.
It sits outside build.py on purpose: the page is standalone, unlisted, and keeps
its own johnplusenglish look instead of the shared JohnPlusTools shell.

The unlock code is never stored. Only a PBKDF2-SHA256 hash and a random salt go
into the page. This is a soft lock (the hash is visible in the page source), good
for keeping a casual visitor out. The student data itself lives only in the
browser's localStorage on John's device, never on the site.

Usage:
    DESK_CODE='the-code' python3 make_desk.py
Re-running with a different code replaces the lock; devices unlocked with the old
code are asked again, because the remembered value is the hash itself.
"""
import hashlib, os, re, secrets, sys
from pathlib import Path

SRC = Path.home() / 'Downloads' / 'class-schedule.html'
OUT = Path(__file__).resolve().parent / 'tools' / 'class-schedule.html'
ITER = 200_000

code = os.environ.get('DESK_CODE', '').strip().lower()
if len(code) < 4:
    sys.exit('Set DESK_CODE to the unlock code (at least 4 characters).')

salt = secrets.token_bytes(16)
digest = hashlib.pbkdf2_hmac('sha256', code.encode('utf-8'), salt, ITER, dklen=32).hex()
salt_hex = salt.hex()

html = SRC.read_text(encoding='utf-8')
assert 'jpt:desk-lock' not in html, 'source already carries a lock; use the pristine Downloads file'

HEAD = f'''<!-- jpt:desk-lock -->
<meta name="robots" content="noindex,nofollow">
<style>
html.locked .top,html.locked main,html.locked footer{{display:none!important}}
#lock{{display:none;position:fixed;inset:0;z-index:200;align-items:center;justify-content:center;padding:20px;background:var(--cream)}}
html.locked #lock{{display:flex}}
.lockcard{{background:#fff;border:1px solid var(--border);border-radius:var(--r);box-shadow:var(--sh-md);width:100%;max-width:380px;padding:34px 30px 30px;text-align:center}}
.lockcard .logo{{font-size:1.5rem;justify-content:center;margin-bottom:6px}}
.lockcard .logo svg{{width:28px;height:28px}}
.lockcard h1{{margin:18px 0 6px;font-size:21px;font-weight:700}}
.lockcard p{{margin:0 0 20px;color:var(--muted);font-size:14.5px;line-height:1.5}}
.lockcard input{{width:100%;text-align:center;font-size:18px;letter-spacing:.12em;padding:12px 14px;border:1px solid var(--border);border-radius:var(--r-sm);background:#fff;outline:none}}
.lockcard input:focus{{border-color:var(--sky);box-shadow:0 0 0 3px var(--sky-tint)}}
.lockcard .btn{{width:100%;margin-top:12px}}
.lockcard .lerr{{min-height:20px;margin-top:12px;font-size:13.5px;color:var(--coral-d)}}
.lockcard.shake{{animation:lkshake .35s}}
@keyframes lkshake{{25%{{transform:translateX(-7px)}}75%{{transform:translateX(7px)}}}}
</style>
<script>(function(){{var ok=false;try{{ok=localStorage.getItem('jpt_desk_ok')==='{digest}'}}catch(e){{}}if(!ok)document.documentElement.classList.add('locked')}})();</script>
<!-- /jpt:desk-lock -->
'''

BODY = '''<!-- jpt:desk-lock -->
<div id="lock" role="dialog" aria-modal="true" aria-labelledby="lockTitle">
  <form class="lockcard" id="lockForm" autocomplete="off">
    <div class="logo"><svg><use href="#cap"/></svg><span>john<b>plus</b>english</span></div>
    <h1 id="lockTitle">Teaching Desk</h1>
    <p>This page is private. Enter your unlock code to open the timetable, groups and inquiries.</p>
    <input type="password" id="lockInput" placeholder="Unlock code" aria-label="Unlock code" autocomplete="off" autocapitalize="off" spellcheck="false">
    <button class="btn" type="submit">Unlock</button>
    <div class="lerr" id="lockErr" role="alert"></div>
  </form>
</div>
<!-- /jpt:desk-lock -->
'''

SCRIPT = f'''<!-- jpt:desk-lock -->
<script>
(function(){{
  var SALT='{salt_hex}',ITER={ITER},HASH='{digest}',KEYV='jpt_desk_ok';
  var root=document.documentElement,form=document.getElementById('lockForm'),inp=document.getElementById('lockInput'),err=document.getElementById('lockErr');
  var fails=0,waitUntil=0;
  function hex(b){{return Array.prototype.map.call(new Uint8Array(b),function(x){{return ('0'+x.toString(16)).slice(-2)}}).join('')}}
  function bytes(h){{var a=new Uint8Array(h.length/2);for(var i=0;i<a.length;i++)a[i]=parseInt(h.substr(i*2,2),16);return a}}
  function derive(code){{
    var enc=new TextEncoder();
    return crypto.subtle.importKey('raw',enc.encode(code),'PBKDF2',false,['deriveBits'])
      .then(function(k){{return crypto.subtle.deriveBits({{name:'PBKDF2',salt:bytes(SALT),iterations:ITER,hash:'SHA-256'}},k,256)}})
      .then(hex);
  }}
  function lock(){{try{{localStorage.removeItem(KEYV)}}catch(e){{}}inp.value='';err.textContent='';root.classList.add('locked');setTimeout(function(){{inp.focus()}},50)}}
  form.addEventListener('submit',function(e){{
    e.preventDefault();
    if(!window.crypto||!crypto.subtle){{err.textContent='This browser cannot check the code. Open the page over https in a current browser.';return}}
    var now=Date.now();
    if(now<waitUntil){{err.textContent='Please wait a few seconds and try again.';return}}
    derive(inp.value.trim().toLowerCase()).then(function(h){{
      if(h===HASH){{try{{localStorage.setItem(KEYV,HASH)}}catch(e){{}}root.classList.remove('locked');err.textContent='';inp.value=''}}
      else{{
        fails++;waitUntil=Date.now()+Math.min(fails,6)*1000;
        err.textContent='That code is not right.';
        form.classList.remove('shake');void form.offsetWidth;form.classList.add('shake');
        inp.select();
      }}
    }});
  }});
  var btn=document.getElementById('lockBtn');if(btn)btn.addEventListener('click',lock);
  if(root.classList.contains('locked'))setTimeout(function(){{inp.focus()}},50);
}})();
</script>
<!-- /jpt:desk-lock -->
'''

def once(haystack, needle):
    assert haystack.count(needle) == 1, f'expected exactly one {needle!r}'
    return haystack.index(needle)

# 1. head: right after the meta viewport
i = once(html, '<meta name="viewport" content="width=device-width, initial-scale=1">')
j = html.index('>', i) + 1
html = html[:j] + '\n' + HEAD + html[j:]

# 2. overlay: straight after <body>
i = once(html, '<body>')
html = html[:i + 6] + '\n' + BODY + html[i + 6:]

# 3. Lock button in the header, before Export
btn = '<button class="btn sec sm" id="lockBtn" title="Lock this page on this device">Lock</button>\n    '
i = once(html, '<div class="dmenu-wrap">')
html = html[:i] + btn + html[i:]

# 4. unlock script just before </body> (the app script is the last <script>, no
#    </body> appears inside any JS string in this page)
i = once(html, '</body>')
html = html[:i] + SCRIPT + html[i:]

# proof markers
assert html.count('jpt:desk-lock -->') == 6, 'lock blocks not injected exactly three times'
assert 'id="lockBtn"' in html and digest in html
assert code not in html.replace(digest, ''), 'plain code leaked into the page'
for ch in ('—', '–'):
    assert ch not in html, 'em or en dash found'

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(html, encoding='utf-8')
# The site is served by GitHub Pages, which has no redirect engine, so the short
# URL (/class-schedule) works through a folder index, same as the TOOLS pages.
SHORT = OUT.parent.parent / 'class-schedule' / 'index.html'
SHORT.parent.mkdir(exist_ok=True)
SHORT.write_text(html, encoding='utf-8')
print(f'wrote {OUT}  ({len(html):,} bytes)  hash {digest[:12]}...')
