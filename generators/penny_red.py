#!/usr/bin/env python3
"""The Penny Red — a renamed, erased, or contested place. What used to be here?

Uses real toponymy data: renamed cities, erased indigenous names, 
politically contested places, disappeared towns.
"""
import json, os, random
from utils import ask_claude, today, write_feed, feed_exists

# Curated list of renamed/erased/contested places
PLACES = [
    {"current": "Istanbul", "former": "Constantinople / Byzantium / Lygos", "country": "Turkey", "hint": "Three empires, three names, one strait"},
    {"current": "Mumbai", "former": "Bombay", "country": "India", "hint": "Renamed 1995; the old name was Portuguese, from 'Bom Bahia'"},
    {"current": "St. Petersburg", "former": "Petrograd / Leningrad", "country": "Russia", "hint": "Four names in one century: Sankt-Piterburkh → Petrograd → Leningrad → back"},
    {"current": "Ho Chi Minh City", "former": "Saigon / Prey Nokor", "country": "Vietnam", "hint": "Khmer fishing village → French colonial jewel → revolutionary rebrand"},
    {"current": "Denali", "former": "Mt. McKinley", "country": "USA", "hint": "Koyukon Athabascan name restored in 2015 after 98 years"},
    {"current": "Lake Chargoggagoggmanchauggagoggchaubunagungamaugg", "former": "Webster Lake", "country": "USA", "hint": "Nipmuc name meaning 'you fish on your side, I fish on my side, nobody fishes in the middle'"},
    {"current": "Zimbabwe", "former": "Rhodesia / Great Zimbabwe", "country": "Zimbabwe", "hint": "Named for stone ruins that colonialists refused to believe Africans built"},
    {"current": "Uluru", "former": "Ayers Rock", "country": "Australia", "hint": "Pitjantjatjara name restored; climbing banned in 2019 out of respect"},
    {"current": "Kaliningrad", "former": "Königsberg", "country": "Russia", "hint": "Kant's city, Euler's bridges, emptied of Germans in 1945"},
    {"current": "Taipei", "former": "Wanhua / Bangka / Taihoku", "country": "Taiwan", "hint": "Ketagalan → Hoklo → Japanese → Mandarin, each renaming a conquest"},
    {"current": "Volgograd", "former": "Stalingrad / Tsaritsyn", "country": "Russia", "hint": "De-Stalinified in 1961; still called Stalingrad on Victory Day"},
    {"current": "Oslo", "former": "Christiania / Kristiania", "country": "Norway", "hint": "Reverted to its medieval Norse name in 1925"},
    {"current": "Nuuk", "former": "Godthåb", "country": "Greenland", "hint": "Danish name meant 'Good Hope'; Kalaallisut name means 'cape'"},
    {"current": "Chennai", "former": "Madras / Madraspatinam", "country": "India", "hint": "Renamed 1996; some say 'Madras' was Portuguese, others say it was always there"},
    {"current": "Beijing", "former": "Peking / Beiping / Khanbaliq / Zhongdu / Yanjing", "country": "China", "hint": "Capital of five dynasties, each with its own name"},
    {"current": "Kolkata", "former": "Calcutta", "country": "India", "hint": "Anglicized Bengali restored to its pronunciation in 2001"},
    {"current": "Centralia, PA", "former": "Centralia", "country": "USA", "hint": "Ghost town since 1962 coal mine fire; still burning underground, population: 5"},
    {"current": "Pripyat", "former": "Pripyat", "country": "Ukraine", "hint": "Not renamed — erased. Evacuated in 36 hours, frozen in 1986"},
    {"current": "New Amsterdam", "former": "Lenapehoking", "country": "USA", "hint": "Became New York in 1664; before the Dutch, it was Lenape land"},
    {"current": "Gdańsk", "former": "Danzig", "country": "Poland", "hint": "Free City, Prussian, Polish, German, Polish again — the city that started WWII"},
    {"current": "Thessaloniki", "former": "Selanik / Solun", "country": "Greece", "hint": "Ottoman Selanik was majority Sephardic Jewish; nearly all killed in the Holocaust"},
    {"current": "Lviv", "former": "Lwów / Lemberg / Lvov", "country": "Ukraine", "hint": "Polish → Austrian → Polish → Soviet → Ukrainian, four names still in use"},
    {"current": "Edo", "former": "Edo → Tokyo", "country": "Japan", "hint": "'Eastern Capital' — renamed when the emperor moved from Kyoto in 1868"},
    {"current": "Mesopotamia", "former": "Iraq / Al-Iraq", "country": "Iraq", "hint": "Greek name meaning 'between rivers' for a place that named itself differently"},
    {"current": "Tenochtitlan", "former": "Mexico City", "country": "Mexico", "hint": "Aztec island city razed and built over by Cortés; sinking into the lakebed it erased"},
    {"current": "Aotearoa", "former": "New Zealand", "country": "New Zealand", "hint": "Māori name gaining official status; 'Land of the Long White Cloud'"},
    {"current": "Salisbury → Harare", "former": "Harare", "country": "Zimbabwe", "hint": "Named for Lord Salisbury until 1982; Shona name means 'one who does not sleep'"},
    {"current": "Saigon District 1", "former": "Saigon", "country": "Vietnam", "hint": "The name survived as a district inside the city that replaced it"},
    {"current": "Leningrad Oblast", "former": "Leningrad Oblast", "country": "Russia", "hint": "The city became St. Petersburg again, but the region around it stayed Leningrad"},
    {"current": "Cahokia", "former": "(erased)", "country": "USA", "hint": "Larger than London in 1100 CE; by 1400, abandoned; by 1800, forgotten"},
    {"current": "Ezo → Hokkaido", "former": "Hokkaido", "country": "Japan", "hint": "Renamed in 1869 during Meiji colonization of Ainu lands"},
    {"current": "East Pakistan → Bangladesh", "former": "Bangladesh", "country": "Bangladesh", "hint": "'Land of Bengal' — a country born from a linguistic identity in 1971"},
    {"current": "Batavia → Jakarta", "former": "Sunda Kelapa / Jayakarta / Batavia", "country": "Indonesia", "hint": "Sundanese port → Muslim victory city → Dutch colonial capital → independence name"},
    {"current": "Sandwich Islands → Hawaii", "former": "Hawaii", "country": "USA", "hint": "Captain Cook named them for the Earl of Sandwich; annexed 1898 against Hawaiians' will"},
    {"current": "Van Diemen's Land → Tasmania", "former": "Tasmania", "country": "Australia", "hint": "Renamed 1856 to escape the penal colony stigma; the Palawa people had older names"},
    {"current": "Formosa → Taiwan", "former": "Taiwan", "country": "Taiwan", "hint": "Portuguese 'Ilha Formosa' (beautiful island); indigenous Austronesian peoples were there 6000 years earlier"},
    {"current": "Ceylon → Sri Lanka", "former": "Sri Lanka", "country": "Sri Lanka", "hint": "Colonial name shed in 1972; 'Lanka' appears in the Ramayana"},
    {"current": "Persia → Iran", "former": "Iran", "country": "Iran", "hint": "Reza Shah requested the change in 1935; 'Iran' means 'land of the Aryans' in Old Persian"},
    {"current": "Siam → Thailand", "former": "Thailand", "country": "Thailand", "hint": "'Land of the Free' — the only Southeast Asian country never colonized by Europe"},
    {"current": "Nyaminyami → Lake Kariba", "former": "Kariba", "country": "Zambia/Zimbabwe", "hint": "The Tonga people's river god supposedly caused earthquakes during dam construction"},
    {"current": "Doggerland", "former": "(submerged)", "country": "North Sea", "hint": "Connected Britain to Europe until ~6500 BCE; now 20m underwater; fishing boats dredge up mammoth bones"},
    {"current": "Zealandia", "former": "(submerged)", "country": "Pacific Ocean", "hint": "Earth's 8th continent, 94% underwater; New Zealand is its mountaintops"},
    {"current": "Beringia", "former": "(submerged)", "country": "Bering Strait", "hint": "The land bridge humans walked to reach the Americas; now 50m under the sea"},
    {"current": "Tombstone, AZ", "former": "Goose Flats", "country": "USA", "hint": "Ed Schieffelin was told he'd only find his tombstone; found silver instead, named the town"},
    {"current": "Truth or Consequences, NM", "former": "Hot Springs", "country": "USA", "hint": "Renamed in 1950 after a radio game show offered to broadcast from any town that took its name"},
    {"current": "Rough and Ready, CA", "former": "Rough and Ready", "country": "USA", "hint": "Briefly seceded from the Union in 1850 to avoid a mining tax; rejoined for July 4th liquor"},
]

