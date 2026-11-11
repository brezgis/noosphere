'use strict';
/* noosphere. A one-reader dashboard.
 *
 * Every stream is treated as a blog that this dashboard follows. Cards from
 * the feed become posts of one of seven kinds (text, photo, quote, link,
 * chat, audio, video), and an "echo" card is shown as a reblog.
 *
 * No build step. The feed is /api/feed, a static JSON file in production.
 */

// ---------------------------------------------------------------- utilities

const $ = (sel, root = document) => root.querySelector(sel);

function esc(v) {
  return String(v == null ? '' : v)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function safeUrl(u) {
  u = String(u || '').trim();
  return /^https?:\/\//i.test(u) ? esc(u) : '';
}

// Old cards carry model-written HTML and stray markdown. This keeps a short
// list of harmless tags, drops every attribute except a link's href, and
// turns everything else into text.
const ALLOWED = new Set(['P', 'BR', 'EM', 'I', 'STRONG', 'B', 'UL', 'OL', 'LI', 'H1', 'H2', 'H3', 'H4', 'SUP', 'A', 'BLOCKQUOTE']);
function cleanHtml(html) {
  if (!html) return '';
  const src = String(html)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[\s(])\*([^*\n]+?)\*(?=[\s).,;:!?]|$)/g, '$1<em>$2</em>')
    .replace(/\n{2,}/g, '<br><br>');
  const doc = new DOMParser().parseFromString('<div>' + src + '</div>', 'text/html');
  const walk = node => {
    let out = '';
    node.childNodes.forEach(n => {
      if (n.nodeType === 3) { out += esc(n.nodeValue); return; }
      if (n.nodeType !== 1) return;
      const tag = n.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE') return;
      const inner = walk(n);
      if (!ALLOWED.has(tag)) { out += inner; return; }
      if (tag === 'BR') { out += '<br>'; return; }
      if (tag === 'A') {
        const href = safeUrl(n.getAttribute('href'));
        out += href ? `<a href="${href}" target="_blank" rel="noopener">${inner}</a>` : inner;
        return;
      }
      const t = (tag === 'H1' || tag === 'H2') ? 'h3' : tag.toLowerCase();
      out += `<${t}>${inner}</${t}>`;
    });
    return out;
  };
  return walk(doc.body.firstChild).replace(/(?:\s*<br>\s*){3,}/g, '<br><br>').replace(/^(?:\s*<br>\s*)+|(?:\s*<br>\s*)+$/g, '');
}

