#!/usr/bin/env python3
"""Recipe — a seasonal recipe card with an etymology Easter egg.

Non-interactive. Weekly card with a real recipe + the etymological story of a key ingredient.
"""
import json, os, random
from datetime import datetime
from utils import ask_claude, today, write_feed, feed_exists

# Seasonal ingredients with etymological seeds, grouped by rough month range
INGREDIENTS = {
    "winter": [  # Dec-Feb
        {"name": "blood orange", "hint": "Citrus sinensis mutation, possibly from Sicily or China"},
        {"name": "parsnip", "hint": "From Latin pastinaca; confused with carrots until the 17th century"},
        {"name": "rutabaga", "hint": "Swedish 'rotabagge' (root bag); also called swede, neep, turnip (but isn't one)"},
        {"name": "black truffle", "hint": "Latin tuber → Old French trufe → English truffle; 'the diamond of the kitchen'"},
        {"name": "Meyer lemon", "hint": "Named for Frank Meyer, USDA explorer who found it in Beijing in 1908"},
        {"name": "cardoon", "hint": "Wild ancestor of the artichoke; from Arabic 'kharshūf' → Spanish 'cardo'"},
        {"name": "sunchoke", "hint": "Not from Jerusalem, not an artichoke. 'Girasole' (sunflower in Italian) → folk etymology → Jerusalem"},
        {"name": "pomelo", "hint": "Possibly from Dutch 'pompelmoes'; the ancestor of grapefruit"},
        {"name": "celeriac", "hint": "Celery's ugly cousin, cultivated for its root instead of stalks"},
        {"name": "kumquat", "hint": "Cantonese 'gam gwat' (金橘) meaning 'golden orange'; you eat the peel"},
        {"name": "black garlic", "hint": "Not fermented — Maillard-reacted over weeks at low heat. Sweet, umami, sticky."},
        {"name": "buckwheat", "hint": "Not wheat, not related to wheat. A fruit seed related to rhubarb and sorrel."},
    ],
    "spring": [  # Mar-May
        {"name": "ramps", "hint": "Appalachian wild leek; from Old English 'hramsa'; the first green thing after winter"},
        {"name": "fiddlehead fern", "hint": "The coiled frond of ostrich fern; eaten for millennia by First Nations peoples"},
        {"name": "morel", "hint": "From Old French 'morille'; possibly related to 'maurus' (dark/Moorish)"},
        {"name": "asparagus", "hint": "Greek 'asparagos' from Persian 'asparag' (sprout); folk-etymologized to 'sparrow grass' in English"},
        {"name": "sorrel", "hint": "From Old French 'surele' (sour); used in borscht, schav, and French potage"},
        {"name": "nettle", "hint": "Old English 'netele'; stings you, feeds you, makes linen. Used in beer before hops."},
        {"name": "green garlic", "hint": "Young garlic pulled before it forms cloves; milder, ephemeral, spring-only"},
        {"name": "pea shoot", "hint": "Chinese 'dou miao' (豆苗); the tendrils of the common pea"},
    ],
    "summer": [  # Jun-Aug
        {"name": "shiso", "hint": "Japanese 'shiso' (紫蘇) meaning 'purple revive'; used in umeboshi, sashimi, cocktails"},
        {"name": "purslane", "hint": "Latin 'portulaca'; the most common 'weed' in the world is also the most nutritious green"},
        {"name": "padron pepper", "hint": "From Padrón, Galicia; 'unos pican y otros no' (some are hot and some are not)"},
        {"name": "gooseberry", "hint": "Nothing to do with geese. Possibly from French 'groseille' or Dutch 'kruisbes'"},
        {"name": "lemon verbena", "hint": "South American native called 'cedrón'; arrived in Europe in the 18th century"},
        {"name": "summer savory", "hint": "Latin 'satureia', associated with satyrs; the Romans' pepper substitute"},
        {"name": "husk cherry / ground cherry", "hint": "Physalis: Greek 'physa' (bladder), for its papery husk. Not a cherry."},
        {"name": "Thai basil", "hint": "Greek 'basilikon' (royal); the Thai cultivar has anise notes and stays firm when cooked"},
    ],
    "autumn": [  # Sep-Nov
        {"name": "quince", "hint": "Greek 'kydonion melon' (apple of Kydonia, Crete); the original 'apple' of many myths"},
        {"name": "persimmon", "hint": "Algonquian 'pessemmin' (dried fruit); the Hachiya must be soft as jelly, the Fuyu can be eaten firm"},
        {"name": "saffron", "hint": "Arabic 'za'farān' (yellow); 75,000 flowers for one pound; most labor-intensive spice on Earth"},
        {"name": "medlar", "hint": "Must be 'bletted' (rotted) before eating; Chaucer and Shakespeare used it as a bawdy metaphor"},
        {"name": "crab apple", "hint": "Old Norse 'skrab-' → 'scrab' → 'crab'; the ancestor of all cultivated apples"},
        {"name": "maitake", "hint": "Japanese 'dancing mushroom' (舞茸); said to make foragers dance with joy upon finding one"},
        {"name": "feijoa", "hint": "Named for João da Silva Feijó, Portuguese naturalist; also called pineapple guava"},
        {"name": "black walnut", "hint": "Old English 'wealh-hnutu' (foreign nut); 'wealh' = foreigner, same root as 'Wales' and 'walnut'"},
    ],
}

def current_season():
    month = datetime.now().month
    if month in (12, 1, 2): return "winter"
    if month in (3, 4, 5): return "spring"
    if month in (6, 7, 8): return "summer"
    return "autumn"

def generate():
    name = f"{today()}-recipe"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    season = current_season()
    ingredient = random.choice(INGREDIENTS[season])

    prompt = f"""Create a simple, satisfying recipe card featuring {ingredient['name']} as a key ingredient.

Season: {season}
Etymology hint: {ingredient['hint']}

Format your response in two parts:

PART 1 - THE RECIPE:
A recipe title, then 2-3 sentences describing the dish (not full instructions — 
more like a compelling description that makes someone want to cook it). 
Include rough quantities for 2 people. Keep it achievable for a grad student 
with basic kitchen skills and limited time.

PART 2 - THE WORD:
The etymological story of "{ingredient['name']}" in 2-3 sentences. 
Where does the word come from? What linguistic journey did it take? 
What does the etymology reveal about the ingredient's history?

Separate the two parts with [ETYMOLOGY]. Use HTML tags (<em>, <strong>) not markdown."""

    system = "You are a home cook and amateur etymologist. Your recipes are unfussy but interesting — the kind of food a curious person makes on a Wednesday night. Your etymology is precise and surprising."

    result = ask_claude(prompt, system=system, max_tokens=500, temperature=0.85)

    # Split on the marker
    parts = result.split('[ETYMOLOGY]')
    recipe_text = parts[0].strip() if len(parts) > 0 else result
    etymology = parts[1].strip() if len(parts) > 1 else ''

    write_feed(name, {
        "type": "recipe",
        "timestamp": f"{today()}T17:00:00",
        "ingredient": ingredient['name'],
        "season": season,
        "recipe": recipe_text,
        "etymology": etymology,
    })

if __name__ == '__main__':
    generate()
