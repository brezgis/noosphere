'use strict';
/* noosphere. An almanac with one reader.
 *
 * Every stream posts at its own hour, so the page knows the shape of a day
 * before it happens: each day gets a line from midnight to midnight with a
 * dot per post, and today's also shows what is still to come. Cards from the
 * feed become posts of one of seven kinds (text, photo, quote, link, chat,
 * audio, video). An "echo" card is an old post returning, and a liked post
 * is one whose corner has been turned down ("kept").
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
  text: { label: 'Text' }, photo: { label: 'Photo' }, quote: { label: 'Quote' }, link: { label: 'Link' },
  chat: { label: 'Chat' }, audio: { label: 'Audio' }, video: { label: 'Video' },
};

// Every stream has a mark of its own, drawn on a 24-unit grid in one weight
// of line. The class "f" fills a shape instead of outlining it.
const sig = inner => `<svg class="sigil" viewBox="0 0 24 24" aria-hidden="true">${inner}</svg>`;

// `at` and `days` say when a stream posts, which lets the page show what is
// still to come. They repeat generators/schedule.py and the timestamp each
// generator writes, so a change there needs the same change here. `days` is
// 'daily', 'first' (of the month) or a list of weekdays with Sunday as 0.
const STREAMS = {
  weather: { blog: 'lyrical-weather', name: 'Lyrical Weather', kind: 'text', at: '06:50', days: 'daily',
    about: 'The Boston forecast in the forecasters’ own words.',
    sigil: sig('<path d="M3 16h18M6.500 16a5.500 5.500 0 0 1 11 0M12 4.500v3M5 8.300l2 2.200M19 8.300l-2 2.200M7.500 20h9"/>') },
  wittgenstein: { blog: 'wittgensteins-ladder', name: 'Wittgenstein’s Ladder', kind: 'quote', at: '08:00', days: 'daily',
    about: 'The Tractatus, one proposition a day.',
    sigil: sig('<path d="M8.500 3 7.500 21M15.500 3l1 18M8.300 7.500h7.400M8 12h8M7.800 16.500h8.400"/>') },
  russian: { blog: 'russkiy-chas', name: 'Русский час', kind: 'quote', at: '08:30', days: 'daily',
    about: 'One sentence of Russian literature a day.',
    sigil: sig('<path d="M12 4v16M5 4c.500 5 3 8 7 8M19 4c-.500 5-3 8-7 8M5 20c.500-5 3-8 7-8M19 20c-.500-5-3-8-7-8"/>') },
  untranslatable: { blog: 'the-untranslatable', name: 'The Untranslatable', kind: 'text', at: '15:00', days: [1, 3, 5],
    about: 'Words that English needs a sentence for.',
    sigil: sig('<circle cx="12" cy="12" r="9"/><path d="M8 10h8M8 14h8M14.500 7l-5 10"/>') },
  corpus_surprise: { blog: 'corpus-surprise', name: 'Corpus Surprise', kind: 'quote', at: '14:15', days: 'daily',
    about: 'One sentence pulled at random from 130,000.',
    sigil: sig('<g class="f"><circle cx="5" cy="5" r="1.100"/><circle cx="12" cy="5" r="1.100"/><circle cx="19" cy="5" r="1.100"/><circle cx="5" cy="12" r="1.100"/><circle cx="19" cy="12" r="1.100"/><circle cx="5" cy="19" r="1.100"/><circle cx="12" cy="19" r="1.100"/><circle cx="19" cy="19" r="1.100"/><circle cx="12" cy="12" r="1.100"/></g><circle cx="12" cy="12" r="4"/>') },
  annotation: { blog: 'commonplace-book', name: 'The Commonplace Book', kind: 'text', at: '15:00', days: [0],
    about: 'A paragraph from an old novel, once a week.',
    sigil: sig('<path d="M12 7c-2.500-2-5.500-2-8.500-1v12c3-1 6-1 8.500 1 2.500-2 5.500-2 8.500-1V6c-3-1-6-1-8.500 1zM12 7v12"/>') },
  entropy_garden: { blog: 'entropy-garden', name: 'Entropy Garden', kind: 'video', at: '23:00', days: 'daily',
    about: 'A small simulation that grows while you watch.',
    sigil: sig('<path d="M12 21v-7M12 14 7 9M12 14l5-5M7 9V4M7 9H3M17 9V4M17 9h4"/>') },
  apophenia: { blog: 'apophenia-machine', name: 'Apophenia Machine', kind: 'link', at: '14:00', days: [2, 4],
    about: 'Two unrelated things and one question.',
    sigil: sig('<circle cx="6" cy="17" r="3"/><circle cx="18" cy="7" r="3"/><path d="M9 14.500l6-5" stroke-dasharray="1 2.600"/>') },
  dead_medium: { blog: 'the-dead-medium', name: 'The Dead Medium', kind: 'text', at: '10:00', days: [5],
    about: 'An obituary page for communication technology.',
    sigil: sig('<path d="M12 3v18M7 8.500h10M9.500 21h5"/>') },
  painting: { blog: 'midday-museum', name: 'Midday Museum', kind: 'photo', at: '13:00', days: 'daily',
    about: 'One public-domain painting from Chicago at lunch.',
    sigil: sig('<rect x="3.500" y="5" width="17" height="14"/><path d="M3.500 16l5-5 4 4 3-2.500 5 4.500"/><circle class="f" cx="15.500" cy="9" r="1.200"/>') },
  postcard: { blog: 'midnight-postcard', name: 'Midnight Postcard', kind: 'photo', at: '23:30', days: 'daily',
    about: 'One photograph, late, with no caption.',
    sigil: sig('<path d="M15 3.500A9 9 0 1 0 20.500 15 7.500 7.500 0 0 1 15 3.500z"/>') },
  git_log: { blog: 'git-log-oneline', name: 'git log --oneline', kind: 'chat', at: '12:00', days: 'daily',
    about: 'What other people committed today.',
    sigil: sig('<path d="M7 7.800v8.400M7 15c0-4 10-2.500 10-7.200"/><circle cx="7" cy="6" r="1.800"/><circle cx="7" cy="18" r="1.800"/><circle cx="17" cy="6" r="1.800"/>') },
  penny_red: { blog: 'the-penny-red', name: 'The Penny Red', kind: 'text', at: '11:00', days: [2, 6],
    about: 'Places that were renamed, erased or argued over.',
    sigil: sig('<rect x="5" y="3.500" width="14" height="17" stroke-dasharray="1.500 2.500"/><circle cx="12" cy="12" r="3.500"/>') },
  the_diff: { blog: 'the-diff', name: 'The Diff', kind: 'chat', at: '09:00', days: [1],
    about: 'One passage in two or three languages.',
    sigil: sig('<path d="M12 4v9M7.500 8.500h9M7.500 18.500h9"/>') },
  typeface: { blog: 'typeface-of-the-week', name: 'Typeface of the Week', kind: 'photo', at: '09:30', days: [3],
    about: 'A typeface and where it came from.',
    sigil: sig('<path d="M6 18 12 4l6 14M8.200 13h7.600M3 21h18"/>') },
  recipe: { blog: 'the-recipe-box', name: 'The Recipe Box', kind: 'photo', at: '17:00', days: [3],
    about: 'A real recipe and the history of one word in it.',
    sigil: sig('<path d="M3.500 12h17a8.500 8.500 0 0 1-17 0zM9.500 8.500c-1-1.500 1-2.500 0-4.500M14.500 8.500c-1-1.500 1-2.500 0-4.500"/>') },
  music_rec: { blog: 'you-should-hear-this', name: 'You Should Hear This', kind: 'audio', at: '19:30', days: 'daily',
    about: 'One song a day that is not in the library yet.',
    sigil: sig('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.500"/><circle class="f" cx="12" cy="12" r="1.200"/>') },
  monthly_playlist: { blog: 'monthly-mixtape', name: 'Monthly Mixtape', kind: 'audio', at: '06:00', days: 'first',
    about: 'Last month’s songs on one tape.',
    sigil: sig('<rect x="3" y="6" width="18" height="12" rx="1"/><circle cx="8.500" cy="12" r="2"/><circle cx="15.500" cy="12" r="2"/><path d="M10.500 12h3"/>') },
  language: { blog: 'a-language-a-day', name: 'A Language a Day', kind: 'text', at: '10:30', days: 'daily',
    about: 'One language from the World Atlas of Language Structures.',
    sigil: sig('<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>') },
  poem: { blog: 'the-night-poem', name: 'The Night Poem', kind: 'text', at: '21:00', days: [0, 2, 4],
    about: 'A short poem, three evenings a week.',
    sigil: sig('<path d="M12 3c2.500 3 3.500 5 3.500 7a3.500 3.500 0 0 1-7 0c0-2 1-4 3.500-7zM12 13.500V21M8 21h8"/>') },
  link: { blog: 'open-tabs', name: 'Open Tabs', kind: 'link', at: '16:00', days: 'daily',
    about: 'One thing to read from a short list of blogs.',
    sigil: sig('<path d="M10 5H5v14h14v-5M13.500 4H20v6.500M20 4l-9 9"/>') },
};
const STREAM_LIST = Object.values(STREAMS);
STREAMS.diff = STREAMS.the_diff;

const UNKNOWN = { blog: 'unsorted', name: 'Unsorted', kind: 'text', about: '', sigil: sig('<circle cx="12" cy="12" r="9" stroke-dasharray="2 3"/>') };
const streamOf = type => STREAMS[type] || UNKNOWN;
// Jost sets two hyphens so close that "--oneline" reads as a dash, so a
// sliver of space goes between them.
const nameHTML = s => esc(s.name).replace('--', '-<i class="hy"></i>-');

// ------------------------------------------------------------------ almanac
// What the page knows about a day without being told: its number, the phase
// of the moon, and which streams are due.

const FIRST_DAY = new Date(2026, 1, 16);   // the date of the first card
function dayNumber(d) {
  return Math.round((new Date(d.getFullYear(), d.getMonth(), d.getDate()) - FIRST_DAY) / 864e5) + 1;
}

// Mean lunar phase as a fraction of the synodic month: 0 is new, 0.5 is full.
// Counting from the new moon of 6 January 2000 is good to a few hours, which
// is plenty for a picture 16 pixels wide.
function moonPhase(d) {
  const days = (d.getTime() - Date.UTC(2000, 0, 6, 18, 14)) / 864e5;
  const p = (days / 29.530588853) % 1;
  return p < 0 ? p + 1 : p;
}
function moonName(p) {
  if (p < .034 || p >= .966) return 'new moon';
  if (p < .216) return 'waxing crescent';
  if (p < .284) return 'first quarter';
  if (p < .466) return 'waxing gibbous';
  if (p < .534) return 'full moon';
  if (p < .716) return 'waning gibbous';
  if (p < .784) return 'last quarter';
  return 'waning crescent';
}
function moonHTML(d) {
  const p = moonPhase(new Date(d.getFullYear(), d.getMonth(), d.getDate(), 21));
  const rx = (Math.abs(Math.cos(2 * Math.PI * p)) * 7).toFixed(2);
  const waxing = p < .5, crescent = p < .25 || p >= .75;
  // The lit limb is half the disc. The terminator is half an ellipse that
  // closes the shape on the near side for a crescent and the far side otherwise.
  const lit = `M8 1A7 7 0 0 ${waxing ? 1 : 0} 8 15A${rx} 7 0 0 ${waxing === crescent ? 0 : 1} 8 1z`;
  return `<span class="moon"><svg viewBox="0 0 16 16" aria-hidden="true"><path class="lit" d="${lit}"/><circle class="disc" cx="8" cy="8" r="7"/></svg>${moonName(p)}</span>`;
}

const minutesOf = hhmm => { const [h, m] = hhmm.split(':'); return +h * 60 + +m; };
function clockMinutes(str) {   // "6:30 am" from the weather stream
  const m = /^(\d{1,2}):(\d\d)\s*([ap])m$/i.exec(String(str || '').trim());
  if (!m) return null;
  return (+m[1] % 12 + (m[3].toLowerCase() === 'p' ? 12 : 0)) * 60 + +m[2];
}
function dueOn(s, d) {
  if (s.days === 'daily') return true;
  if (s.days === 'first') return d.getDate() === 1;
  return s.days.includes(d.getDay());
}
function slot(s, d) {
  const m = minutesOf(s.at);
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), Math.floor(m / 60), m % 60);
}
function nextPost(s, now) {
  for (let i = 0; i < 40; i++) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + i);
    if (dueOn(s, d) && slot(s, d) > now) return slot(s, d);
  }
  return null;
}
function whenLabel(d) {
  const now = new Date();
  const days = Math.round((new Date(d.getFullYear(), d.getMonth(), d.getDate()) - new Date(now.getFullYear(), now.getMonth(), now.getDate())) / 864e5);
  if (days === 0) return clock(d);
  if (days === 1) return `tomorrow, ${clock(d)}`;
  if (days < 7) return `${DAYS[d.getDay()]}, ${clock(d)}`;
  return shortDate(d);
}
function cadence(s) {
  const at = clock(slot(s, new Date()));
  if (s.days === 'daily') return `Posts every day at ${at}.`;
  if (s.days === 'first') return `Posts on the first of the month at ${at}.`;
  return `Posts on ${listOf(s.days.map(n => DAYS[n] + 's'))} at ${at}.`;
}

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
  days: new Map(),      // every post of a day, keyed by dayKey
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
    case 'kept': case 'likes': return { view: 'feed', likes: true };
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
  // A page with its corner turned down.
  keep: '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M1.500 1h7L12.500 5v8h-11z"/><path class="fold" d="M8.500 1v4h4z"/></svg>',
};

function postHTML(it) {
  const s = it._stream;
  let r;
  try { r = (RENDER[it.type] || renderGeneric)(it); }
  catch (e) { console.warn('Could not render', it._id, e); r = renderGeneric(it); }
  const kept = state.likes.has(it._id);
  const streamHref = `#/stream/${s.blog}`;
  const src = r.source && safeUrl(r.source.url)
    ? `<a class="src" href="${safeUrl(r.source.url)}" target="_blank" rel="noopener">${esc(r.source.label)}</a>` : '';
  const returning = it.echo
    ? `<span class="returning">${it.echo_from ? `returning from ${esc(it.echo_from)}` : 'returning from the archive'}</span>` : '';
  const tags = it._tags.length
    ? `<ul class="tags">${it._tags.map(t => `<li><a href="#/tagged/${encodeURIComponent(t)}">#${esc(t)}</a></li>`).join('')}</ul>` : '';
  return `<article class="post k-${it._kind} s-${esc(it.type)}${r.flush ? ' flush' : ''}${it.echo ? ' returns' : ''}${kept ? ' kept' : ''}" id="p-${it._id}" data-id="${it._id}" tabindex="-1">
  <div class="margin">
    <a class="mark" href="${streamHref}" title="${esc(s.name)}" aria-hidden="true" tabindex="-1">${s.sigil}</a>
    <a class="when" href="#/post/${it._id}" title="Open this post by itself">${clock(it._date)}</a>
  </div>
  <div class="card">
    <header class="phead"><span class="mini">${s.sigil}</span><a class="blog" href="${streamHref}">${nameHTML(s)}</a>${returning}<a class="when" href="#/post/${it._id}">${clock(it._date)}</a>${src}</header>
    <div class="pbody">${r.body}</div>
    <footer class="pfoot">
      ${tags}
      <button class="act like" type="button" aria-pressed="${kept}">${ICON.keep}<span>${kept ? 'Kept' : 'Keep'}</span></button>
    </footer>
    <span class="ear" aria-hidden="true"></span>
  </div>
</article>`;
}

// The heading of a day: its date, its number, the moon, and (on the full
// feed) a line from midnight to midnight with a dot for every post.
function dayHTML(d, withLine) {
  const now = new Date();
  const today = dayKey(d) === dayKey(now);
  const y = new Date(now); y.setDate(now.getDate() - 1);
  const rel = today ? 'Today' : dayKey(d) === dayKey(y) ? 'Yesterday' : '';
  const yr = d.getFullYear() === now.getFullYear() ? '' : `, ${d.getFullYear()}`;
  const date = `${DAYS[d.getDay()]}, ${MONTHS[d.getMonth()]} ${d.getDate()}${yr}`;
  const n = dayNumber(d);
  let html = `<header class="day${today ? ' today' : ''}"><div class="day-head"><h2>${rel ? `<small>${rel}</small>` : ''}${date}</h2><p class="day-meta">${n > 0 ? `<span>No. ${n}</span>` : ''}${moonHTML(d)}</p></div>`;
  if (withLine) html += dayLine(d, today, now);
  return html + '</header>';
}

function dayLine(d, today, now) {
  const items = state.days.get(dayKey(d)) || [];
  const pct = m => (m / 1440 * 100).toFixed(2);
  const mins = t => t.getHours() * 60 + t.getMinutes();
  let line = '';
  const wx = items.find(it => it.type === 'weather' && !it.echo);
  const rise = wx && clockMinutes(wx.sunrise), set = wx && clockMinutes(wx.sunset);
  if (rise != null && set != null && set > rise) {
    line += `<span class="light" style="left:${pct(rise)}%;width:${pct(set - rise)}%" title="The sun is up from ${esc(wx.sunrise)} to ${esc(wx.sunset)}"></span>`;
  }
  line += '<span class="hr" style="left:25%">6 am</span><span class="hr" style="left:50%">noon</span><span class="hr" style="left:75%">6 pm</span>';
  for (const it of items.slice().reverse()) {
    const label = `${it._stream.name}${it.echo ? ', returning' : ''}, ${clock(it._date)}`;
    line += `<button class="dot${it.echo ? ' ret' : ''}" type="button" data-go="${it._id}" style="left:${pct(mins(it._date))}%" title="${esc(label)}" aria-label="Go to ${esc(label)}"></button>`;
  }
  let coming = [];
  if (today) {
    const have = new Set(items.filter(it => !it.echo).map(it => it._stream));
    coming = STREAM_LIST.filter(s => dueOn(s, d) && !have.has(s)).sort((a, b) => minutesOf(a.at) - minutesOf(b.at));
    for (const s of coming) {
      line += `<span class="dot due" style="left:${pct(minutesOf(s.at))}%" title="${esc(s.name)}, due at ${clock(slot(s, d))}"></span>`;
    }
    line += `<span class="now" style="left:${pct(mins(now))}%" title="Now"></span>`;
  }
  let html = `<div class="dayline">${line}</div>`;
  if (today && coming.length) {
    html += `<p class="tocome">Still to come today: ${listOf(coming.map(s => `${nameHTML(s)} at ${clock(slot(s, d))}`))}.</p>`;
  }
  return html;
}

const postsEl = $('#posts');

function appendPosts(n) {
  const slice = state.shown.slice(state.count, state.count + n);
  if (!slice.length) return;
  const whole = state.shown.length === state.items.length;
  let html = '';
  for (const it of slice) {
    const k = dayKey(it._date);
    if (k !== state.lastDay) {
      state.lastDay = k;
      html += dayHTML(it._date, whole);
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
    const s = STREAM_LIST.find(x => x.blog === r.stream);
    if (!s) return `Nothing posts under the name ${esc(r.stream)}.`;
    const nx = nextPost(s, new Date());
    return `<strong>${nameHTML(s)}.</strong> ${esc(s.about)} ${cadence(s)}${nx ? ` The next one is due ${dayKey(nx) === dayKey(new Date()) ? 'today at ' : ''}${whenLabel(nx)}.` : ''}`;
  }
  if (r.tag) return `Showing posts tagged <strong>#${esc(r.tag)}</strong>.`;
  if (r.q) return `Showing posts that mention <strong>${esc(r.q)}</strong>.`;
  if (r.likes) return 'These are the posts you kept. They are remembered in this browser only.';
  return '';
}

function emptyMessage(r) {
  if (r.likes) return 'You have not kept anything yet. Choose Keep under a post to turn its corner down, and it will wait for you here.';
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
  notice.innerHTML = `<p>${it ? 'You are looking at one post.' : 'That post has scrolled out of the last 500.'}</p><a href="#/">Back to today</a>`;
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
  notice.innerHTML = `<p>The archive holds the last ${state.items.length} posts, newest first.</p><a href="#/">Back to today</a>`;
  $('#end').hidden = true;
  postsEl.className = 'archive';
  let html = '', month = '';
  for (const it of state.items) {
    const m = `${MONTHS[it._date.getMonth()]} ${it._date.getFullYear()}`;
    if (m !== month) {
      if (month) html += '</div>';
      month = m;
      html += `<h2 class="month">${m}</h2><div class="tiles">`;
    }
    const img = thumbUrl(it);
    const label = `${it._stream.name}, ${shortDate(it._date)}`;
    html += `<a class="tile k-${it._kind}${img ? ' has-img' : ''}" href="#/post/${it._id}" title="${esc(label)}">${
      img ? `<img src="${img}" alt="" loading="lazy" decoding="async">` : `<span class="snip" dir="auto">${esc(snippet(it))}</span>`
    }<span class="tile-foot">${it._stream.sigil}<b>${nameHTML(it._stream)}</b><i>${it._date.getDate()}</i></span></a>`;
  }
  if (month) html += '</div>';
  postsEl.innerHTML = html || '<p class="empty">The archive is empty.</p>';
}

// ----------------------------------------------------------------- sidebar

const LIGHTS = [
  { id: 'sun', label: 'Follow the sun' },
  { id: 'day', label: 'Day' },
  { id: 'night', label: 'Night' },
];
const PAGE_COLOR = { day: '#e7e2f0', night: '#120e24' };

function renderSidebar() {
  const now = new Date();
  const next = new Map(STREAM_LIST.map(s => [s, nextPost(s, now)]));
  const streams = STREAM_LIST.slice().sort((a, b) => (next.get(a) || Infinity) - (next.get(b) || Infinity));
  // The streams in the order they will post. Six show, the rest fold away.
  const dayStart = d => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const rows = streams.filter(s => next.get(s)).map(s => {
    const t = next.get(s);
    const away = Math.round((dayStart(t) - dayStart(now)) / 864e5);
    const when = away === 0 ? clock(t) : away < 7 ? `${DAYS[t.getDay()].slice(0, 3)} ${clock(t)}` : shortDate(t);
    return `<li><a href="#/stream/${s.blog}" title="${esc(s.about)}">${s.sigil}<b>${nameHTML(s)}</b><i>${when}</i></a></li>`;
  });
  const light = store.get('noosphere.light', 'sun');

  $('#sidebar').innerHTML = `
  <section>
    <h2>What posts next</h2>
    <ul class="streams">${rows.slice(0, 6).join('')}</ul>
    ${rows.length > 6 ? `<details class="rest"><summary>All ${rows.length} streams</summary><ul class="streams">${rows.slice(6).join('')}</ul></details>` : ''}
  </section>
  <section>
    <h2>Show one kind of post</h2>
    <nav class="typebar" id="typebar" aria-label="Filter by kind of post"></nav>
  </section>
  <section>
    <h2>Light</h2>
    <div class="themes" role="radiogroup" aria-label="Light">${LIGHTS.map(t => `<button type="button" role="radio" aria-checked="${t.id === light}" data-light="${t.id}">${t.label}</button>`).join('')}</div>
  </section>`;
}

function renderTypebar(r) {
  const bar = $('#typebar');
  if (!bar) return;
  bar.innerHTML = Object.entries(KINDS).map(([k, v]) =>
    `<a class="tb" href="${r.kind === k ? '#/' : '#/type/' + k}" aria-current="${r.kind === k}">${v.label}</a>`).join('');
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
  state.days = new Map();
  for (const it of state.items) {
    const k = dayKey(it._date);
    if (!state.days.has(k)) state.days.set(k, []);
    state.days.get(k).push(it);
  }
  applyLight();
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
  // A dot on a day line scrolls to its post, rendering more of the feed if
  // the post is further down than the page has got to.
  const go = e.target.closest('[data-go]');
  if (go) {
    let el = document.getElementById('p-' + go.dataset.go);
    while (!el && state.count < state.shown.length) { appendPosts(PAGE); el = document.getElementById('p-' + go.dataset.go); }
    if (el) {
      el.scrollIntoView({ block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
      el.focus({ preventScroll: true });
    }
    return;
  }
  const post = e.target.closest('.post');
  if (!post) return;
  const it = state.byId.get(post.dataset.id);
  if (!it) return;

  const like = e.target.closest('.like');
  if (like) { toggleLike(it, post); return; }

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
  $('span', btn).textContent = on ? 'Kept' : 'Keep';
  post.classList.toggle('kept', on);
  post.classList.toggle('pop', on);
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

// Day or night. "sun" switches at the sunrise and sunset in the newest
// weather post, and the last pair seen is kept so the next visit can choose
// before the feed has loaded.
function sunTimes() {
  const wx = state.items.find(it => it.type === 'weather' && !it.echo && it.sunrise && it.sunset);
  const rise = wx && clockMinutes(wx.sunrise), set = wx && clockMinutes(wx.sunset);
  if (rise != null && set != null) { store.set('noosphere.sun', [rise, set]); return [rise, set]; }
  return store.get('noosphere.sun', [390, 1080]);
}
function applyLight() {
  const light = store.get('noosphere.light', 'sun');
  let theme = light === 'night' ? 'night' : 'day';
  if (light === 'sun') {
    const [rise, set] = sunTimes();
    const now = new Date(), m = now.getHours() * 60 + now.getMinutes();
    theme = m >= rise && m < set ? 'day' : 'night';
  }
  document.documentElement.setAttribute('data-theme', theme);
  $('#themeColor').setAttribute('content', PAGE_COLOR[theme]);
}
sidebar.addEventListener('click', e => {
  const b = e.target.closest('[data-light]');
  if (!b) return;
  store.set('noosphere.light', b.dataset.light);
  applyLight();
  sidebar.querySelectorAll('[data-light]').forEach(x => x.setAttribute('aria-checked', x === b));
});
applyLight();

// Once a minute the sun moves along today's line, and the light may change.
setInterval(() => {
  applyLight();
  const now = new Date(), dot = $('.day.today .now');
  if (dot) dot.style.left = ((now.getHours() * 60 + now.getMinutes()) / 1440 * 100).toFixed(2) + '%';
}, 60 * 1000);

// Keyboard: J and K step through posts, L keeps one, slash searches.
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

renderTypebar(route());
loadFeed(true);
setInterval(() => loadFeed(false), 5 * 60 * 1000);

if ('serviceWorker' in navigator && location.protocol === 'https:') {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}
