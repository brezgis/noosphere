#!/usr/bin/env python3
"""The Untranslatable — words that resist clean translation, with cultural meditation."""
import json, os, random
from utils import ask_claude, today, write_feed, feed_exists

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
    {"word": "toska", "language": "Russian (тоска)", "hint": "Nabokov: 'No single word in English renders all the shades of toska'"},
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

STATE_FILE = os.path.join(os.path.dirname(__file__), '.untranslatable-state.json')

def get_next_word():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
        used = set(state.get('used', []))
    else:
        used = set()
    
    available = [i for i in range(len(WORDS)) if i not in used]
    if not available:
        used = set()
        available = list(range(len(WORDS)))
    
    idx = random.choice(available)
    used.add(idx)
    with open(STATE_FILE, 'w') as f:
        json.dump({'used': list(used)}, f)
    return WORDS[idx]

def generate():
    name = f"{today()}-untranslatable"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    entry = get_next_word()

    prompt = f"""Write about the untranslatable word "{entry['word']}" ({entry['language']}).
Approximate meaning: {entry['hint']}

Write 3-5 sentences exploring what this word reveals about the culture that created it.
What does it mean that English doesn't have this word? What does its existence tell us 
about how speakers of {entry['language'].split('(')[0].strip()} carve up experience differently?

Connect it, if natural, to computational linguistics — how would a distributional model 
trained on this language represent this concept vs. one trained on English? 
What would the embedding space look like?

End with a provocative question (italicized). Keep it under 120 words.
No intro like "This word..." — start in the middle of the idea."""

    system = "You are a linguistic anthropologist with expertise in lexical typology and computational semantics. Your writing is precise but warm, academic but accessible."

    content = ask_claude(prompt, system=system, max_tokens=400, temperature=0.85)
    
    # Extract question if it ends with one
    lines = content.strip().split('\n')
    question = None
    if lines[-1].strip().endswith('?'):
        question = lines[-1].strip().strip('*').strip('_')
        content = '\n'.join(lines[:-1]).strip()

    write_feed(name, {
        "type": "untranslatable",
        "timestamp": f"{today()}T15:00:00",
        "word": entry['word'],
        "language": entry['language'],
        "content": content,
        "question": question,
    })

if __name__ == '__main__':
    generate()
