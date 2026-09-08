import requests, ssl, re
from ics import Calendar
from datetime import datetime, timedelta
from collections import defaultdict
import pytz
import random

# --- ICS Feed ---
ical_url = "https://calendar.google.com/calendar/ical/6bl9ubrc8vssoqi0jm1l7ljpc05ngqrt%40import.calendar.google.com/public/basic.ics"

local_tz = pytz.timezone("America/New_York")
today = datetime.now(local_tz).date()

# --- Travel Towns (second filter) ---
travel_towns = {
    "Stoughton", "Sharon", "Raynham", "Bridgewater", "Mansfield",
    "Canton", "Foxboro", "Easton", "Taunton", "Whitman", "Abington",
    "Quincy"
}

# --- Field Map Coordinates ---
field_positions = {
    # Field 1 (bare) → same as Field 1A
    "Field 1":  { "x": 40.0, "y": 24.2, "width": 17.0, "height": 13.0 },

    # Field 1A / 1B
    "Field 1A": { "x": 40.0, "y": 24.2, "width": 17.0, "height": 13.0 },
    "Field 1B": { "x": 40.0, "y": 15.7, "width": 17.0, "height": 13.0 },

    # Field 2 (bare) → same as Field 2A
    "Field 2":  { "x": 60.0, "y": 24.2, "width": 17.0, "height": 13.0 },

    # Field 2A / 2B
    "Field 2A": { "x": 60.0, "y": 24.2, "width": 17.0, "height": 13.0 },
    "Field 2B": { "x": 60.0, "y": 15.7, "width": 17.0, "height": 13.0 },

    # Field 3 (bare)
    "Field 3":  { "x": 15, "y": 75.5, "width": 14.5, "height": 19, "rotate": 7.5 },

    # Field 4 (bare) → same as Field 4A
    "Field 4":  { "x": 36.5, "y": 68, "width": 20, "height": 10.5, "rotate": 4.9 },

    # Field 4A / 4B
    "Field 4A": { "x": 36.5, "y": 68, "width": 20, "height": 10.5, "rotate": 4.9 },
    "Field 4B": { "x": 55.5, "y": 69, "width": 20, "height": 10.5, "rotate": 4.9 },
}


# --- Helpers ---
def parse_team(raw_team):
    raw_team = raw_team.strip()

    match = re.match(r"^(.*?)\s*\(([^()-]+)-([^()]+)\)$", raw_team)
    if match:
        team_name = match.group(1).strip()
        coach = match.group(2).strip()
        color = match.group(3).strip()
        return f"{team_name} ({coach})", color

    match = re.match(r"^(.*?)\s*\(([^()]+)\)$", raw_team)
    if match:
        team_name = match.group(1).strip()
        coach = match.group(2).strip()
        return f"{team_name} ({coach})", "Gray"

    return raw_team, "Gray"


def extract_division(description):
    if not description:
        return ""
    match = re.search(r"(\d+(?:/\d+)*\s+(Boys|Girls)(?:\s+Travel)?)", description)
    if match:
        return match.group(1)
    if "Kindergarten" in description:
        return "Kindergarten"
    return ""


def format_field(raw_field):
    if "H-SuSS" in raw_field:
        return "Snack Shack Area"

    core = raw_field.split(",", 1)[0].strip()

    # Direct A/B fields
    match = re.match(r"H-Su(\d)([A-Z])$", core)
    if match:
        num = match.group(1)
        suffix = match.group(2)
        return f"Field {num}{suffix}"

    match = re.match(r"H-SJ(\d)([A-Z])$", core)
    if match:
        num = match.group(1)
        suffix = match.group(2)
        return f"Field {num}{suffix}"

    # Bare fields → return Field 1, Field 2, etc.
    match = re.match(r"H-Su(\d)$", core)
    if match:
        num = match.group(1)
        return f"Field {num}"

    match = re.match(r"H-SJ(\d)$", core)
    if match:
        num = match.group(1)
        return f"Field {num}"

    return raw_field



def time_sort_key(t):
    return datetime.strptime(t, "%I:%M %p")

# --- Auto Color Detection ---
def build_color_map(future_games):
    known_colors = {
        "Blue": "#4996D1", "Red": "#E88989", "Green": "#429964",
        "Orange": "#FCB03A", "Berry": "#E8DAEF", "Gray": "#F2F3F4",
        "Black": "#000000", "White": "#FFFFFF", "Yellow": "#FFEB3B",
        "Purple": "#9B59B6", "Maroon": "#800000", "Teal": "#008080",
        "Pink": "#FFC0CB", "Gold": "#FFD700", "Silver": "#C0C0C0",
        "Navy": "#001F3F", "Royal Blue": "#4169E1",
        "Light Blue": "#ADD8E6", "Dark Green": "#006400",
    }

    auto_map = {}
    for date, games in future_games.items():
        for g in games:
            for c in (g["color1"], g["color2"]):
                if c not in auto_map:
                    auto_map[c] = known_colors.get(
                        c, "#{:06x}".format(random.randint(0x444444, 0xDDDDDD))
                    )
    return auto_map

