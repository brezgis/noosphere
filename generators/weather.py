#!/usr/bin/env python3
"""Lyrical Weather. The forecast for the Boston area, in the forecasters' own words.

Everything on the card comes from the National Weather Service (api.weather.gov):
the gridpoint forecast for today and tonight, and the "key messages" that the
Boston/Norton office writes at the top of its Area Forecast Discussion. Sunrise
and sunset are computed locally. No model writes any of it.
"""
import math, re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from utils import today, today_date, write_feed, feed_exists, get_json

# A downtown Boston grid point. The feed is public, so the card stays at
# metro-area resolution on purpose.
LAT, LON = 42.36, -71.06
OFFICE = 'BOX'
TZ = ZoneInfo('America/New_York')
NWS = {'Accept': 'application/geo+json'}


def sun_times(d, lat=LAT, lon=LON):
    """(sunrise, sunset) as local datetimes, from the NOAA sunrise equation."""
    n = d.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    la = math.radians(lat)
    ha = math.degrees(math.acos(
        math.cos(math.radians(90.833)) / (math.cos(la) * math.cos(decl))
        - math.tan(la) * math.tan(decl)))
    base = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    rise = base + timedelta(minutes=720 - 4 * (lon + ha) - eqtime)
    sett = base + timedelta(minutes=720 - 4 * (lon - ha) - eqtime)
    return rise.astimezone(TZ), sett.astimezone(TZ)


def clock(dt):
    return dt.strftime('%-I:%M %p').lower()


def key_messages():
    """The bulleted key messages from the latest Area Forecast Discussion."""
    try:
        latest = get_json(f'https://api.weather.gov/products/types/AFD/locations/{OFFICE}',
                          headers=NWS)['@graph'][0]
        text = get_json(f"https://api.weather.gov/products/{latest['id']}",
                        headers=NWS)['productText']
    except Exception as e:
        print(f"  forecast discussion unavailable: {e}")
        return [], ''
    m = re.search(r'\.KEY MESSAGES\.\.\.(.*?)&&', text, re.S)
    if not m:
        return [], ''
    items = []
    for chunk in re.split(r'\n\s*-\s+', '\n' + m.group(1).strip()):
        line = ' '.join(chunk.split())
        # The office writes "..." where a sentence would take a comma.
        line = re.sub(r'\s*\.\.\.\s*', ', ', line).strip(' ,')
        if len(line) > 12:
            items.append(line)
    return items[:4], latest.get('issuanceTime', '')


def generate():
    name = f"{today()}-weather"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    point = get_json(f'https://api.weather.gov/points/{LAT},{LON}', headers=NWS)['properties']
    periods = get_json(point['forecast'], headers=NWS)['properties']['periods']
    if not periods:
        print("No forecast periods returned")
        return

    forecast = [{
        'name': p['name'],
        'short': p['shortForecast'],
        'text': p['detailedForecast'],
        'temp_f': p['temperature'],
        'daytime': bool(p['isDaytime']),
    } for p in periods[:3]]

    day = next((p for p in forecast if p['daytime']), forecast[0])
    night = next((p for p in forecast if not p['daytime']), None)
    messages, issued = key_messages()
    rise, sett = sun_times(today_date())
    light = sett - rise

    write_feed(name, {
        "type": "weather",
        "v": 2,
        "timestamp": f"{today()}T06:50:00",
        "place": "Boston area",
        "summary": day['short'],
        "high_f": day['temp_f'],
        "low_f": night['temp_f'] if night else None,
        "forecast": forecast,
        "key_messages": messages,
        "discussion_issued": issued,
        "sunrise": clock(rise),
        "sunset": clock(sett),
        "daylight": f"{light.seconds // 3600} h {light.seconds % 3600 // 60} min",
        "source": "National Weather Service, Boston/Norton",
        "source_url": "https://forecast.weather.gov/MapClick.php?lat=42.36&lon=-71.06",
        "discussion_url": "https://forecast.weather.gov/product.php?site=BOX&issuedby=BOX&product=AFD",
    })


if __name__ == '__main__':
    generate()