function plain(html) {
  const d = new DOMParser().parseFromString('<div>' + String(html || '') + '</div>', 'text/html');
  return d.body.textContent || '';
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

function parseTs(ts) {
  // Feed timestamps are naive local times ("2026-11-11T08:00:00").
  const m = /^(\d{4})-(\d\d)-(\d\d)(?:T(\d\d):(\d\d))?/.exec(ts || '');
  if (!m) return new Date(NaN);
  return new Date(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0));
}
function clock(d) {
  let h = d.getHours();
  const ap = h < 12 ? 'am' : 'pm';
  h = h % 12 || 12;
  return `${h}:${String(d.getMinutes()).padStart(2, '0')} ${ap}`;
}
function dayKey(d) { return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`; }
function dayLabel(d) {
  const now = new Date();
  const y = new Date(now); y.setDate(now.getDate() - 1);
  if (dayKey(d) === dayKey(now)) return 'Today';
  if (dayKey(d) === dayKey(y)) return 'Yesterday';
  const yr = d.getFullYear() === now.getFullYear() ? '' : `, ${d.getFullYear()}`;
  return `${DAYS[d.getDay()]}, ${MONTHS[d.getMonth()]} ${d.getDate()}${yr}`;
}
function shortDate(d) { return `${MONTHS[d.getMonth()].slice(0, 3)} ${d.getDate()}`; }
function ago(d) {
  const days = Math.round((new Date().setHours(0, 0, 0, 0) - new Date(d).setHours(0, 0, 0, 0)) / 864e5);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 7) return `${days} days ago`;
  if (days < 14) return 'last week';
  return shortDate(d);
}

const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem(key); return v == null ? fallback : JSON.parse(v); }
    catch (e) { return fallback; }
  },
  set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {} },
};

// ------------------------------------------------------------------ streams

const KINDS = {
  text:  { label: 'Text',  icon: '<text x="20" y="28" text-anchor="middle" font-family="Georgia,serif" font-weight="700" font-size="25">Aa</text>' },
  photo: { label: 'Photo', icon: '<path d="M6 12h6l2.500-4h11L28 12h6v19H6z"/><circle cx="20" cy="21" r="6" fill="#fff"/><circle cx="20" cy="21" r="3.200"/>' },
  quote: { label: 'Quote', icon: '<path d="M7 28V19c0-6 3-10 9-11v4c-3 1-4 3-4 6h4v10zm15 0V19c0-6 3-10 9-11v4c-3 1-4 3-4 6h4v10z"/>' },
  link:  { label: 'Link',  icon: '<g fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"><path d="M17 23a6 6 0 0 0 8.500 0l5-5a6 6 0 0 0-8.500-8.500l-2 2"/><path d="M23 17a6 6 0 0 0-8.500 0l-5 5a6 6 0 0 0 8.500 8.500l2-2"/></g>' },
  chat:  { label: 'Chat',  icon: '<path d="M5 8h30v19H19l-8 7v-7H5z"/><g fill="#fff"><circle cx="13" cy="17.500" r="2.300"/><circle cx="20" cy="17.500" r="2.300"/><circle cx="27" cy="17.500" r="2.300"/></g>' },
  audio: { label: 'Audio', icon: '<path d="M6 30V20a14 14 0 0 1 28 0v10" fill="none" stroke="currentColor" stroke-width="4"/><rect x="5" y="21" width="8" height="13" rx="2.500"/><rect x="27" y="21" width="8" height="13" rx="2.500"/>' },
  video: { label: 'Video', icon: '<rect x="5" y="10" width="21" height="20" rx="3"/><path d="M27 18l8-5v14l-8-5z"/>' },
};

const av = (bg, inner) =>
  `<svg viewBox="0 0 64 64" role="img" aria-hidden="true"><rect width="64" height="64" fill="${bg}"/>${inner}</svg>`;
const glyph = (ch, fill, extra = '') =>
  `<text x="32" y="45" text-anchor="middle" font-size="38" fill="${fill}" font-family="Georgia,'Times New Roman',serif" ${extra}>${ch}</text>`;

const ME = {
  blog: 'noosphere',
  avatar: av('#22364b', '<g fill="none" stroke="#e8eef5" stroke-width="2.500"><circle cx="32" cy="32" r="21"/><circle cx="32" cy="32" r="13"/></g><circle cx="32" cy="32" r="5" fill="#f2992e"/>'),
};

const STREAMS = {
  weather: { blog: 'lyrical-weather', name: 'Lyrical Weather', kind: 'text',
    about: 'The Boston forecast in the forecasters’ own words.',
    avatar: av('#8cbfe0', '<circle cx="42" cy="24" r="11" fill="#ffd66b"/><g fill="#fff"><circle cx="24" cy="38" r="10"/><circle cx="36" cy="40" r="8"/><circle cx="14" cy="42" r="6"/><rect x="14" y="40" width="24" height="8"/></g>') },
  wittgenstein: { blog: 'wittgensteins-ladder', name: 'Wittgenstein’s Ladder', kind: 'quote',
    about: 'The Tractatus, one proposition a day.',
    avatar: av('#efe6d2', '<g stroke="#4a3f35" stroke-width="3.500" stroke-linecap="round"><path d="M22 8 20 56M42 8l2 48"/><path d="M22 17h20M21.500 28h21M21 39h22M20.500 50h23" stroke-width="3"/></g>') },
  russian: { blog: 'russkiy-chas', name: 'Русский час', kind: 'quote',
    about: 'One sentence of Russian literature a day.',
    avatar: av('#c64b3f', glyph('Я', '#fff', 'font-weight="700"')) },
  untranslatable: { blog: 'the-untranslatable', name: 'The Untranslatable', kind: 'text',
    about: 'Words that English needs a sentence for.',
    avatar: av('#7b62a8', glyph('≠', '#fff')) },
  corpus_surprise: { blog: 'corpus-surprise', name: 'Corpus Surprise', kind: 'quote',
    about: 'One sentence pulled at random from 130,000.',
    avatar: av('#4f9d79', glyph('¶', '#fff')) },
  annotation: { blog: 'commonplace-book', name: 'The Commonplace Book', kind: 'text',
    about: 'A paragraph from an old novel, once a week.',
    avatar: av('#b98d58', '<path d="M32 18c-6-4-13-4-19-2v30c6-2 13-2 19 2 6-4 13-4 19-2V16c-6-2-13-2-19 2z" fill="#fff8ea"/><path d="M32 18v30" stroke="#b98d58" stroke-width="2"/>') },
  entropy_garden: { blog: 'entropy-garden', name: 'Entropy Garden', kind: 'video',
    about: 'A small simulation that grows while you watch.',
    avatar: av('#1e1e2e', '<g fill="#a6e3a1"><rect x="26" y="14" width="9" height="9"/><rect x="37" y="25" width="9" height="9"/><rect x="15" y="36" width="9" height="9"/><rect x="26" y="36" width="9" height="9"/><rect x="37" y="36" width="9" height="9"/></g>') },
  apophenia: { blog: 'apophenia-machine', name: 'Apophenia Machine', kind: 'link',
    about: 'Two unrelated things and one question.',
    avatar: av('#f0c24a', '<path d="M17 44 47 20" stroke="#5b4300" stroke-width="2.500" stroke-dasharray="3 5" stroke-linecap="round"/><circle cx="17" cy="44" r="8" fill="#5b4300"/><circle cx="47" cy="20" r="8" fill="#fff"/>') },
  dead_medium: { blog: 'the-dead-medium', name: 'The Dead Medium', kind: 'text',
    about: 'An obituary page for communication technology.',
    avatar: av('#4b4f58', '<rect x="10" y="18" width="44" height="29" rx="3" fill="#d9dce2"/><rect x="17" y="24" width="30" height="12" rx="2" fill="#4b4f58"/><circle cx="25" cy="30" r="3.500" fill="#d9dce2"/><circle cx="39" cy="30" r="3.500" fill="#d9dce2"/>') },
  painting: { blog: 'midday-museum', name: 'Midday Museum', kind: 'photo',
    about: 'One public-domain painting from Chicago at lunch.',
    avatar: av('#b8893a', '<rect x="9" y="12" width="46" height="40" fill="#f7efdc"/><rect x="15" y="18" width="34" height="28" fill="#9fc6dc"/><path d="M15 46l11-14 8 9 6-6 9 11z" fill="#57805a"/><circle cx="41" cy="25" r="3.500" fill="#f6d36b"/>') },
  postcard: { blog: 'midnight-postcard', name: 'Midnight Postcard', kind: 'photo',
    about: 'One photograph, late, with no caption.',
    avatar: av('#1d2a4d', '<circle cx="31" cy="31" r="15" fill="#f4e9b8"/><circle cx="38" cy="26" r="13" fill="#1d2a4d"/><g fill="#f4e9b8"><circle cx="48" cy="44" r="1.600"/><circle cx="14" cy="16" r="1.300"/><circle cx="50" cy="14" r="1.300"/></g>') },
  git_log: { blog: 'git-log-oneline', name: 'git log --oneline', kind: 'chat',
    about: 'What other people committed today.',
    avatar: av('#16181d', '<text x="9" y="41" font-family="\'Courier New\',monospace" font-weight="700" font-size="26" fill="#7ee081">$_</text>') },
  penny_red: { blog: 'the-penny-red', name: 'The Penny Red', kind: 'text',
    about: 'Places that were renamed, erased or argued over.',
    avatar: av('#f3ece0', '<rect x="11" y="9" width="42" height="46" fill="#b5483a" stroke="#f3ece0" stroke-width="4" stroke-dasharray="1 4.600" stroke-linecap="round"/><text x="32" y="41" text-anchor="middle" font-family="Georgia,serif" font-size="21" fill="#f3ece0">1d</text>') },
  the_diff: { blog: 'the-diff', name: 'The Diff', kind: 'chat',
    about: 'One passage in two or three languages.',
    avatar: av('#f1f3f5', '<path d="M0 0h32v64H0z" fill="#f9d2cf"/><path d="M32 0h32v64H32z" fill="#cdeccd"/><path d="M9 32h14" stroke="#b03a30" stroke-width="5"/><path d="M41 32h14M48 25v14" stroke="#2f7d3b" stroke-width="5"/>') },
  typeface: { blog: 'typeface-of-the-week', name: 'Typeface of the Week', kind: 'photo',
    about: 'A typeface and where it came from.',
    avatar: av('#fff', '<text x="32" y="44" text-anchor="middle" font-family="Georgia,serif" font-size="34" fill="#16181d">Aa</text><path d="M8 52h48" stroke="#e0483e" stroke-width="2"/>') },
  recipe: { blog: 'the-recipe-box', name: 'The Recipe Box', kind: 'photo',
    about: 'A real recipe and the history of one word in it.',
    avatar: av('#ee8d4b', '<path d="M32 12c12 0 21 8 20 20s-10 21-21 20-20-10-19-22 8-18 20-18z" fill="#fff"/><circle cx="33" cy="33" r="9" fill="#f7c531"/>') },
  music_rec: { blog: 'you-should-hear-this', name: 'You Should Hear This', kind: 'audio',
    about: 'One song a day that is not in the library yet.',
    avatar: av('#a77dc2', '<circle cx="32" cy="32" r="22" fill="#1b1b1f"/><circle cx="32" cy="32" r="15" fill="none" stroke="#3a3a42" stroke-width="2"/><circle cx="32" cy="32" r="8" fill="#f2992e"/><circle cx="32" cy="32" r="2" fill="#1b1b1f"/>') },
  monthly_playlist: { blog: 'monthly-mixtape', name: 'Monthly Mixtape', kind: 'audio',
    about: 'Last month’s songs on one tape.',
    avatar: av('#e0709a', '<rect x="9" y="17" width="46" height="31" rx="3" fill="#fff"/><rect x="15" y="22" width="34" height="14" rx="7" fill="#e0709a"/><circle cx="23" cy="29" r="4" fill="#fff"/><circle cx="41" cy="29" r="4" fill="#fff"/><path d="M19 48l3-6h20l3 6z" fill="#e0709a"/>') },
  language: { blog: 'a-language-a-day', name: 'A Language a Day', kind: 'text',
    about: 'One language from the World Atlas of Language Structures.',
    avatar: av('#2f8f8b', '<g fill="none" stroke="#fff" stroke-width="2.500"><circle cx="32" cy="32" r="20"/><ellipse cx="32" cy="32" rx="9" ry="20"/><path d="M12 32h40M15 22h34M15 42h34"/></g>') },
  poem: { blog: 'the-night-poem', name: 'The Night Poem', kind: 'text',
    about: 'A short poem, three evenings a week.',
    avatar: av('#2c2a4a', '<rect x="27" y="30" width="10" height="22" rx="1.500" fill="#f3ead7"/><path d="M32 12c5 6 6 9 6 12a6 6 0 0 1-12 0c0-3 1-6 6-12z" fill="#f6b23e"/><path d="M20 52h24" stroke="#f3ead7" stroke-width="3" stroke-linecap="round"/>') },
  link: { blog: 'open-tabs', name: 'Open Tabs', kind: 'link',
    about: 'One thing to read from a short list of blogs.',
    avatar: av('#56bc8a', '<g fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"><path d="M28 36a8 8 0 0 0 11 0l8-8a8 8 0 0 0-11-11l-3 3"/><path d="M36 28a8 8 0 0 0-11 0l-8 8a8 8 0 0 0 11 11l3-3"/></g>') },
};
STREAMS.diff = STREAMS.the_diff;

const UNKNOWN = { blog: 'unsorted', name: 'Unsorted', kind: 'text', about: '', avatar: av('#8c96a3', glyph('?', '#fff')) };
const streamOf = type => STREAMS[type] || UNKNOWN;

// --------------------------------------------------------------------- tags

function firstPart(s) { return plain(s || '').split(',')[0].trim(); }

function tagsFor(it) {
  const t = [];
  const add = (...xs) => xs.forEach(x => { if (x != null && x !== '') t.push(String(x)); });
  switch (it.type) {
    case 'weather': add('weather', it.place, it.summary); break;
    case 'wittgenstein': add('tractatus', 'wittgenstein', it.number); break;
    case 'russian': add('русский', firstPart(it.source)); break;
    case 'corpus_surprise': add(it.language || (it.corpus || '').replace(/^Leipzig\s+/, ''), it.register, 'found sentence'); break;
    case 'annotation': add(it.author || firstPart(it.source), it.title, it.year); break;
    case 'untranslatable': add(plain(it.language).split('(')[0], 'untranslatable'); break;
    case 'dead_medium': add('dead media', it.wiki_title); break;
    case 'penny_red': add('place names', it.country, ...(it.formerly || [])); break;
    case 'the_diff': case 'diff':
      add('translation', ...(it.texts || []).map(x => String(x.lang || '').split('(')[0].split('/')[0])); break;
    case 'typeface': add('typography', it.font_name); break;
    case 'recipe': add('recipe', it.area, it.category, it.word && it.word.term); break;
    case 'apophenia': add('apophenia', ...(it.items || [it.item_a, it.item_b]).filter(Boolean).map(x => x.kind || x.type)); break;
    case 'git_log': add('git log', ...(it.commits || []).map(c => c.repo)); break;
    case 'painting': add(it.artist, it.date, it.origin, 'painting'); break;
    case 'postcard': add('postcard', it.query); break;
    case 'music_rec': add('music', it.artist, it.year); break;
    case 'monthly_playlist': add('mixtape', it.month); break;
    case 'language': add(it.family, it.macroarea, ...(it.countries || []).slice(0, 2), 'wals'); break;
    case 'poem': add('poetry', it.author); break;
    case 'link': add(it.site, 'reading'); break;
    case 'entropy_garden': add('generative', ({ dla: 'diffusion', flow_field: 'flow field', cellular: 'rule 110', game_of_life: 'game of life' })[it.algorithm] || it.algorithm); break;
  }
  if (it.echo) add(it.echo_note || 'from the archive');
  const seen = new Set();
  return t.map(x => x.toLowerCase().replace(/\s+/g, ' ').trim())
    .filter(x => x && x.length <= 42 && !seen.has(x) && seen.add(x)).slice(0, 6);
}

// ---------------------------------------------------------------- renderers
// Each returns { body, source } where body is trusted HTML built from escaped
// pieces and source is an optional { label, url } shown in the post header.

const para = text => String(text || '').split(/\n{2,}/).map(p => p.trim()).filter(Boolean)
  .map(p => `<p>${esc(p)}</p>`).join('');
const srcLine = html => html ? `<p class="by"><span>${html}</span></p>` : '';
const ext = (url, label) => {
  const u = safeUrl(url);
  return u ? `<a href="${u}" target="_blank" rel="noopener">${esc(label)}</a>` : esc(label);
};

function imageBlock(url, alt, w, h, cls = '') {
  const u = safeUrl(url);
  if (!u) return '';
  const ratio = (w && h) ? ` style="aspect-ratio:${+w}/${+h}"` : '';
  return `<a class="pic ${cls}" href="${u}" target="_blank" rel="noopener"${ratio}><img src="${u}" alt="${esc(alt || '')}" loading="lazy" decoding="async"></a>`;
}

function spotifyId(it) {
  if (it.track_id) return String(it.track_id);
  const m = /\/track\/([A-Za-z0-9]+)/.exec(it.spotify_url || '');
  return m ? m[1] : '';
}

const RENDER = {
  weather(it) {
    if (!it.forecast) return { body: `<div class="legacy">${cleanHtml(it.content)}</div>` };
    const temps = [it.high_f != null ? `${esc(it.high_f)}°` : '', it.low_f != null ? `${esc(it.low_f)}°` : ''].filter(Boolean);
    let body = `<div class="wx"><span class="wx-t">${temps.join('<i>/</i>')}</span><h2>${esc(it.summary || '')}</h2></div>`;
    body += it.forecast.map(p => `<p><strong>${esc(p.name)}.</strong> ${esc(p.text)}</p>`).join('');
    if ((it.key_messages || []).length) {
      body += `<p class="lead-in">The forecasters at the Norton office write:</p><blockquote><ul>${it.key_messages.map(m => `<li>${esc(m)}</li>`).join('')}</ul></blockquote>`;
    }
    if (it.sunrise && it.sunset) {
      body += `<p class="fine">The sun rises at ${esc(it.sunrise)} and sets at ${esc(it.sunset)}, which leaves ${esc(it.daylight)} of daylight.</p>`;
    }
    return { body, source: { label: 'weather.gov', url: it.source_url } };
  },

  wittgenstein(it) {
    let body = `<p class="q-num">${esc(it.number)}</p><blockquote class="q">${esc(it.proposition)}</blockquote>`;
    body += srcLine(`Ludwig Wittgenstein, <cite>Tractatus Logico-Philosophicus</cite>`);
    if ((it.ladder || []).length) {
      const n = it.ladder.length;
      body += `<details class="more"><summary>Show the ${n === 1 ? 'rung' : n + ' rungs'} above this one</summary><ol class="ladder">${
        it.ladder.map(r => `<li><b>${esc(r.number)}</b> ${esc(r.text)}</li>`).join('')}</ol></details>`;
    }
    if (it.commentary) body += `<div class="legacy">${cleanHtml(it.commentary)}</div>`;
    return { body };
  },

  russian(it) {
    let body = `<blockquote class="q" lang="ru">${esc(it.text)}</blockquote>`;
    if (it.transliteration) body += `<p class="translit">${esc(it.transliteration)}</p>`;
    if (it.translation) body += `<p class="gloss">${esc(it.translation)} <span class="mt">(machine translation)</span></p>`;
    body += srcLine(esc(it.source));
    if (it.breakdown) body += `<div class="legacy">${cleanHtml(it.breakdown)}</div>`;
    return { body };
  },

  corpus_surprise(it) {
    const lang = it.lang_code ? ` lang="${esc(it.lang_code)}"` : '';
    const long = (it.sentence || '').length > 220 ? ' long' : '';
    let body = `<blockquote class="q${long}"${lang} dir="auto">${esc(it.sentence)}</blockquote>`;
    if (it.translation) body += `<p class="gloss">${esc(it.translation)} <span class="mt">(machine translation)</span></p>`;
    body += srcLine(`${esc(it.corpus || 'Leipzig Corpora Collection')}${it.year ? ', ' + esc(it.year) : ''}`);
    if (it.context) body += `<div class="legacy">${cleanHtml(it.context)}</div>`;
    return { body };
  },

  annotation(it) {
    const text = (it.v || 1) >= 2 ? esc(it.text) : cleanHtml(it.text);
    let body = `<blockquote class="passage">${text}</blockquote>${srcLine(cleanHtml(it.source))}`;
    if ((it.annotations || []).length) {
      body += `<ol class="legacy notes-list">${it.annotations.map(a => `<li>${cleanHtml(a)}</li>`).join('')}</ol>`;
    }
    return { body };
  },

  untranslatable(it) {
    let body = `<h2 class="word" dir="auto">${esc(it.word)}${it.native ? ` <span>${esc(it.native)}</span>` : ''}</h2>`;
    body += `<p class="word-lang">${esc(plain(it.language))}</p>`;
    if (it.gloss) body += `<p>${esc(it.gloss.charAt(0).toUpperCase() + it.gloss.slice(1))}.</p>`;
    if ((it.senses || []).length) {
      body += `<dl class="senses">${it.senses.map(s => `<div><dt>${esc((s.pos || '').toLowerCase())}</dt><dd>${esc(s.text)}</dd></div>`).join('')}</dl>`;
    }
    if (it.content) body += `<div class="legacy">${cleanHtml(it.content)}${it.question ? `<p><em>${esc(it.question)}</em></p>` : ''}</div>`;
    return { body, source: it.url ? { label: 'Wiktionary', url: it.url } : null };
  },

  dead_medium(it) {
    let body = '';
    if (it.image) body += imageBlock(it.image, it.wiki_title || it.title, 0, 0, 'thumb');
    body += `<h2>${esc(it.title)}</h2><p class="dates">${esc(it.dates || '')}</p>`;
    if (it.gloss) body += `<p class="gloss-line">${esc(it.gloss.charAt(0).toUpperCase() + it.gloss.slice(1))}.</p>`;
    if (it.extract) body += `<p>${esc(it.extract)}</p>`;
    if (it.content) body += `<div class="legacy">${cleanHtml(it.content)}</div>`;
    return { body, source: it.url ? { label: 'Wikipedia', url: it.url } : null };
  },

  penny_red(it) {
    const v2 = !!it.name;
    const name = v2 ? it.name : String(it.current_name || '').split('→').pop().trim();
    let former = v2 ? (it.formerly || []) : String(it.former_name || '').split('/').map(s => s.trim());
    if (!v2 && String(it.current_name || '').includes('→')) former = [String(it.current_name).split('→')[0].trim()];
    former = former.filter(f => f && f !== name && !name.startsWith(f) && !/^\(/.test(f));
    let body = `<h2>${esc(name)}</h2>`;
    if (former.length) body += `<p class="formerly">${former.map(f => `<s>${esc(f)}</s>`).join(' ')}</p>`;
    if (it.gloss) body += `<p class="gloss-line">${esc(it.gloss)}.</p>`;
    if (it.extract) body += `<p>${esc(it.extract)}</p>`;
    if (it.content) body += `<div class="legacy">${cleanHtml(it.content)}</div>`;
    return { body, source: it.url ? { label: 'Wikipedia', url: it.url } : null };
  },

  the_diff(it) {
    let body = `<h2>${esc(it.title)}</h2><div class="chat">${(it.texts || []).map(t =>
      `<p><b>${esc(t.lang)}:</b> <span dir="auto">${esc(t.text)}</span></p>`).join('')}</div>`;
    if (it.commentary) body += `<div class="legacy">${cleanHtml(it.commentary)}</div>`;
    return { body };
  },

  git_log(it) {
    const body = `<div class="chat mono">${(it.commits || []).map(c => {
      if (typeof c === 'string') return `<p>${esc(c)}</p>`;
      const hash = c.url ? ext(c.url, c.hash) : esc(c.hash);
      return `<p><b>${esc(c.repo)}:</b> ${esc(c.message)} <span class="hash">${hash}</span></p>`;
    }).join('')}</div>`;
    return { body };
  },

  typeface(it) {
    let body = it.thumbnail ? imageBlock(it.thumbnail, `Specimen of ${it.font_name}`, 0, 0, 'specimen') : '';
    body += `<div class="cap"><h2>${esc(it.font_name)}</h2>`;
    if (it.description) body += `<p class="dates">${esc(it.description)}</p>`;
    if (it.extract) body += `<p>${esc(it.extract)}</p>`;
    if (it.content) body += `<div class="legacy">${cleanHtml(it.content)}</div>`;
    body += '</div>';
    return { body, source: it.wikipedia_url ? { label: 'Wikipedia', url: it.wikipedia_url } : null, flush: !!it.thumbnail };
  },

  recipe(it) {
    let body = it.image ? imageBlock(it.image, it.name || it.ingredient, 0, 0, 'crop') : '';
    body += '<div class="cap">';
    if (Array.isArray(it.ingredients)) {
      body += `<h2>${esc(it.name)}</h2>`;
      const facts = [it.area, it.category].filter(Boolean).map(esc).join(', ');
      if (facts) body += `<p class="dates">${facts}</p>`;
      body += `<ul class="ingredients">${it.ingredients.map(i => `<li><span>${esc(i.measure)}</span> ${esc(i.item)}</li>`).join('')}</ul>`;
      const steps = it.steps || [];
      if (steps.length) {
        body += `<details class="more"><summary>Show the method</summary><ol class="steps">${steps.map(s => `<li>${esc(s)}</li>`).join('')}</ol></details>`;
      }
      if (it.word) {
        body += `<aside class="etym"><h3>${esc(it.word.term)}</h3><p>${esc(it.word.etymology)}</p><p class="fine">The etymology is quoted from ${ext(it.word.url, 'Wiktionary')}.</p></aside>`;
      }
    } else {
      // v1 cards hold model-written HTML, sometimes with its own prompt scaffolding.
      const tidy = s => String(s || '').replace(/PART\s*[12]\s*[-:–—][^\n<]*(\n|$)/gi, '').replace(/^\s*Pick the most[^\n]*\n/i, '');
      body += `<div class="legacy">${cleanHtml(tidy(it.recipe))}</div>`;
      if (it.etymology) body += `<aside class="etym legacy">${cleanHtml(tidy(it.etymology))}</aside>`;
    }
    body += '</div>';
    return { body, source: it.source_url ? { label: 'the recipe', url: it.source_url } : null, flush: !!it.image };
  },

  apophenia(it) {
    const label = { wikipedia: 'A Wikipedia article', arxiv: 'An arXiv paper', poem: 'A poem', history: 'On this day' };
    let items;
    if (it.items) {
      items = it.items.map(x => `<div class="apo"><p class="apo-kind">${esc(label[x.kind] || x.kind)}</p><h3>${ext(x.url, x.title)}</h3><p class="${x.kind === 'poem' ? 'verse' : ''}">${esc(x.text)}</p></div>`);
    } else {
      items = [it.item_a, it.item_b].filter(Boolean).map(x => {
        const html = cleanHtml(String(x.content || '').replace(/\n/g, '<br>'));
        return `<div class="apo legacy-apo"><p class="apo-kind">${esc(label[x.type] || x.type)}</p><div>${html}</div></div>`;
      });
    }
    let body = items.join(`<p class="apo-q">${esc(it.prompt || 'What connects these?')}</p>`);
    if (it.connection) body += `<details class="more"><summary>Show the machine’s old answer</summary><div class="legacy">${cleanHtml(it.connection)}</div></details>`;
    return { body };
  },

  painting(it) {
    let body = imageBlock(it.image, it.alt || it.title, it.width, it.height);
    const facts = [it.date, it.medium, it.origin].filter(Boolean).map(esc).join(', ');
    body += `<div class="cap"><p class="placard"><cite>${esc(it.title)}</cite><br>${esc(it.artist)}</p>${facts ? `<p class="dates">${facts}</p>` : ''}${it.credit ? `<p class="fine">${esc(it.museum || '')}. ${esc(it.credit)}.</p>` : ''}</div>`;
    return { body, source: { label: 'artic.edu', url: it.source_url }, flush: true };
  },

  postcard(it) {
    let body = imageBlock(it.image, it.alt || 'A photograph with no caption', it.width, it.height);
    if (it.photographer) {
      body += `<div class="cap"><p class="fine">Photograph by ${ext(it.photographer_url, it.photographer)} on ${ext(it.unsplash_url, 'Unsplash')}.</p></div>`;
    }
    return { body, flush: true };
  },

  music_rec(it) {
    const id = spotifyId(it);
    const art = safeUrl(it.image);
    let body = `<div class="player" data-track="${esc(id)}">
      <button class="play" type="button" ${id ? '' : 'disabled'} aria-label="Play ${esc(it.title)} in the Spotify player"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4.500v15l13-7.500z"/></svg></button>
      <div class="track"><strong>${esc(it.title)}</strong><span>${esc(it.artist)}</span></div>
      ${art ? `<img src="${art}" alt="" loading="lazy">` : ''}
    </div><div class="cap">`;
    const album = it.album ? `<cite>${esc(it.album)}</cite>${it.year ? ` (${esc(it.year)})` : ''}` : '';
    if (album) body += `<p>From ${album}.</p>`;
    if (it.seed) body += `<p>This one turned up next to ${esc(it.seed)}.</p>`;
    if (it.body) body += `<div class="legacy">${cleanHtml(it.body)}</div>`;
    body += '</div>';
    return { body, source: it.spotify_url ? { label: 'Spotify', url: it.spotify_url } : null, flush: true };
  },

  monthly_playlist(it) {
    const tracks = it.tracks || [];
    let body = `<div class="tape"><h2>${esc(it.title)}</h2><p>${tracks.length} songs from ${esc(it.month)} ${esc(it.year)}</p></div><div class="cap">`;
    if (it.description && (it.v || 1) < 2) body += `<div class="legacy"><p>${esc(it.description)}</p></div>`;
    body += `<ol class="tracklist">${tracks.map(t => `<li>${ext(t.spotify_url, t.track)} <span>${esc(t.artist)}</span></li>`).join('')}</ol></div>`;
    return { body, source: it.spotify_url ? { label: 'the playlist', url: it.spotify_url } : null, flush: true };
  },

  entropy_garden(it) {
    const algo = /^[a-z_]+$/.test(it.algorithm || '') ? it.algorithm : 'dla';
    const seed = Number(it.seed) || 1;
    const names = { dla: 'Diffusion-limited aggregation', flow_field: 'A flow field', cellular: 'Rule 110', game_of_life: 'Conway’s Game of Life' };
    const body = `<canvas class="garden" width="740" height="400" data-algo="${algo}" data-seed="${seed}" role="img" aria-label="${esc(names[algo] || algo)}, drawn live"></canvas>
      <div class="cap"><p>${esc(names[algo] || algo)}, grown from seed <code>0x${(seed >>> 0).toString(16).padStart(8, '0')}</code>.</p></div>`;
    return { body, flush: true };
  },

  language(it) {
    const where = (it.countries || []).length ? ` It is spoken in ${esc(listOf(it.countries))}.` : '';
    const fam = it.genus && it.genus !== it.family ? `${esc(it.genus)} branch of the ${esc(it.family)} family` : `${esc(it.family)} family`;
    let body = `<h2>${esc(it.name)}</h2><p>${esc(it.name)} belongs to the ${fam}.${where}</p>`;
    body += miniMap(it.lat, it.lon);
    body += `<dl class="features">${(it.features || []).map(f => `<div><dt>${esc(f.name)}</dt><dd>${esc(f.value)}</dd></div>`).join('')}</dl>`;
    body += `<p class="fine">Feature values are quoted from the World Atlas of Language Structures (CC BY 4.0).</p>`;
    return { body, source: { label: 'WALS', url: it.url } };
  },

  poem(it) {
    const stanzas = [];
    let cur = [];
    (it.lines || []).forEach(l => { if (l.trim()) cur.push(l); else if (cur.length) { stanzas.push(cur); cur = []; } });
    if (cur.length) stanzas.push(cur);
    const body = `<h2 class="poem-title">${esc(it.title)}</h2><div class="poem">${stanzas.map(s =>
      `<p>${s.map(l => `<span>${esc(l)}</span>`).join('')}</p>`).join('')}</div>${srcLine(esc(it.author))}`;
    return { body };
  },

  link(it) {
    let host = '';
    try { host = new URL(it.url).hostname.replace(/^www\./, ''); } catch (e) {}
    const when = it.published ? shortDate(parseTs(it.published)) : '';
    let body = `<a class="biglink" href="${safeUrl(it.url)}" target="_blank" rel="noopener"><strong>${esc(it.title)}</strong><span>${esc(host)}</span></a>`;
    if (it.summary) body += `<p>${esc(it.summary)}</p>`;
    const by = [it.author, it.site, when].filter(Boolean).map(esc).join(', ');
    body += srcLine(by);
    return { body };
  },
};
RENDER.diff = RENDER.the_diff;

function listOf(xs) {
  xs = xs.map(String);
  if (xs.length <= 1) return xs.join('');
  if (xs.length === 2) return xs.join(' and ');
  return xs.slice(0, -1).join(', ') + ' and ' + xs[xs.length - 1];
}

// A locator strip: the whole world as a flat band, with one dot.
function miniMap(lat, lon) {
  if (typeof lat !== 'number' || typeof lon !== 'number') return '';
  const x = ((lon + 180) / 360 * 100).toFixed(2), y = ((90 - lat) / 180 * 100).toFixed(2);
  const ns = `${Math.abs(lat).toFixed(1)}°${lat >= 0 ? 'N' : 'S'}`, ew = `${Math.abs(lon).toFixed(1)}°${lon >= 0 ? 'E' : 'W'}`;
  return `<div class="locator" role="img" aria-label="Located at ${ns}, ${ew}"><i style="left:${x}%;top:${y}%"></i><span>${ns}, ${ew}</span></div>`;
}

function renderGeneric(it) {
  const title = it.title ? `<h2>${esc(it.title)}</h2>` : '';
  return { body: title + `<div class="legacy">${cleanHtml(it.body || it.content || it.text || '')}</div>` };
}

// ------------------------------------------------------------------- state

const state = {
  items: [],
  byId: new Map(),
  signature: '',
  pending: null,        // a newer feed waiting behind the "new posts" button
  likes: new Set(store.get('noosphere.likes', [])),
  shown: [],            // the filtered list currently on screen
  count: 0,             // how many of them are rendered
  lastDay: '',
};
const PAGE = 12;

function prepare(items) {
  const ids = new Map();
  const out = [];
  for (const raw of items) {
    if (!raw || !raw.type || !raw.timestamp) continue;
    if (raw.type === 'monthly_playlist' && !(raw.tracks || []).length) continue; // empty tapes from the old generator
    const it = Object.assign({}, raw);
    it._date = parseTs(it.timestamp);
    if (isNaN(it._date)) continue;
    let id = `${it.timestamp.slice(0, 10)}-${it.type}${it.echo ? '-echo' : ''}`.replace(/[^a-z0-9-]/gi, '-');
    const n = (ids.get(id) || 0) + 1;
    ids.set(id, n);
    if (n > 1) id += '-' + n;
    it._id = id;
    it._stream = streamOf(it.type);
    it._kind = it._stream.kind;
    it._tags = tagsFor(it);
    out.push(it);
  }
  return out;
}

function searchText(it) {
  if (it._text == null) {
    const parts = [];
    const walk = v => {
      if (typeof v === 'string') parts.push(v);
      else if (Array.isArray(v)) v.forEach(walk);
      else if (v && typeof v === 'object') Object.keys(v).forEach(k => { if (k[0] !== '_') walk(v[k]); });
    };
    walk(it);
    it._text = (plain(parts.join(' ')) + ' ' + it._stream.name + ' ' + it._tags.join(' ')).toLowerCase();
  }
  return it._text;
}

// ------------------------------------------------------------------ routing

function route() {
  const parts = decodeURIComponent(location.hash.replace(/^#\/?/, '')).split('/');
  const [a, ...rest] = parts;
  const arg = rest.join('/');
  switch (a) {
    case 'type': return KINDS[arg] ? { view: 'feed', kind: arg } : { view: 'feed' };
    case 'stream': return { view: 'feed', stream: arg };
    case 'tagged': return { view: 'feed', tag: arg.toLowerCase() };
    case 'search': return { view: 'feed', q: arg };
    case 'likes': return { view: 'feed', likes: true };
    case 'archive': return { view: 'archive' };
    case 'post': return { view: 'post', id: arg };
    case 'random': return { view: 'random' };
    default: return { view: 'feed' };
  }
}

function filtered(r) {
  let list = state.items;
  if (r.kind) list = list.filter(it => it._kind === r.kind);
  if (r.stream) list = list.filter(it => it._stream.blog === r.stream);
  if (r.tag) list = list.filter(it => it._tags.includes(r.tag));
  if (r.likes) list = list.filter(it => state.likes.has(it._id));
  if (r.q) {
    const words = r.q.toLowerCase().split(/\s+/).filter(Boolean);
    list = list.filter(it => { const t = searchText(it); return words.every(w => t.includes(w)); });
  }
  return list;
}

// ------------------------------------------------------------------- posts

const ICON = {
  reblog: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 11V9a3 3 0 0 1 3-3h9M14 3l3 3-3 3M19 13v2a3 3 0 0 1-3 3H7M10 21l-3-3 3-3" fill="none" stroke="currentColor" stroke-width="2.200" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  heart: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-8-5.200-8-11a4.600 4.600 0 0 1 8-3 4.600 4.600 0 0 1 8 3c0 5.800-8 11-8 11z"/></svg>',
};

function noteCount(it) { return (it.echo ? 1 : 0) + (state.likes.has(it._id) ? 1 : 0); }
function notesLabel(it) { const n = noteCount(it); return n ? `${n} note${n === 1 ? '' : 's'}` : ''; }

function postHTML(it) {
  const s = it._stream;
  let r;
  try { r = (RENDER[it.type] || renderGeneric)(it); }
  catch (e) { console.warn('Could not render', it._id, e); r = renderGeneric(it); }
  const liked = state.likes.has(it._id);
  const streamHref = `#/stream/${s.blog}`;
  const who = it.echo
    ? `<a class="blog" href="#/">${ME.blog}</a><span class="rb" title="reblogged">${ICON.reblog}</span><a class="blog from" href="${streamHref}">${esc(s.blog)}</a>`
    : `<a class="blog" href="${streamHref}">${esc(s.blog)}</a>`;
  const src = r.source && safeUrl(r.source.url)
    ? `<a class="src" href="${safeUrl(r.source.url)}" target="_blank" rel="noopener">${esc(r.source.label)}</a>` : '';
  const echoLine = it.echo && it.echo_from
    ? `<p class="echo-line">${esc(s.blog)} first posted this on ${esc(it.echo_from)}.</p>` : '';
  const tags = it._tags.length
    ? `<ul class="tags">${it._tags.map(t => `<li><a href="#/tagged/${encodeURIComponent(t)}">#${esc(t)}</a></li>`).join('')}</ul>` : '';
  const avatar = it.echo
    ? `<a class="avatar" href="#/" aria-hidden="true" tabindex="-1">${ME.avatar}<span class="sub">${s.avatar}</span></a>`
    : `<a class="avatar" href="${streamHref}" aria-hidden="true" tabindex="-1">${s.avatar}</a>`;
  return `<article class="post k-${it._kind} s-${esc(it.type)}${r.flush ? ' flush' : ''}" id="p-${it._id}" data-id="${it._id}" tabindex="-1">
  ${avatar}
  <div class="card">
    <header class="phead"><span class="mini">${it.echo ? ME.avatar : s.avatar}</span><span class="who">${who}</span>${src}</header>
    <div class="pbody">${r.body}${echoLine}</div>
    ${tags}
    <footer class="pfoot">
      <span class="notes">${notesLabel(it)}</span>
      <a class="when" href="#/post/${it._id}" title="Open this post">${shortDate(it._date)}, ${clock(it._date)}</a>
      <span class="acts">
        <button class="act copy" type="button" title="Copy a link to this post" aria-label="Copy a link to this post">${ICON.reblog}</button>
        <button class="act like" type="button" aria-pressed="${liked}" title="${liked ? 'Unlike' : 'Like'}" aria-label="Like this post">${ICON.heart}</button>
      </span>
    </footer>
  </div>
</article>`;
}

