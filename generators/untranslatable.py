#!/usr/bin/env python3
"""The Untranslatable. Words that resist a one-word English gloss.

Each card shows the word, a short gloss from the curated list below, and the
dictionary senses from the English Wiktionary entry for that word in its own
language. No model writes anything here.
"""
import json, os, random, urllib.parse
from utils import today, write_feed, feed_exists, wiktionary_definitions, SourceUnavailable

# Seed corpus — deep cuts, not the usual suspects
WORDS = [
    {"word": "тоска", "language": "Russian", "hint": "spiritual anguish without cause"},
    {"word": "saudade", "language": "Portuguese", "hint": "longing for something absent"},
    {"word": "木漏れ日", "language": "Japanese (komorebi)", "hint": "sunlight filtering through leaves"},
    {"word": "Weltanschauung", "language": "German", "hint": "a comprehensive worldview"},
    {"word": "mamihlapinatapai", "language": "Yaghan", "hint": "a mutual unspoken desire"},
    {"word": "hyggelig", "language": "Danish", "hint": "cozy intimacy, warm atmosphere"},
    {"word": "Sehnsucht", "language": "German", "hint": "deep longing for an alternative life"},
    {"word": "wabi-sabi", "language": "Japanese (侘寂)", "hint": "beauty of imperfection and transience"},
    {"word": "duende", "language": "Spanish", "hint": "the spirit of art that moves toward death"},
    {"word": "Fernweh", "language": "German", "hint": "ache for distant places"},
    {"word": "hiraeth", "language": "Welsh", "hint": "homesickness for a home you can't return to"},
    {"word": "meraki", "language": "Greek (μεράκι)", "hint": "doing something with soul and creativity"},
    {"word": "ubuntu", "language": "Zulu/Xhosa", "hint": "I am because we are"},
    {"word": "ikigai", "language": "Japanese (生き甲斐)", "hint": "a reason for being"},
    {"word": "Torschlusspanik", "language": "German", "hint": "gate-closing panic, fear of diminishing opportunities"},
    {"word": "jayus", "language": "Indonesian", "hint": "a joke so unfunny it becomes funny"},
    {"word": "Backpfeifengesicht", "language": "German", "hint": "a face that invites a slap"},
    {"word": "aware", "language": "Japanese (哀れ, mono no aware)", "hint": "the pathos of things, gentle sadness of passing"},
    {"word": "razliubit", "language": "Russian (разлюбить)", "hint": "to fall out of love — a single verb"},
    {"word": "litost", "language": "Czech", "hint": "Kundera: torment at the sight of one's own misery"},
    {"word": "Schadenfreude", "language": "German", "hint": "pleasure from another's misfortune"},
    {"word": "dépaysement", "language": "French", "hint": "disorientation of being in a foreign country"},
    {"word": "Gemütlichkeit", "language": "German", "hint": "coziness, belonging, social warmth"},
    {"word": "пошлость", "language": "Russian (poshlost')", "hint": "Nabokov's untranslatable: vulgar self-satisfied mediocrity"},
    {"word": "yugen", "language": "Japanese (幽玄)", "hint": "profound mysterious beauty"},
    {"word": "querencia", "language": "Spanish", "hint": "a place where one feels safe, draws strength from"},
    {"word": "Waldeinsamkeit", "language": "German", "hint": "the feeling of being alone in the woods"},
    {"word": "sobremesa", "language": "Spanish", "hint": "time spent lingering at the table after eating"},
    {"word": "verschlimmbessern", "language": "German", "hint": "to make worse by trying to improve"},
    {"word": "gökotta", "language": "Swedish", "hint": "dawn picnic to hear the first birdsong"},
    {"word": "desenrascanço", "language": "Portuguese", "hint": "artful improvisation, pulling a solution out of nothing"},
    {"word": "Handschuhschneeballwerfer", "language": "German", "hint": "coward who throws snowballs with gloves on"},
    {"word": "shemomedjamo", "language": "Georgian (შემომეჭამა)", "hint": "eating past fullness because it tastes so good"},
    {"word": "forelsket", "language": "Norwegian", "hint": "the euphoria of falling in love"},
    {"word": "hygge", "language": "Danish", "hint": "creating warm atmosphere, enjoying the good things in life"},
    {"word": "pochemuchka", "language": "Russian (почемучка)", "hint": "a person who asks too many questions"},
    {"word": "Kummerspeck", "language": "German", "hint": "grief bacon — weight gained from emotional overeating"},
    {"word": "tsundoku", "language": "Japanese (積ん読)", "hint": "buying books and letting them pile up unread"},
    {"word": "ennui", "language": "French", "hint": "existential boredom — deeper than English 'boredom'"},
    {"word": "uitwaaien", "language": "Dutch", "hint": "walking in the wind to clear your head"},
    {"word": "cafuné", "language": "Brazilian Portuguese", "hint": "running fingers through someone's hair"},
    {"word": "Luftschloss", "language": "German", "hint": "air castle — an impossible dream"},
    {"word": "nyelv", "language": "Hungarian", "hint": "means both 'tongue' and 'language' — no distinction"},
    {"word": "Sprachgefühl", "language": "German", "hint": "intuitive feeling for language, linguistic instinct"},
    {"word": "taarradhin", "language": "Arabic (تراضين)", "hint": "a happy compromise where everyone wins"},
    {"word": "ilunga", "language": "Tshiluba", "hint": "readiness to forgive a first time, tolerate a second, never a third"},
    {"word": "ya'aburnee", "language": "Arabic (يقبرني)", "hint": "'you bury me' — wanting to die before a loved one"},
    {"word": "gezellig", "language": "Dutch", "hint": "cozy, fun, warm atmosphere with friends"},
    {"word": "Zeitgeist", "language": "German", "hint": "spirit of the age — but more alive than 'zeitgeist'"},
]