# --- Load ICS ---
ssl._create_default_https_context = ssl._create_unverified_context
ics_text = requests.get(ical_url).text
calendar = Calendar(ics_text)

# --- Extract REC games only ---
future_games = defaultdict(list)

for event in calendar.events:
    local_start = event.begin.datetime.astimezone(local_tz)
    game_date = local_start.date()
    if game_date < today:
        continue

    name = event.name
    location = event.location or ""
    description = event.description or ""

    if "Practice" in name or "vs." not in name:
        continue

    team1_raw, team2_raw = name.split("vs.")
    team1_raw = team1_raw.strip()
    team2_raw = team2_raw.strip()

    if "Travel" in team1_raw or "Travel" in team2_raw:
        continue

    if team1_raw in travel_towns or team2_raw in travel_towns:
        continue

    division = extract_division(description)

    if "Travel" in division:
        continue

    time_label = local_start.strftime("%I:%M %p").lstrip("0")
    team1, color1 = parse_team(team1_raw)
    team2, color2 = parse_team(team2_raw)
    field = format_field(location)

    future_games[game_date].append({
        "time": time_label,
        "field": field,
        "team1": team1,
        "color1": color1,
        "team2": team2,
        "color2": color2,
        "division": division
    })

# --- Auto Color Map ---
color_map = build_color_map(future_games)

# --- Determine next REC Saturday ---
next_saturday = today + timedelta((5 - today.weekday()) % 7)
games_this_sat = future_games.get(next_saturday, [])

# --- Determine next REC game day ---
next_game_date = next((d for d in sorted(future_games) if future_games[d]), None)

# --- HTML Output ---
output_html = "map_overlay_enhanced.html"
image_path = "assets/field_map.jpeg"

with open(output_html, "w", encoding="utf8") as f:
    f.write("<html><head><style>\n")
    f.write("""
        body { font-family: sans-serif; background: #fff; padding: 20px; }
        .map-grid { display: flex; flex-wrap: wrap; gap: 20px; }
        .map-column { flex: 1; min-width: 300px; text-align: center; }
        .map-container { position: relative; width: 100%; max-width: 400px; margin: auto; }
        .field-map { width: 100%; display: block; }
        .match-overlay { position: absolute; font-size: 0.65em; background: white; border: 0.5px solid black;
            text-align: center; padding: 4px 2px; box-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
        .team-left, .team-right { font-weight: bold; padding: 6px 2px; color: #000; }
        .division-label { font-size: 0.75em; font-weight: bold; margin-top: 2px; }
    """)
    f.write("</style></head><body>\n")

    if not games_this_sat:
        f.write(f"<p style='color:#666;font-style:italic;font-size:0.85em;'>No REC games scheduled for Saturday, {next_saturday.strftime('%B %d')}</p>")

    if not next_game_date:
        f.write("<h1>No upcoming REC games found.</h1></body></html>")
        exit(0)

    f.write(f"<h1>Next REC game day: {next_game_date.strftime('%A, %B %d')}</h1>\n")

    games = future_games[next_game_date]
    games_by_block = defaultdict(list)
    for g in games:
        games_by_block[g["time"]].append(g)

    f.write("<div class='map-grid'>\n")

    for block in sorted(games_by_block.keys(), key=time_sort_key):
        f.write(f"<div class='map-column'><h2>{block}</h2>\n")
        f.write(f"<div class='map-container'><img src='{image_path}' class='field-map'>\n")

        for g in games_by_block[block]:
            pos = field_positions.get(g["field"])
            if not pos:
                continue

            left = f"{pos['x']}%"
            top = f"{pos['y']}%"
            width = f"{pos['width']}%"
            height = f"{pos['height']}%"
            rotation = pos.get("rotate", 0)
            transform = f"rotate({rotation}deg)" if rotation else "none"

            f.write(
                f"<div class='match-overlay' "
                f"style='left:{left};top:{top};width:{width};height:{height};transform:{transform};'>"
            )
            f.write(
                f"<div class='team-left' style='background-color:{color_map[g['color1']]}'>{g['team1']}</div>"
            )
            f.write(
                f"<div class='team-right' style='background-color:{color_map[g['color2']]}'>{g['team2']}</div>"
            )
            f.write(f"<div class='division-label'>{g['division']}</div>")
            f.write("</div>")

        f.write("</div></div>\n")

    f.write("</div></body></html>")

print(f"Overlay saved to: {output_html}")
