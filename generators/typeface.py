#!/usr/bin/env python3
"""Typeface of the Week — a font specimen with its story.

Curated list of historically interesting typefaces with Claude commentary.
"""
import json, os, random
from utils import ask_claude, today, write_feed, feed_exists

TYPEFACES = [
    {"name": "Garamond", "designer": "Claude Garamond", "year": "c. 1530", "category": "serif", "hint": "French Renaissance. Based on Aldus Manutius's types. Still one of the most-used book faces in the world."},
    {"name": "Futura", "designer": "Paul Renner", "year": "1927", "category": "sans-serif", "hint": "Bauhaus-era geometry. Almost banned by the Nazis despite its German origin. Went to the moon on the Apollo 11 plaque."},
    {"name": "Helvetica", "designer": "Max Miedinger & Eduard Hoffmann", "year": "1957", "category": "sans-serif", "hint": "The default of modernity. Originally called Neue Haas Grotesk. Subway signs, corporate logos, the texture of the 20th century."},
    {"name": "Comic Sans", "designer": "Vincent Connare", "year": "1994", "category": "casual", "hint": "Designed for Microsoft Bob. Universally mocked, yet beloved by dyslexics for its readability. The most controversial typeface alive."},
    {"name": "Times New Roman", "designer": "Stanley Morison & Victor Lardent", "year": "1932", "category": "serif", "hint": "Commissioned by The Times of London for legibility. Became the default for bureaucracy, term papers, and looking 'serious.'"},
    {"name": "Baskerville", "designer": "John Baskerville", "year": "1757", "category": "serif", "hint": "Birmingham industrialist invented new paper, ink, and press to achieve unprecedented sharpness. Benjamin Franklin was a fan and prankster with it."},
    {"name": "Bodoni", "designer": "Giambattista Bodoni", "year": "1798", "category": "serif", "hint": "Italian neoclassical. Extreme contrast between thick and thin strokes. Fashion magazines and luxury brands still can't quit it."},
    {"name": "Palatino", "designer": "Hermann Zapf", "year": "1949", "category": "serif", "hint": "Zapf designed it at 25, named for 16th-century calligrapher Giambattista Palatino. One of the top 10 most-used typefaces ever."},
    {"name": "Gill Sans", "designer": "Eric Gill", "year": "1926", "category": "sans-serif", "hint": "The face of the BBC and British Rail. Gill himself was, by his own diary, a monstrous person. Can you separate type from typographer?"},
    {"name": "Fraktur", "designer": "Various", "year": "c. 1513", "category": "blackletter", "hint": "German blackletter. Made compulsory under the Nazis, then banned by them in 1941 when they decided it was 'Jewish.' A typeface whiplashed by ideology."},
    {"name": "Didot", "designer": "Firmin Didot", "year": "c. 1784", "category": "serif", "hint": "French counterpart to Bodoni. Hairline serifs, mathematical precision. The Didot family also invented stereotyping and the point system still used in type."},
    {"name": "Optima", "designer": "Hermann Zapf", "year": "1958", "category": "sans-serif", "hint": "Zapf sketched it on Swiss banknotes in a Florence church. Sans-serif but with tapered strokes like a Roman inscription. Used on the Vietnam Veterans Memorial."},
    {"name": "Courier", "designer": "Howard 'Bud' Kettler", "year": "1955", "category": "monospace", "hint": "Designed for IBM typewriters. Never copyrighted — IBM wanted every typewriter to use it. Became the face of screenplays, code, and bureaucratic documents."},
    {"name": "Johnston", "designer": "Edward Johnston", "year": "1916", "category": "sans-serif", "hint": "Created for the London Underground. The diamond-dotted 'i' and perfect 'O' became synonymous with London itself. Gill Sans is its (controversial) offspring."},
    {"name": "Caslon", "designer": "William Caslon", "year": "1722", "category": "serif", "hint": "The first great English typeface. Used to print the U.S. Declaration of Independence. 'When in doubt, use Caslon' was a real printers' maxim."},
    {"name": "Univers", "designer": "Adrian Frutiger", "year": "1957", "category": "sans-serif", "hint": "Frutiger designed 21 weights in a systematic grid — the first truly planned type family. More coherent than Helvetica, less famous."},
    {"name": "Zapfino", "designer": "Hermann Zapf", "year": "1998", "category": "script", "hint": "Zapf's calligraphic dream — 1,400 glyphs, contextual alternates, four alphabets. Apple shipped it with every Mac. The antithesis of Helvetica."},
    {"name": "Fira Code", "designer": "Nikita Prokopov", "year": "2014", "category": "monospace", "hint": "Programming ligatures: != becomes ≠, -> becomes →. The first typeface designed around the idea that code is meant to be read, not just written."},
    {"name": "JetBrains Mono", "designer": "Philipp Nurullin & Konstantin Bulenkov", "year": "2020", "category": "monospace", "hint": "Designed specifically for reading code 8 hours a day. Increased x-height, functional ligatures. Anna's daily driver."},
    {"name": "Berkeley Mono", "designer": "Neil Panchal", "year": "2023", "category": "monospace", "hint": "Indie type foundry, $75 license. Sharp, opinionated, beloved by terminal enthusiasts. The new status symbol of 'I care about my dev environment.'"},
    {"name": "Inter", "designer": "Rasmus Andersson", "year": "2017", "category": "sans-serif", "hint": "Designed for computer screens. Open source. Became the default UI font for half the internet. The Helvetica of the 2020s."},
    {"name": "IBM Plex", "designer": "Mike Abbink", "year": "2017", "category": "family", "hint": "IBM's first custom corporate typeface in 50 years. Replaces Helvetica Neue. Four subfamilies including a gorgeous monospace."},
    {"name": "Blackletter (Textura)", "designer": "Various scribes", "year": "c. 1150", "category": "blackletter", "hint": "The hand of the medieval scriptorium. Gutenberg's Bible used it. Still appears on newspaper mastheads, metal albums, and Disneyland signage."},
    {"name": "OCR-B", "designer": "Adrian Frutiger", "year": "1968", "category": "monospace", "hint": "Designed to be readable by both humans and machines. Used on passports, checks, and UPC codes worldwide. A font at the boundary of human and computer vision."},
    {"name": "Cooper Black", "designer": "Oswald Bruce Cooper", "year": "1922", "category": "serif", "hint": "The chunky, friendly face of the 1970s. Pet Sounds, easyJet, Tootsie Roll. Called 'the friendliest typeface in the world.'"},
    {"name": "DIN 1451", "designer": "German standards committee", "year": "1931", "category": "sans-serif", "hint": "Designed by committee for German road signs and engineering. Industrial, functional, unlovely — and accidentally beautiful. Now in every design studio."},
    {"name": "Sabon", "designer": "Jan Tschichold", "year": "1967", "category": "serif", "hint": "Named for Jacques Sabon, who brought Garamond's matrices to Frankfurt. Tschichold designed it to work identically on three competing typesetting systems."},
    {"name": "Papyrus", "designer": "Chris Costello", "year": "1983", "category": "decorative", "hint": "Costello hand-drew it over 6 months with calligraphy and textured paper. It ended up on Avatar, every yoga studio, and countless church bulletins. A design crime or a democratic masterpiece?"},
    {"name": "Trajan", "designer": "Carol Twombly", "year": "1989", "category": "serif", "hint": "Based on the inscription on Trajan's Column in Rome (113 CE). Used on more movie posters than any other font. All caps — the original had no lowercase."},
    {"name": "Gotham", "designer": "Tobias Frere-Jones", "year": "2000", "category": "sans-serif", "hint": "Inspired by mid-century New York architectural signage. Obama's 2008 campaign typeface. Subject of a bitter legal battle between Frere-Jones and Hoefler."},
    {"name": "Iosevka", "designer": "Belleve Invis (be5invis)", "year": "2015", "category": "monospace", "hint": "Open source, infinitely customizable. 700+ build parameters. The 'Linux of typefaces' — you can compile your own version with exactly the features you want."},
    {"name": "Source Code Pro", "designer": "Paul D. Hunt", "year": "2012", "category": "monospace", "hint": "Adobe's first open-source type family. Designed for code readability. Distinguished 0/O, 1/l/I. The workhorse of VS Code defaults."},
]