STATE_FILE = os.path.join(os.path.dirname(__file__), '.penny-red-state.json')

def get_next_place():
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
    used = set(state.get('used', []))
    available = [i for i in range(len(PLACES)) if i not in used]
    if not available:
        used = set()
        available = list(range(len(PLACES)))
    idx = random.choice(available)
    used.add(idx)
    with open(STATE_FILE, 'w') as f:
        json.dump({'used': list(used)}, f)
    return PLACES[idx]

def generate():
    name = f"{today()}-penny-red"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    place = get_next_place()

    prompt = f"""Write about this renamed/erased/contested place:

Current name: {place['current']}
Former name(s): {place['former']}
Country: {place['country']}
Context: {place['hint']}

Write 3-5 sentences about what the name change reveals — about power, memory, identity, 
or the politics of cartography. Who named it? Who lost their name? What does the old name 
remember that the new one forgets (or vice versa)?

Be specific and vivid. This is about the human stories compressed into place names.
Use HTML tags (<em>, <strong>) not markdown. Keep it under 120 words."""

    system = "You are a critical toponymist — someone who reads the politics and grief encoded in place names. Your tone is precise, evocative, and attuned to what maps choose to remember and forget."

    content = ask_claude(prompt, system=system, max_tokens=400, temperature=0.8)

    write_feed(name, {
        "type": "penny_red",
        "timestamp": f"{today()}T11:00:00",
        "current_name": place['current'],
        "former_name": place['former'],
        "country": place['country'],
        "content": content,
    })

if __name__ == '__main__':
    generate()
