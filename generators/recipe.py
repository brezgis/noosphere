#!/usr/bin/env python3
"""Recipe. A real recipe each week, with the etymology of one of its ingredients.

The recipe comes from TheMealDB exactly as published: name, cuisine, the full
ingredient list with its measures, the method and the photo. The etymology is
the English Wiktionary entry for one ingredient. No model rewrites or scales
anything (the old version let the model "simplify for two" and it invented
quantities).
"""
import random, re, urllib.parse
from utils import today, write_feed, feed_exists, get_json, wiktionary_etymology, clip, SourceUnavailable

# Ingredients whose etymology is not worth a card.
PLAIN = {'water', 'salt', 'sugar', 'oil', 'butter', 'milk', 'egg', 'eggs',
         'flour', 'pepper', 'cream', 'stock', 'rice', 'bread'}


def fetch_recipe():
    meal = get_json("https://www.themealdb.com/api/json/v1/1/random.php")['meals'][0]
    ingredients = []
    for i in range(1, 21):
        ing = (meal.get(f'strIngredient{i}') or '').strip()
        measure = (meal.get(f'strMeasure{i}') or '').strip()
        if ing:
            ingredients.append({'item': ing, 'measure': measure})
    steps = [' '.join(s.split()) for s in re.split(r'[\r\n]+', meal.get('strInstructions') or '')]
    # Drop bare step labels such as "STEP 1" or "2." that some recipes carry.
    steps = [s for s in steps if s and not re.fullmatch(r'(step\s*)?\d+[.:)]?', s, re.I)]
    return {
        'name': meal['strMeal'].strip(),
        'category': meal.get('strCategory') or '',
        'area': meal.get('strArea') or '',
        'steps': steps,
        'ingredients': ingredients,
        'image': meal.get('strMealThumb') or '',
        'source': meal.get('strSource') or '',
        'youtube': meal.get('strYoutube') or '',
        'id': meal.get('idMeal') or '',
    }


def pick_word(ingredients):
    """An ingredient with a real etymology on Wiktionary: (word, text) or None."""
    words = []
    for ing in ingredients:
        name = ing['item'].lower().strip()
        # "Chopped tomatoes" -> "tomatoes". The head noun is usually last.
        head = name.split()[-1] if name else ''
        for w in (name, head, head.rstrip('s')):
            if w and w not in PLAIN and re.fullmatch(r"[a-zà-ÿ' -]+", w) and w not in words:
                words.append(w)
    random.shuffle(words)
    for w in words[:6]:
        try:
            text = wiktionary_etymology(w)
        except SourceUnavailable as e:
            print(f"  {e}")
            return None
        if len(text) >= 60:
            return w, text
    return None


def generate():
    name = f"{today()}-recipe"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    try:
        recipe = fetch_recipe()
    except Exception as e:
        print(f"Failed to fetch recipe: {e}")
        return

    card = {
        "type": "recipe",
        "v": 2,
        "timestamp": f"{today()}T17:00:00",
        "name": recipe['name'],
        "area": recipe['area'],
        "category": recipe['category'],
        "ingredients": recipe['ingredients'],
        "steps": recipe['steps'],
        "image": recipe['image'],
        "source_url": recipe['source'] or f"https://www.themealdb.com/meal/{recipe['id']}",
        "youtube": recipe['youtube'],
    }
    word = pick_word(recipe['ingredients'])
    if word:
        card["word"] = {
            "term": word[0],
            "etymology": clip(word[1], 480),
            "url": "https://en.wiktionary.org/wiki/" + urllib.parse.quote(word[0]) + "#English",
        }
    write_feed(name, card)


if __name__ == '__main__':
    generate()