const postsEl = $('#posts');

function appendPosts(n) {
  const slice = state.shown.slice(state.count, state.count + n);
  if (!slice.length) return;
  let html = '';
  for (const it of slice) {
    const k = dayKey(it._date);
    if (k !== state.lastDay) {
      state.lastDay = k;
      html += `<h2 class="day"><span>${dayLabel(it._date)}</span></h2>`;
    }
    html += postHTML(it);
  }
  state.count += slice.length;
  postsEl.insertAdjacentHTML('beforeend', html);
  mountGardens(postsEl);
  const done = state.count >= state.shown.length;
  const end = $('#end');
  end.hidden = !done || !state.shown.length;
  if (done) end.textContent = state.shown.length === state.items.length
    ? 'That is everything. The feed keeps its last 500 posts and lets the rest go.'
    : `That is all ${state.shown.length} of them.`;
}

function describe(r) {
  if (r.kind) return `Showing only ${KINDS[r.kind].label.toLowerCase()} posts.`;
  if (r.stream) {
    const s = Object.values(STREAMS).find(x => x.blog === r.stream);
    return s ? `<strong>${esc(s.name)}</strong> ${esc(s.about)}` : `Nothing posts under the name ${esc(r.stream)}.`;
  }
  if (r.tag) return `Showing posts tagged <strong>#${esc(r.tag)}</strong>.`;
  if (r.q) return `Showing posts that mention <strong>${esc(r.q)}</strong>.`;
  if (r.likes) return 'These are the posts you liked. Likes are kept in this browser only.';
  return '';
}

