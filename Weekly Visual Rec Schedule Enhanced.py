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

# --- Travel Towns ---
travel_towns = {
    "Stoughton", "Sharon", "Raynham", "Bridgewater", "Mansfield",
    "Canton", "Foxboro", "Easton", "Taunton", "Whitman", "Abington",
    "Quincy"
}

# --- Fallback Colors ---
DEFAULT_COLOR_1 = "#D0D8E8"   # soft blue-gray
DEFAULT_COLOR_2 = "#E8D0D0"   # soft red-gray

# --- Field Map Coordinates ---
field_positions = {
    # -----------------------------
    # FIELD 1 (full field → top/bottom)
    # -----------------------------
    "Field 1_top":    { "x": 40.0, "y": 15.7, "width": 17.0, "height": 10.8 },
    "Field 1_bottom": { "x": 40.0, "y": 26.5, "width": 17.0, "height": 10.8 },

    # FIELD 1A → left/right
    "Field 1A_left":  { "x": 40.0, "y": 24.2, "width": 8.5, "height": 13.0 },
    "Field 1A_right": { "x": 48.5, "y": 24.2, "width": 8.5, "height": 13.0 },

    # FIELD 1B → left/right
    "Field 1B_left":  { "x": 40.0, "y": 15.7, "width": 8.5, "height": 13.0 },
    "Field 1B_right": { "x": 48.5, "y": 15.7, "width": 8.5, "height": 13.0 },


    # -----------------------------
    # FIELD 2 (full field → top/bottom)
    # -----------------------------
    "Field 2_top":    { "x": 60.0, "y": 15.7, "width": 17.0, "height": 10.8 },
    "Field 2_bottom": { "x": 60.0, "y": 26.5, "width": 17.0, "height": 10.8 },

    # FIELD 2A → left/right
    "Field 2A_left":  { "x": 60.0, "y": 24.2, "width": 8.5, "height": 13.0 },
    "Field 2A_right": { "x": 68.5, "y": 24.2, "width": 8.5, "height": 13.0 },

    # FIELD 2B → left/right
    "Field 2B_left":  { "x": 60.0, "y": 15.7, "width": 8.5, "height": 13.0 },
    "Field 2B_right": { "x": 68.5, "y": 15.7, "width": 8.5, "height": 13.0 },


    # -----------------------------
    # FIELD 3 (unchanged)
    # -----------------------------
    "Field 3":  { "x": 15, "y": 75.5, "width": 14.5, "height": 19, "rotate": 7.5 },


    # -----------------------------
    # FIELD 4 (left/right)
    # -----------------------------
    "Field 4_left":  { "x": 36.5, "y": 63, "width": 10.0, "height": 10.5, "rotate": 4.9 },
    "Field 4_right": { "x": 46.5, "y": 63, "width": 10.0, "height": 10.5, "rotate": 4.9 },

    # FIELD 4A → top/bottom
    "Field 4A_top":    { "x": 36.5, "y": 63,   "width": 20.0, "height": 5.0, "rotate": 4.9 },
    "Field 4A_bottom": { "x": 36.5, "y": 68.2, "width": 20.0, "height": 5.0, "rotate": 4.9 },

    # FIELD 4B → left/right
    "Field 4B_left":  { "x": 55.5, "y": 63, "width": 10.0, "height": 10.5, "rotate": 4.9 },
    "Field 4B_right": { "x": 65.5, "y": 63, "width": 10.0, "height": 10.5, "rotate": 4.9 },
}


# --- Helpers ---
def parse_team(raw_team):
    raw_team = raw_team.strip()

    # Format: Team Name (Coach - Color)
    match = re.match(r"^(.*?)\s*\(([^()-]+)-([^()]+)\)$", raw_team)
    if match:
        return f"{match.group(1).strip()} ({match.group(2).strip()})", match.group(3).strip()

    # Format: Team Name (Color)
    match = re.match(r"^(.*?)\s*\(([^()]+)\)$", raw_team)
    if match:
        return match.group(1).strip(), match.group(2).strip()

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
    core = raw_field.split(",", 1)[0].strip()

    # Direct A/B fields
    match = re.match(r"H-Su(\d)([A-Z])$", core)
    if match:
        return f"Field {match.group(1)}{match.group(2)}"

    match = re.match(r"H-SJ(\d)([A-Z])$", core)
    if match:
        return f"Field {match.group(1)}{match.group(2)}"

    # Bare fields
    match = re.match(r"H-Su(\d)$", core)
    if match:
        return f"Field {match.group(1)}"

    match = re.match(r"H-SJ(\d)$", core)
    if match:
        return f"Field {match.group(1)}"

    return raw_field


