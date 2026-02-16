#!/usr/bin/env python3
"""The Dead Medium — weekly profile of a defunct or dying communication technology."""
import json, os, random
from utils import ask_claude, today, write_feed, feed_exists

# Curated list of dead/dying media — enough for ~2 years at weekly cadence
MEDIA = [
    {"name": "Pneumatic tube mail", "dates": "1853–1960s", "hint": "pressurized air tubes carrying capsules of mail under cities"},
    {"name": "The Chappe telegraph", "dates": "1794–1855", "hint": "semaphore towers across France, arms spelling messages"},
    {"name": "Telex", "dates": "1933–2000s", "hint": "typewriter-to-typewriter over telephone lines"},
    {"name": "Soviet samizdat", "dates": "1950s–1989", "hint": "underground self-publishing, hand-typed carbon copies"},
    {"name": "Carrier pigeons", "dates": "antiquity–1950s", "hint": "homing pigeons carrying messages, used through both World Wars"},
    {"name": "The heliograph", "dates": "1820s–1960s", "hint": "mirrors reflecting sunlight in Morse code over vast distances"},
    {"name": "Fax machine", "dates": "1964–present (barely)", "hint": "scanning and transmitting images over phone lines"},
    {"name": "Pager/Beeper", "dates": "1950–2000s", "hint": "one-way numeric messages, '911' meant call me now"},
    {"name": "The telegraph", "dates": "1837–1960s", "hint": "dots and dashes over copper wire, changed the speed of news"},
    {"name": "Teletext", "dates": "1974–2010s", "hint": "text and crude graphics broadcast in TV signal gaps"},
    {"name": "The mimeograph", "dates": "1876–1990s", "hint": "ink-through-stencil duplicator, smell of fresh copies"},
    {"name": "Usenet", "dates": "1980–present (barely)", "hint": "decentralized discussion system before the web"},
    {"name": "The town crier", "dates": "medieval–1800s", "hint": "human broadcasting, 'Oyez!' three times to get attention"},
    {"name": "Drum telegraphy", "dates": "antiquity–present (rare)", "hint": "tonal languages encoded in drumbeats across miles"},
    {"name": "The penny post", "dates": "1680–evolved", "hint": "affordable mail for everyone, not just the rich"},
    {"name": "Shortwave radio broadcasting", "dates": "1920s–declining", "hint": "voices bouncing off the ionosphere, reaching the world"},
    {"name": "The ditto machine", "dates": "1923–1990s", "hint": "spirit duplicator, purple ink, intoxicating chemical smell"},
    {"name": "CB radio", "dates": "1945–1990s peak", "hint": "citizens band, truckers and hobbyists, '10-4 good buddy'"},
    {"name": "Intelpost", "dates": "1980–2003", "hint": "international electronic mail via postal services"},
    {"name": "The Aldis lamp", "dates": "1867–present (naval)", "hint": "shuttered lamp flashing Morse code between ships"},
    {"name": "Minitel", "dates": "1982–2012", "hint": "France's proto-internet, free terminals in every home"},
    {"name": "The optical telegraph", "dates": "1790s–1850s", "hint": "chains of towers with shutters, faster than horseback"},
    {"name": "Dictation machines", "dates": "1877–2000s", "hint": "recording speech for later transcription by a secretary"},
    {"name": "The Autotel", "dates": "1971–1990s", "hint": "early mobile phone system, car-mounted, operator-connected"},
    {"name": "Viewdata/Prestel", "dates": "1979–1994", "hint": "interactive information service via telephone and TV"},
    {"name": "The smoke signal", "dates": "antiquity–1800s", "hint": "fire and blanket, visible for miles, pre-agreed codes"},
    {"name": "The semaphore flag system", "dates": "1800s–present (ceremonial)", "hint": "two flags held at angles spelling letters"},
    {"name": "Fidonet", "dates": "1984–present (barely)", "hint": "bulletin board system network, store-and-forward over phone lines"},
    {"name": "The Eidophone", "dates": "1870s", "hint": "device for visualizing sound waves as patterns in sand"},
    {"name": "The Phonautograph", "dates": "1857–1870s", "hint": "recorded sound before the phonograph — but couldn't play it back"},
    {"name": "The Vocoder", "dates": "1928–evolved", "hint": "speech compression for secure military communication"},
    {"name": "The Memex", "dates": "1945 (concept)", "hint": "Vannevar Bush's hypothetical desk with microfilm hyperlinks"},
    {"name": "Acoustic coupler modem", "dates": "1958–1990s", "hint": "rubber cups on a telephone handset, 300 baud"},
    {"name": "The Telharmonium", "dates": "1897–1914", "hint": "200-ton instrument that broadcast music over telephone lines"},
    {"name": "The Wirephoto", "dates": "1935–2000s", "hint": "transmitting photographs over telephone wires for newspapers"},
    {"name": "The Blue Box", "dates": "1960s–1980s", "hint": "tone generators to hack the phone system, Wozniak and Jobs built them"},
    {"name": "Aerogramme / Air letter", "dates": "1933–declining", "hint": "single sheet that folded into its own envelope, lightweight for airmail"},
    {"name": "The Telescribe", "dates": "1910s", "hint": "Edison's machine to record both sides of a phone call"},
    {"name": "Xerography (early)", "dates": "1938–evolved", "hint": "dry photocopying, changed how information moved in offices"},
    {"name": "The chain letter", "dates": "1888–evolved (now spam)", "hint": "self-replicating message, early viral content"},
    {"name": "Electroencephalophone", "dates": "1934", "hint": "converting brain waves to sound, early brain-computer interface"},
    {"name": "The Photophone", "dates": "1880", "hint": "Bell's invention to transmit sound on a beam of light"},
    {"name": "Newsreel", "dates": "1910–1967", "hint": "short news films shown before feature films in cinemas"},
    {"name": "The personal ad", "dates": "1695–evolved (Tinder)", "hint": "strangers seeking strangers through newspaper columns"},
    {"name": "The dead drop", "dates": "espionage tradition", "hint": "physical location where messages are left without meeting"},
    {"name": "Message in a bottle", "dates": "antiquity–present", "hint": "sealed communication entrusted to ocean currents"},
    {"name": "BBS (Bulletin Board System)", "dates": "1978–1990s", "hint": "dial-up communities, one caller at a time, ANSI art"},
    {"name": "The singing telegram", "dates": "1933–declining", "hint": "Western Union's musical message delivery service"},
    {"name": "The pneumatic dispatch", "dates": "1853–1960s", "hint": "city-wide tube systems for mail and small packages"},
    {"name": "The mechanical semaphore", "dates": "1684–1850s", "hint": "Robert Hooke's proposal for visual telegraphy"},
    {"name": "IRC (Internet Relay Chat)", "dates": "1988–declining", "hint": "real-time text chat, channels, the social internet before social media"},
    {"name": "The Zoetrope", "dates": "1834–1900s", "hint": "spinning cylinder of sequential images creating motion"},
    {"name": "Wax cylinder recording", "dates": "1886–1929", "hint": "Edison's cylinders, each one unique, no mass production"},
    {"name": "8-track tape", "dates": "1964–1988", "hint": "continuous loop cartridge, no rewinding, click between programs"},
    {"name": "The LaserDisc", "dates": "1978–2001", "hint": "12-inch optical disc, beautiful picture, never went mainstream"},
    {"name": "MiniDisc", "dates": "1992–2013", "hint": "Sony's elegant, recordable optical disc, beloved in Japan"},
    {"name": "The answering machine", "dates": "1935–2010s", "hint": "magnetic tape recording callers' messages when you weren't home"},
    {"name": "Dot-matrix printer", "dates": "1970–2000s", "hint": "pins striking ribbon, tearing off perforated edges"},
    {"name": "The rolodex", "dates": "1956–2000s", "hint": "rotating file of contact cards, the original contacts app"},
    {"name": "Carbon paper", "dates": "1806–declining", "hint": "thin coated paper creating duplicates, 'cc' still means carbon copy"},
    {"name": "The magic lantern", "dates": "1659–1900s", "hint": "projected images from painted glass slides, proto-cinema"},
]