function emptyMessage(r) {
  if (r.likes) return 'You have not liked anything yet. Press the heart under a post and it will wait for you here.';
  if (r.q) return `Nothing in the last 500 posts mentions “${esc(r.q)}”. A shorter search may find more.`;
  if (!state.items.length) return 'The feed is empty. The generators have not written anything yet.';
  return 'No posts match that filter.';
}

function renderFeed(r) {
  state.shown = filtered(r);
  state.count = 0;
  state.lastDay = '';
  postsEl.className = '';
  postsEl.innerHTML = '';
  const notice = $('#notice');
  const text = describe(r);
  notice.hidden = !text;
  notice.innerHTML = text ? `<p>${text}</p><a href="#/">Show everything</a>` : '';
  if (!state.shown.length) {
    postsEl.innerHTML = `<p class="empty">${emptyMessage(r)}</p>`;
    $('#end').hidden = true;
    return;
  }
  appendPosts(PAGE);
}

function renderPost(r) {
  const it = state.byId.get(r.id);
  postsEl.className = 'single';
  const notice = $('#notice');
  notice.hidden = false;
  notice.innerHTML = `<p>${it ? 'You are looking at one post.' : 'That post has scrolled out of the last 500.'}</p><a href="#/">Back to the dashboard</a>`;
  state.shown = it ? [it] : [];
  state.count = 0;
  state.lastDay = '';
  postsEl.innerHTML = '';
  $('#end').hidden = true;
  if (it) { appendPosts(1); $('#end').hidden = true; }
}