def get_positions_for_field(field_name):
    if field_name == "Field 1":
        return ["Field 1_top", "Field 1_bottom"]
    if field_name == "Field 1A":
        return ["Field 1A_left", "Field 1A_right"]
    if field_name == "Field 1B":
        return ["Field 1B_left", "Field 1B_right"]

    if field_name == "Field 2":
        return ["Field 2_top", "Field 2_bottom"]
    if field_name == "Field 2A":
        return ["Field 2A_left", "Field 2A_right"]
    if field_name == "Field 2B":
        return ["Field 2B_left", "Field 2B_right"]

    if field_name == "Field 4":
        return ["Field 4_left", "Field 4_right"]
    if field_name == "Field 4A":
        return ["Field 4A_top", "Field 4A_bottom"]
    if field_name == "Field 4B":
        return ["Field 4B_left", "Field 4B_right"]

    if field_name == "Field 3":
        return ["Field 3"]

    return []


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
            c1 = g["color1"]
            c2 = g["color2"]

            if c1 not in auto_map:
                if c1 in known_colors:
                    auto_map[c1] = known_colors[c1]
                elif c1 == "Gray":
                    auto_map[c1] = "#F2F3F4"
                else:
                    auto_map[c1] = DEFAULT_COLOR_1

            if c2 not in auto_map:
                if c2 in known_colors:
                    auto_map[c2] = known_colors[c2]
                elif c2 == "Gray":
                    auto_map[c2] = "#F2F3F4"
                else:
                    auto_map[c2] = DEFAULT_COLOR_2

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

    if not next_game_date:
        f.write("<h1>No upcoming REC games found.</h1></body></html>")
        exit(0)

    f.write(f"<h1>Next REC game day: {next_game_date.strftime('%A, %B %d')}</h1>\n")

    games = future_games[next_game_date]
    games_by_block = defaultdict(list)
    for g in games:
        games_by_block[g["time"]].append(g)

    f.write("<div class='map-grid'>\n")

    for block in sorted(games_by_block.keys(), key=lambda t: datetime.strptime(t, "%I:%M %p")):
        f.write(f"<div class='map-column'><h2>{block}</h2>\n")
        f.write(f"<div class='map-container'><img src='{image_path}' class='field-map'>\n")

        for g in games_by_block[block]:
            positions = get_positions_for_field(g["field"])
            if not positions:
                continue

            # Team 1 box
            pos1 = field_positions[positions[0]]
            f.write(
                f"<div class='match-overlay' style='left:{pos1['x']}%;top:{pos1['y']}%;"
                f"width:{pos1['width']}%;height:{pos1['height']}%;"
                f"transform:rotate({pos1.get('rotate',0)}deg);'>"
            )
            f.write(f"<div class='team-left' style='background-color:{color_map[g['color1']]}'>{g['team1']}</div>")
            f.write(f"<div class='division-label'>{g['division']}</div>")
            f.write("</div>")

            # Team 2 box (if exists)
            if len(positions) > 1:
                pos2 = field_positions[positions[1]]
                f.write(
                    f"<div class='match-overlay' style='left:{pos2['x']}%;top:{pos2['y']}%;"
                    f"width:{pos2['width']}%;height:{pos2['height']}%;"
                    f"transform:rotate({pos2.get('rotate',0)}deg);'>"
                )
                f.write(f"<div class='team-right' style='background-color:{color_map[g['color2']]}'>{g['team2']}</div>")
                f.write(f"<div class='division-label'>{g['division']}</div>")
                f.write("</div>")

        f.write("</div></div>\n")

    f.write("</div></body></html>")

print(f"Overlay saved to: {output_html}")
