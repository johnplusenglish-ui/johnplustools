/* Extract the diff functions straight out of the shipped HTML and exercise
   them, so the test runs the real code rather than a copy. */
const fs = require('fs');
const target = process.argv[2] || __dirname + '/../tools/corrections.html';
const html = fs.readFileSync(target, 'utf8');

const start = html.indexOf('/* ---------- word-level diff ---------- */');
const end   = html.indexOf('/* ---------- rendering ---------- */');
if (start === -1 || end === -1) { console.error('FAIL: could not locate diff section'); process.exit(1); }
const src = html.slice(start, end);
eval(src);   // defines tokenize, isParaBreak, diffTokens, push, esc, renderDiff

let pass = 0, fail = 0;
function check(label, got, want) {
  if (got === want) { pass++; console.log('  ok   ' + label); }
  else { fail++; console.log('  FAIL ' + label + '\n        got:  ' + JSON.stringify(got) + '\n        want: ' + JSON.stringify(want)); }
}
function contains(label, got, needle) {
  if (got.includes(needle)) { pass++; console.log('  ok   ' + label); }
  else { fail++; console.log('  FAIL ' + label + '\n        got:      ' + JSON.stringify(got) + '\n        expected: ' + JSON.stringify(needle)); }
}
function absent(label, got, needle) {
  if (!got.includes(needle)) { pass++; console.log('  ok   ' + label); }
  else { fail++; console.log('  FAIL ' + label + ' — should not contain ' + JSON.stringify(needle) + '\n        got: ' + JSON.stringify(got)); }
}

console.log('\n-- identical text --');
check('no del/ins when unchanged',
  renderDiff('The cat sat.', 'The cat sat.'), '<p>The cat sat.</p>');

console.log('\n-- single word substitution --');
{
  const r = renderDiff('I have a good idea.', 'I have a great idea.');
  contains('marks the removed word', r, '<del>good</del>');
  contains('marks the added word', r, '<ins>great</ins>');
  contains('keeps the unchanged head', r, 'I have a ');
  absent('does not re-mark unchanged words', r, '<del>I</del>');
}

console.log('\n-- pure insertion --');
{
  const r = renderDiff('I went home.', 'I went back home.');
  contains('inserts the new word', r, '<ins>');
  absent('nothing deleted', r, '<del>');
}

console.log('\n-- pure deletion --');
{
  const r = renderDiff('I went back home.', 'I went home.');
  contains('deletes the word', r, '<del>');
  absent('nothing inserted', r, '<ins>');
}

console.log('\n-- empty sides --');
contains('empty original is all insertion', renderDiff('', 'Hello there.'), '<ins>Hello there.</ins>');
contains('empty corrected is all deletion', renderDiff('Hello there.', ''), '<del>Hello there.</del>');
check('both empty renders nothing', renderDiff('', ''), '');

console.log('\n-- paragraphs --');
{
  const r = renderDiff('One two.\n\nThree four.', 'One two.\n\nThree five.');
  check('produces two paragraphs', (r.match(/<p>/g) || []).length, 2);
  contains('edits the second paragraph', r, '<ins>five.</ins>');
  check('first paragraph left untouched', r.startsWith('<p>One two.</p>'), true);
  // The real risk: a <del>/<ins> left open across a </p><p> boundary.
  check('no del/ins spans a paragraph boundary',
    /<(del|ins)>[^<]*<\/p>/.test(r), false);
}
{
  // A deletion that runs right up to a paragraph break must not leave a
  // <del> open across </p><p>.
  const r = renderDiff('Alpha bravo\n\nCharlie', 'Alpha\n\nCharlie');
  const opens = (r.match(/<del>/g) || []).length;
  const closes = (r.match(/<\/del>/g) || []).length;
  check('del tags balanced across break', opens, closes);
  absent('no del wrapping a paragraph tag', r, '<del></p>');
}

console.log('\n-- html escaping --');
{
  const r = renderDiff('a < b & c', 'a > b & c');
  absent('raw < from content is escaped', r, 'a < b');
  contains('ampersand escaped', r, '&amp;');
}
{
  const r = renderDiff('hi', '<script>alert(1)</script>');
  absent('injected script tag is neutralised', r, '<script>');
  contains('script tag shown as text', r, '&lt;script&gt;');
}

console.log('\n-- realistic sentence --');
{
  const r = renderDiff(
    'I enjoy to polish my work to the next level.',
    'I enjoy polishing my work to the next level.');
  contains('catches the gerund fix (del)', r, '<del>');
  contains('catches the gerund fix (ins)', r, '<ins>');
  const text = r.replace(/<[^>]+>/g, '');
  contains('unchanged tail preserved', text, 'my work to the next level.');
}

console.log('\n-- tag balance on a longer edit --');
{
  const a = 'The quick brown fox jumps over the lazy dog near the river bank every single morning.';
  const b = 'The quick red fox leaps over a lazy dog beside the river bank each morning.';
  const r = renderDiff(a, b);
  check('del balanced', (r.match(/<del>/g)||[]).length, (r.match(/<\/del>/g)||[]).length);
  check('ins balanced', (r.match(/<ins>/g)||[]).length, (r.match(/<\/ins>/g)||[]).length);
  check('p balanced',   (r.match(/<p>/g)||[]).length,   (r.match(/<\/p>/g)||[]).length);
  // Stripping ins and keeping del must reproduce the original text.
  const asOriginal = r.replace(/<ins>.*?<\/ins>/g, '').replace(/<[^>]+>/g, '').replace(/\s+/g,' ').trim();
  check('original reconstructable from diff', asOriginal, a);
  const asCorrected = r.replace(/<del>.*?<\/del>/g, '').replace(/<[^>]+>/g, '').replace(/\s+/g,' ').trim();
  check('corrected reconstructable from diff', asCorrected, b);
}

console.log('\n-- large input guard --');
{
  // Scattered edits throughout, so head/tail trimming cannot collapse it and
  // the DP table is genuinely exercised at essay length.
  const words = Array.from({length: 1200}, (_, i) => 'word' + i);
  const big = words.join(' ');
  const edited = words.map((w, i) => (i % 25 === 0 ? w.toUpperCase() : w)).join(' ');
  const t0 = Date.now();
  const r = renderDiff(big, edited);
  const ms = Date.now() - t0;
  contains('large diff marks a scattered change', r, 'WORD0');
  check('large diff del balanced', (r.match(/<del>/g)||[]).length, (r.match(/<\/del>/g)||[]).length);
  const back = r.replace(/<ins>.*?<\/ins>/g, '').replace(/<[^>]+>/g, '').replace(/\s+/g,' ').trim();
  check('large diff reconstructs the original', back, big);
  console.log('  info 1200-word scattered diff took ' + ms + 'ms');
  if (ms > 5000) { fail++; console.log('  FAIL large diff too slow'); } else pass++;
}

console.log('\n' + (fail === 0 ? 'ALL PASS' : 'FAILURES: ' + fail) + '  (' + pass + ' checks passed)');
process.exit(fail === 0 ? 0 : 1);