# Where each word lives on en.wiktionary: (page title, language heading).
# Words missing here are looked up under their own spelling and language.
WIKTIONARY = {
    "木漏れ日": ("木漏れ日", "Japanese"),
    "mamihlapinatapai": ("mamihlapinatapai", "Yagán"),
    "wabi-sabi": ("侘寂", "Japanese"),
    "meraki": ("μεράκι", "Greek"),
    "ubuntu": ("ubuntu", "Zulu"),
    "ikigai": ("生き甲斐", "Japanese"),
    "aware": ("哀れ", "Japanese"),
    "razliubit": ("разлюбить", "Russian"),
    "litost": ("lítost", "Czech"),
    "пошлость": ("пошлость", "Russian"),
    "yugen": ("幽玄", "Japanese"),
    "shemomedjamo": ("შემომეჭამა", "Georgian"),
    "forelsket": ("forelsket", "Norwegian Bokmål"),
    "pochemuchka": ("почемучка", "Russian"),
    "tsundoku": ("積ん読", "Japanese"),
    "cafuné": ("cafuné", "Portuguese"),
    "taarradhin": ("تراضين", "Arabic"),
    "ilunga": ("ilunga", "Luba-Kasai"),
    "ya'aburnee": ("يقبرني", "Arabic"),
}

STATE_FILE = os.path.join(os.path.dirname(__file__), '.untranslatable-state.json')


def load_used():
    try:
        with open(STATE_FILE) as f:
            return set(json.load(f).get('used', []))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return set()


def mark_used(used, idx):
    if len(used) >= len(WORDS) - 1 and idx not in used:
        used = set()  # the pool is exhausted, so the cycle starts again
    used.add(idx)
    with open(STATE_FILE, 'w') as f:
        json.dump({'used': sorted(used)}, f)


def generate():
    name = f"{today()}-untranslatable"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    used = load_used()
    available = [i for i in range(len(WORDS)) if i not in used]
    idx = random.choice(available or list(range(len(WORDS))))
    entry = WORDS[idx]
    language = entry['language'].split('(')[0].strip()
    page, wlang = WIKTIONARY.get(entry['word'], (entry['word'], language))
    try:
        senses = wiktionary_definitions(page, wlang, limit=3)
    except SourceUnavailable as e:
        print(f"Source unavailable, will retry on the next run: {e}")
        return

    write_feed(name, {
        "type": "untranslatable",
        "v": 2,
        "timestamp": f"{today()}T15:00:00",
        "word": entry['word'],
        "native": page if page != entry['word'] else "",
        "language": language,
        "gloss": entry['hint'],
        "senses": [{"pos": pos, "text": text} for pos, text in senses],
        "url": "https://en.wiktionary.org/wiki/" + urllib.parse.quote(page) + "#" + wlang.replace(' ', '_'),
    })
    mark_used(used, idx)


if __name__ == '__main__':
    generate()