STATE_FILE = os.path.join(os.path.dirname(__file__), '.typeface-state.json')

def get_next_typeface():
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
    used = set(state.get('used', []))
    available = [i for i in range(len(TYPEFACES)) if i not in used]
    if not available:
        used = set()
        available = list(range(len(TYPEFACES)))
    idx = random.choice(available)
    used.add(idx)
    with open(STATE_FILE, 'w') as f:
        json.dump({'used': list(used)}, f)
    return TYPEFACES[idx]

def generate():
    name = f"{today()}-typeface"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    tf = get_next_typeface()

    prompt = f"""Write about this typeface:

Name: {tf['name']}
Designer: {tf['designer']}
Year: {tf['year']}
Category: {tf['category']}
Context: {tf['hint']}

Write 3-5 sentences. Focus on the STORY — who made it, why, what world it was born into, 
and what it says about the era that needed it. If there's drama, scandal, or irony, lean into it.
What does using this typeface mean today? What are you saying by choosing it?

End with a specimen sentence — a sentence that shows off the typeface's character, 
written in a way that matches the font's personality.

Use HTML tags (<em>, <strong>) not markdown. Keep commentary under 120 words."""

    system = "You are a type historian who believes typefaces are portraits of their time — each one encodes the anxieties, aspirations, and aesthetics of the era that produced it. You write with the precision of a designer and the narrative instinct of a biographer."

    content = ask_claude(prompt, system=system, max_tokens=450, temperature=0.85)

    specimen_url = ''

    write_feed(name, {
        "type": "typeface",
        "timestamp": f"{today()}T09:30:00",
        "font_name": tf['name'],
        "designer": tf['designer'],
        "year": tf['year'],
        "category": tf['category'],
        "content": content,
        "specimen_url": specimen_url,
    })

if __name__ == '__main__':
    generate()