STATE_FILE = os.path.join(os.path.dirname(__file__), '.dead-medium-state.json')

def get_next_medium():
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
    used = set(state.get('used', []))
    available = [i for i in range(len(MEDIA)) if i not in used]
    if not available:
        used = set()
        available = list(range(len(MEDIA)))
    idx = random.choice(available)
    used.add(idx)
    with open(STATE_FILE, 'w') as f:
        json.dump({'used': list(used)}, f)
    return MEDIA[idx]

def generate():
    name = f"{today()}-dead-medium"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    medium = get_next_medium()

    prompt = f"""Write a short elegy for this dead or dying communication technology:

Name: {medium['name']}
Active: {medium['dates']}
What it was: {medium['hint']}

Write 3-5 sentences. Focus on what was LOST when it died — not just what replaced it, 
but what quality of human connection or experience disappeared with it. 
Be specific and sensory. What did it sound like, feel like, smell like to use?

End with one sentence connecting it to something contemporary — what would this technology 
think of how we communicate now?

Use HTML tags (<em>, <strong>) not markdown. Keep it under 120 words."""

    system = "You are a media archaeologist who writes eulogies for dead technologies. Your tone is elegiac but not sentimental — you mourn what was lost while acknowledging why things changed. You notice the sensory and social dimensions that history books skip."

    content = ask_claude(prompt, system=system, max_tokens=400, temperature=0.85)

    write_feed(name, {
        "type": "dead_medium",
        "timestamp": f"{today()}T10:00:00",
        "title": medium['name'],
        "dates": medium['dates'],
        "content": content,
    })

if __name__ == '__main__':
    generate()