// ----------------------------------------------------------------- archive

function thumbUrl(it) {
  let u = it.image || it.thumbnail || '';
  if (!u) return '';
  if (it.type === 'painting') u = u.replace(/\/full\/\d+,\//, '/full/400,/');
  else if (it.type === 'postcard') u = u.replace(/([?&])w=\d+/, '$1w=300');
  else if (it.type === 'recipe') u = u.replace(/\/(preview|small|medium)$/, '') + '/small';
  return safeUrl(u);
}

function snippet(it) {
  const pick = it.proposition || it.sentence || it.word || it.name || it.font_name || it.title ||
    it.current_name || it.text || it.summary || (it.lines && it.lines[0]) ||
    (it.commits && it.commits[0] && it.commits[0].message) || it._stream.name;
  const t = plain(String(pick));
  return t.length > 90 ? t.slice(0, 88).trimEnd() + '…' : t;
}

function renderArchive() {
  const notice = $('#notice');
  notice.hidden = false;
  notice.innerHTML = `<p>The archive holds the last ${state.items.length} posts, newest first.</p><a href="#/">Back to the dashboard</a>`;
  $('#end').hidden = true;
  postsEl.className = 'archive';
  let html = '', month = '';
  for (const it of state.items) {
    const m = `${MONTHS[it._date.getMonth()]} ${it._date.getFullYear()}`;
    if (m !== month) {
      if (month) html += '</div>';
      month = m;
      html += `<h2 class="day"><span>${m}</span></h2><div class="tiles">`;
    }
    const img = thumbUrl(it);
    const label = `${it._stream.name}, ${shortDate(it._date)}`;
    html += `<a class="tile k-${it._kind}${img ? ' has-img' : ''}" href="#/post/${it._id}" title="${esc(label)}">${
      img ? `<img src="${img}" alt="" loading="lazy" decoding="async">` : `<span class="snip" dir="auto">${esc(snippet(it))}</span>`
    }<span class="tile-foot">${esc(it._stream.blog)}<i>${it._date.getDate()}</i></span></a>`;
  }
  if (month) html += '</div>';
  postsEl.innerHTML = html || '<p class="empty">The archive is empty.</p>';
}

// ----------------------------------------------------------------- sidebar

const THEMES = [
  { id: 'dashboard', label: 'Dashboard', color: '#2f4760' },
  { id: 'pale', label: 'Pale', color: '#f3e4e8' },
  { id: 'midnight', label: 'Midnight', color: '#14131f' },
];

function renderSidebar() {
  const latest = new Map();
  const counts = new Map();
  for (const it of state.items) {
    const b = it._stream.blog;
    counts.set(b, (counts.get(b) || 0) + 1);
    if (!latest.has(b)) latest.set(b, it._date);
  }
  const seen = new Set();
  const following = Object.values(STREAMS).filter(s => !seen.has(s.blog) && seen.add(s.blog) && counts.has(s.blog))
    .sort((a, b) => latest.get(b.blog) - latest.get(a.blog));
  const pics = state.items.filter(it => it._kind === 'photo' && thumbUrl(it) && it.type !== 'typeface');
  const radar = pics.length ? pics[Math.floor(Math.random() * pics.length)] : null;
  const theme = document.documentElement.getAttribute('data-theme') || 'dashboard';

  $('#sidebar').innerHTML = `
  <section class="blogcard">
    <span class="avatar">${ME.avatar}</span>
    <h1>noosphere</h1>
    <p>A feed with nobody else in it. The blogs below post by themselves, each on its own schedule, and what they post is quoted from a real source.</p>
    <ul class="stats">
      <li><a href="#/"><span>Posts</span><b>${state.items.length}</b></a></li>
      <li><a href="#/archive"><span>Archive</span><b>${new Set(state.items.map(i => i.timestamp.slice(0, 7))).size} mo</b></a></li>
      <li><a href="#/likes"><span>Likes</span><b id="likeCount">${state.likes.size}</b></a></li>
    </ul>
  </section>
  <section>
    <h2>Following</h2>
    <ul class="following">${following.map(s => `<li><a href="#/stream/${s.blog}" title="${esc(s.about)}"><span class="avatar">${s.avatar}</span><span class="f-name">${esc(s.blog)}</span><span class="f-when">${ago(latest.get(s.blog))}</span></a></li>`).join('')}</ul>
  </section>
  ${radar ? `<section class="radar"><h2>Radar</h2><a href="#/post/${radar._id}"><img src="${thumbUrl(radar)}" alt="${esc(radar.title || radar.alt || 'A photo post from the archive')}" loading="lazy"><span>${esc(radar._stream.blog)}, ${shortDate(radar._date)}</span></a></section>` : ''}
  <section>
    <h2>Theme</h2>
    <div class="themes" role="radiogroup" aria-label="Theme">${THEMES.map(t => `<button type="button" role="radio" aria-checked="${t.id === theme}" data-theme-id="${t.id}"><i style="background:${t.color}"></i>${t.label}</button>`).join('')}</div>
  </section>
  <p class="colophon">The keys <kbd>J</kbd> and <kbd>K</kbd> move between posts, <kbd>L</kbd> likes one, and <kbd>/</kbd> opens search.</p>`;
}

function renderTypebar(r) {
  $('#typebar').innerHTML = Object.entries(KINDS).map(([k, v]) =>
    `<a class="tb k-${k}" href="${r.kind === k ? '#/' : '#/type/' + k}" aria-current="${r.kind === k}"><svg viewBox="0 0 40 40" aria-hidden="true">${v.icon}</svg><span>${v.label}</span></a>`).join('');
  $('#typebar').classList.toggle('filtering', !!r.kind);
}

// -------------------------------------------------------------------- view

function render() {
  const r = route();
  if (r.view === 'random') {
    const pool = state.items;
    if (pool.length) { location.replace('#/post/' + pool[Math.floor(Math.random() * pool.length)]._id); return; }
    location.replace('#/');
    return;
  }
  document.body.dataset.view = r.view;
  document.querySelectorAll('.tabs [data-tab]').forEach(a => {
    const on = a.dataset.tab === (r.likes ? 'likes' : r.view === 'archive' ? 'archive' : r.view === 'feed' ? 'feed' : '');
    a.classList.toggle('on', on);
  });
  renderTypebar(r);
  const q = $('#q');
  if (document.activeElement !== q) q.value = r.q || '';
  if (r.view === 'archive') renderArchive();
  else if (r.view === 'post') renderPost(r);
  else renderFeed(r);
}

function setItems(items) {
  state.items = prepare(items);
  state.byId = new Map(state.items.map(it => [it._id, it]));
  renderSidebar();
  render();
}

const signatureOf = items => items.length + '|' + items.slice(0, 40).map(i => i.timestamp + i.type).join(',');

async function loadFeed(first) {
  let data;
  try {
    const res = await fetch('/api/feed?limit=500', { cache: 'no-cache' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    data = await res.json();
  } catch (err) {
    if (first) postsEl.innerHTML = '<p class="empty">The feed did not load. Check the connection and reload the page.</p>';
    return;
  }
  const items = Array.isArray(data) ? data : (data.items || []);
  const sig = signatureOf(items);
  if (sig === state.signature) return;
  if (first || !state.items.length || window.scrollY < 300) {
    state.signature = sig;
    state.pending = null;
    $('#newPosts').hidden = true;
    setItems(items);
    return;
  }
  // The reader is partway down. Keep the page still and offer the new posts.
  const known = new Set(state.items.map(it => it.timestamp + it.type));
  const fresh = items.filter(i => i && !known.has(i.timestamp + i.type)).length;
  state.pending = { items, sig };
  const btn = $('#newPosts');
  btn.textContent = fresh === 1 ? '1 new post' : `${fresh || 'Some'} new posts`;
  btn.hidden = false;
}

// ------------------------------------------------------------------ events

postsEl.addEventListener('click', e => {
  const post = e.target.closest('.post');
  if (!post) return;
  const it = state.byId.get(post.dataset.id);
  if (!it) return;

  const like = e.target.closest('.like');
  if (like) { toggleLike(it, post); return; }

  const copy = e.target.closest('.copy');
  if (copy) {
    const url = location.origin + location.pathname + '#/post/' + it._id;
    const done = () => { copy.classList.add('done'); copy.title = 'Link copied'; setTimeout(() => { copy.classList.remove('done'); copy.title = 'Copy a link to this post'; }, 1600); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, () => { location.hash = '#/post/' + it._id; });
    else location.hash = '#/post/' + it._id;
    return;
  }

  const play = e.target.closest('.play');
  if (play) {
    const player = play.closest('.player');
    const id = player.dataset.track;
    if (!/^[A-Za-z0-9]+$/.test(id)) return;
    const frame = document.createElement('iframe');
    frame.className = 'spotify';
    frame.title = 'Spotify player';
    frame.allow = 'autoplay; clipboard-write; encrypted-media; fullscreen';
    frame.loading = 'lazy';
    frame.src = `https://open.spotify.com/embed/track/${id}?utm_source=generator`;
    player.replaceWith(frame);
  }
});

function toggleLike(it, post) {
  const on = !state.likes.has(it._id);
  if (on) state.likes.add(it._id); else state.likes.delete(it._id);
  store.set('noosphere.likes', [...state.likes]);
  const btn = $('.like', post);
  btn.setAttribute('aria-pressed', on);
  btn.title = on ? 'Unlike' : 'Like';
  if (on) { btn.classList.remove('pop'); void btn.offsetWidth; btn.classList.add('pop'); }
  $('.notes', post).textContent = notesLabel(it);
  const c = $('#likeCount');
  if (c) c.textContent = state.likes.size;
}

$('#newPosts').addEventListener('click', () => {
  if (!state.pending) return;
  state.signature = state.pending.sig;
  const items = state.pending.items;
  state.pending = null;
  $('#newPosts').hidden = true;
  window.scrollTo({ top: 0 });
  setItems(items);
});

$('#searchForm').addEventListener('submit', e => {
  e.preventDefault();
  const q = $('#q').value.trim();
  location.hash = q ? '#/search/' + encodeURIComponent(q) : '#/';
  $('#q').blur();
});

window.addEventListener('hashchange', () => {
  closeMenu();
  render();
  window.scrollTo({ top: 0 });
});

// Images come from other people's servers and some will fail. A museum scan
// gets one retry at the size the museum caches, and anything still broken
// steps aside instead of leaving a torn-paper icon.
document.addEventListener('error', e => {
  const img = e.target;
  if (!(img instanceof HTMLImageElement)) return;
  if (!img.dataset.retried && /artic\.edu\/iiif/.test(img.src) && !/\/full\/843,\//.test(img.src)) {
    img.dataset.retried = '1';
    img.src = img.src.replace(/\/full\/\d+,\//, '/full/843,/');
    return;
  }
  const tile = img.closest('.tile');
  if (tile) {
    const it = state.byId.get((tile.getAttribute('href') || '').replace('#/post/', ''));
    tile.classList.remove('has-img');
    img.outerHTML = `<span class="snip" dir="auto">${esc(it ? snippet(it) : '')}</span>`;
    return;
  }
  const radar = img.closest('.radar');
  if (radar) { radar.hidden = true; return; }
  const pic = img.closest('.pic');
  if (pic) { pic.classList.add('broken'); pic.removeAttribute('style'); img.remove(); pic.textContent = 'The image did not load. This link opens it at its source.'; return; }
  img.remove();
}, true);

// Infinite scroll.
new IntersectionObserver(entries => {
  if (entries.some(e => e.isIntersecting) && route().view === 'feed') appendPosts(PAGE);
}, { rootMargin: '900px' }).observe($('#sentinel'));

// Back to top.
const toTop = $('#toTop');
window.addEventListener('scroll', () => { toTop.hidden = window.scrollY < 1400; }, { passive: true });
toTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }));

// The sidebar is a drawer on small screens.
const menuBtn = $('#menuBtn'), sidebar = $('#sidebar'), scrim = $('#scrim');
function closeMenu() { document.body.classList.remove('menu-open'); menuBtn.setAttribute('aria-expanded', 'false'); scrim.hidden = true; }
menuBtn.addEventListener('click', () => {
  const open = !document.body.classList.contains('menu-open');
  document.body.classList.toggle('menu-open', open);
  menuBtn.setAttribute('aria-expanded', open);
  scrim.hidden = !open;
});
scrim.addEventListener('click', closeMenu);

sidebar.addEventListener('click', e => {
  const b = e.target.closest('[data-theme-id]');
  if (!b) return;
  setTheme(b.dataset.themeId);
  sidebar.querySelectorAll('[data-theme-id]').forEach(x => x.setAttribute('aria-checked', x === b));
});

function setTheme(id) {
  const t = THEMES.find(x => x.id === id) || THEMES[0];
  document.documentElement.setAttribute('data-theme', t.id);
  $('#themeColor').setAttribute('content', t.color);
  try { localStorage.setItem('noosphere.theme', t.id); } catch (e) {}
}
setTheme(document.documentElement.getAttribute('data-theme'));

// Keyboard: J and K step through posts, L likes, slash searches.
document.addEventListener('keydown', e => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const tag = (e.target.tagName || '').toLowerCase();
  if (e.key === 'Escape') { closeMenu(); if (tag === 'input') e.target.blur(); return; }
  if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;
  if (e.key === '/') { e.preventDefault(); $('#q').focus(); return; }
  const key = e.key.toLowerCase();
  if (!['j', 'k', 'l'].includes(key)) return;
  const posts = [...postsEl.querySelectorAll('.post')];
  if (!posts.length) return;
  const line = 90;
  let cur = posts.findIndex(p => p.getBoundingClientRect().top >= line - 4);
  if (cur < 0) cur = posts.length - 1;
  const at = posts[cur].getBoundingClientRect().top;
  if (key === 'l') {
    const target = Math.abs(at - line) < 60 || cur === 0 ? posts[cur] : posts[cur - 1];
    const it = state.byId.get(target.dataset.id);
    if (it) toggleLike(it, target);
    return;
  }
  let next;
  if (key === 'j') next = Math.abs(at - line) < 8 ? posts[cur + 1] : posts[cur];
  else next = posts[Math.max(0, cur - 1)];
  if (!next) return;
  window.scrollTo({ top: window.scrollY + next.getBoundingClientRect().top - line });
  next.focus({ preventScroll: true });
});

// --------------------------------------------------------------------- boot

$('#meAvatar').innerHTML = ME.avatar;
renderTypebar(route());
loadFeed(true);
setInterval(() => loadFeed(false), 5 * 60 * 1000);

if ('serviceWorker' in navigator && location.protocol === 'https:') {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}
