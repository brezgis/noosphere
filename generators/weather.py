#!/usr/bin/env python3
"""Lyrical Weather — poetic weather report for Cambridge/Alewife area."""
import requests, json
from utils import ask_claude, today, write_feed, feed_exists

def get_weather():
    """Fetch current weather from wttr.in."""
    resp = requests.get('https://wttr.in/Cambridge+MA?format=j1', timeout=10)
    resp.raise_for_status()
    data = resp.json()
    current = data['current_condition'][0]
    return {
        'temp_f': current['temp_F'],
        'feels_like_f': current['FeelsLikeF'],
        'desc': current['weatherDesc'][0]['value'],
        'humidity': current['humidity'],
        'wind_mph': current['windspeedMiles'],
        'wind_dir': current['winddir16Point'],
        'visibility': current['visibility'],
        'precip_mm': current['precipMM'],
        'cloud_cover': current['cloudcover'],
        'uv': current['uvIndex'],
    }

def generate():
    name = f"{today()}-weather"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    w = get_weather()
    
    prompt = f"""Write a lyrical weather report for Cambridge, Massachusetts this morning. 
The actual conditions: {w['temp_f']}°F (feels like {w['feels_like_f']}°F), {w['desc'].lower()}, 
humidity {w['humidity']}%, wind {w['wind_mph']} mph from the {w['wind_dir']}, 
cloud cover {w['cloud_cover']}%, UV index {w['uv']}.

Write 2-4 sentences in the style of a Virginia Woolf or Chekhov weather description — sensory, 
grounded in the physical landscape near Alewife/Cambridge. Mention the temperature naturally 
embedded in the prose using this exact HTML: <span class="temp">{w['temp_f']}°F</span>

No greeting, no sign-off, no "good morning." Just the weather as literature. 
Keep it under 80 words."""

    system = "You are a weather poet. Write evocative, sensory prose about weather. No pleasantries, no emoji, no advice about what to wear. Just the weather itself, rendered in beautiful language."

    content = ask_claude(prompt, system=system, max_tokens=300, temperature=0.9)
    
    write_feed(name, {
        "type": "weather",
        "timestamp": f"{today()}T06:50:00",
        "content": content,
    })

if __name__ == '__main__':
    generate()
