import requests, ssl, re
from ics import Calendar
from datetime import datetime
from collections import defaultdict
import pytz

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
DEFAULT_COLOR_1 = "#0080ff" # Blue
DEFAULT_COLOR_2 = "#ee820d" # Orange

# --- FIELD POSITIONS (PERCENT-BASED, derived from pixels) ---
# Image size: 1113 x 1590

field_positions = {

    # -----------------------------
    # FIELD 1 (full field → top/bottom)
    # -----------------------------
    "Field 1_top": {
        "x": 38.7, "y": 15.2,
        "width": 14.8, "height": 8.9,
        "rotate": 0
    },
    "Field 1_bottom": {
        "x": 38.7, "y": 24.1,
        "width": 14.8, "height": 8.9,
        "rotate": 0
    },

    # -----------------------------
    # FIELD 1A (full diamond)
    # -----------------------------
    "Field 1A": {
        "x": 33.6, "y": 24.7,
        "width": 20.0, "height": 11.8,
        "rotate": 0
    },

    # -----------------------------
    # FIELD 2 (full field → top/bottom)
    # -----------------------------
    "Field 2_top": {
        "x": 57.3, "y": 15.2,
        "width": 14.6, "height": 8.9,
        "rotate": 0
    },
    "Field 2_bottom": {
        "x": 57.3, "y": 24.2,
        "width": 14.6, "height": 8.9,
        "rotate": 0
    },

    # -----------------------------
    # FIELD 3 (rotated → top/bottom)
    # -----------------------------
    "Field 3_top": {
        "x": 16.8, "y": 71.2,
        "width": 14.4, "height": 9.2,
        "rotate": 4
    },
    "Field 3_bottom": {
        "x": 15.3, "y": 80.4,
        "width": 14.5, "height": 8.6,
        "rotate": 3
    },

    # -----------------------------
    # FIELD 4 (rotated → top/bottom)
    # -----------------------------
    "Field 4_top": {
        "x": 37.4, "y": 68.5,
        "width": 12.6, "height": 10.1,
        "rotate": 4.6
    },
    "Field 4_bottom": {
        "x": 49.2, "y": 68.5,
        "width": 13.3, "height": 10.1,
        "rotate": 4.6
    },

    # -----------------------------
    # PLACEHOLDERS (unused)
    # -----------------------------
    "Field 1B": None,
    "Field 2A": None,
    "Field 2B": None,
    "Field 4A": None,
    "Field 4B": None
}

# --- Helpers ---
def parse_team(raw_team):
    raw_team = raw_team.strip()
    match = re.match(r"^(.*?)\s*\(([^()-]+)-([^()]+)\)$", raw_team)
    if match:
        return f"{match.group(1).strip()} ({match.group(2).strip()})", match.group(3).strip()
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

    # Sumner Fields (H-Su)
    match = re.match(r"H-Su(\d)([A-Z])$", core)
    if match:
        return f"Field {match.group(1)}{match.group(2)}"
    match = re.match(r"H-Su(\d)$", core)
    if match:
        return f"Field {match.group(1)}"

    # Sean Joyce Fields (H-SJ)
    match = re.match(r"H-SJ(\d)([A-Z])$", core)
    if match:
        return f"Field {match.group(1)}{match.group(2)}"
    match = re.match(r"H-SJ(\d)$", core)
    if match:
        return f"Field {match.group(1)}"

    return raw_field


def get_positions_for_field(field_name):
    mapping = {
        "Field 1": ["Field 1_top", "Field 1_bottom"],
        "Field 1A": ["Field 1A"],
        "Field 2": ["Field 2_top", "Field 2_bottom"],
        "Field 3": ["Field 3_top", "Field 3_bottom"],
        "Field 4": ["Field 4_top", "Field 4_bottom"]
    }
    return mapping.get(field_name, [])

def build_color_map(future_games):
    known_colors = {
        "Blue": "#4996D1", "Red": "#dc4949", "Green": "#429964",
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
                    auto_map[c] = known_colors.get(c, DEFAULT_COLOR_1 if c != "Gray" else "#F2F3F4")
    return auto_map

# --- Load ICS ---
ssl._create_default_https_context = ssl._create_unverified_context
ics_text = requests.get(ical_url).text
calendar = Calendar(ics_text)

# --- Extract REC games ---
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

color_map = build_color_map(future_games)
next_game_date = next((d for d in sorted(future_games) if future_games[d]), None)

# --- HTML Output ---
output_html = "map_overlay_enhanced.html"
image_path = "assets/field_map.jpeg"

with open(output_html, "w", encoding="utf8") as f:
    f.write("<html><head><style>\n")
    f.write("""
        body { font-family: sans-serif; background: #fff; padding: 20px; }
    
        /* Three maps side-by-side */
        .map-grid { 
            display: flex;
            flex-direction: row;
            justify-content: center;
            gap: 20px;                 /* spacing between maps */
            flex-wrap: nowrap;
        }
    
        .map-column { 
            width: 33%;                /* each column gets 1/3 of the row */
            text-align: center;
        }
    
        /* Scaled map container */
        .map-container {
            position: relative;
            width: 100%;               /* scale with column */
            aspect-ratio: 1113 / 1590; /* preserve proportions */
            margin: 0 auto;
        }
    
        .field-map {
            width: 100%;               /* scaled image */
            height: auto;
            display: block;
        }
    
        .match-overlay {
            position: absolute;
            font-size: 0.65em;
            background: white;
            border: 0.5px solid black;
            text-align: center;
            padding: 4px 2px;
            box-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            transform-origin: top left;
        }
    
        .team-left, .team-right { 
            font-weight: bold; 
            padding: 6px 2px; 
            color: #000; 
        }
    
        .division-label { 
            font-size: 0.75em; 
            font-weight: bold; 
            margin-top: 2px; 
        }
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

            for idx, pos_key in enumerate(positions):
                pos = field_positions.get(pos_key)
                if not pos:
                    continue

                f.write(
                    f"<div class='match-overlay' style='"
                    f"left:{pos['x']}%; top:{pos['y']}%; "
                    f"width:{pos['width']}%; height:{pos['height']}%; "
                    f"transform:rotate({pos.get('rotate',0)}deg);'>"
                )

                if idx == 0:
                    f.write(f"<div class='team-left' style='background-color:{color_map[g['color1']]}'>{g['team1']}</div>")
                else:
                    f.write(f"<div class='team-right' style='background-color:{color_map[g['color2']]}'>{g['team2']}</div>")

                f.write(f"<div class='division-label'>{g['division']}</div>")
                f.write("</div>")

        f.write("</div></div>\n")

    f.write("</div></body></html>")

print(f"Overlay saved to: {output_html}")
