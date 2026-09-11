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
        "x": 40, "y": 16,
        "width": 12, "height": 8,
        "rotate": 0
    },
    "Field 1_bottom": {
        "x": 40, "y": 25,
        "width": 12, "height": 8,
        "rotate": 0
    },

    # -----------------------------
    # FIELD 1A (bottom-left diamond)
    # -----------------------------
    "Field 1A_left": {
        "x": 35, "y": 25,
        "width": 10, "height": 6,
        "rotate": 0
    },
    "Field 1A_right": {
        "x": 45, "y": 25,
        "width": 10, "height": 6,
        "rotate": 0
    },

    # -----------------------------
    # FIELD 1B (top-left diamond)
    # -----------------------------
    "Field 1B_left": {
        "x": 35, "y": 16,
        "width": 10, "height": 6,
        "rotate": 0
    },
    "Field 1B_right": {
        "x": 45, "y": 16,
        "width": 10, "height": 6,
        "rotate": 0
    },

    # -----------------------------
    # FIELD 2 (full field → top/bottom)
    # -----------------------------
    "Field 2_top": {
        "x": 63, "y": 16,
        "width": 10, "height": 9,
        "rotate": 0
    },
    "Field 2_bottom": {
        "x": 63, "y": 25,
        "width": 10, "height": 9,
        "rotate": 0
    },

    # -----------------------------
    # FIELD 2A (bottom-right diamond)
    # -----------------------------
    "Field 2A_left": {
        "x": 58, "y": 25,
        "width": 10, "height": 6,
        "rotate": 0
    },
    "Field 2A_right": {
        "x": 68, "y": 25,
        "width": 10, "height": 6,
        "rotate": 0
    },

    # -----------------------------
    # FIELD 2B (top-right diamond)
    # -----------------------------
    "Field 2B_left": {
        "x": 58, "y": 16,
        "width": 10, "height": 6,
        "rotate": 0
    },
    "Field 2B_right": {
        "x": 68, "y": 16,
        "width": 10, "height": 6,
        "rotate": 0
    },

    # -----------------------------
    # FIELD 3 (rotated → top/bottom)
    # -----------------------------
    "Field 3_top": {
        "x": 17, "y": 74,
        "width": 16, "height": 10,
        "rotate": 7
    },
    "Field 3_bottom": {
        "x": 15, "y": 85,
        "width": 16, "height": 10,
        "rotate": 6
    },

    # -----------------------------
    # FIELD 4 (rotated → top/bottom)
    # -----------------------------
    "Field 4_top": {
        "x": 36, "y": 68,
        "width": 14, "height": 7,
        "rotate": 5
    },
    "Field 4_bottom": {
        "x": 55, "y": 68,
        "width": 14, "height": 7,
        "rotate": 5
    },

    # -----------------------------
    # FIELD 4A / 4B (diamonds on Field 4)
    # -----------------------------

    # 4B = top diamond
    "Field 4B_left": {     # Left field top
        "x": 36, "y": 65,
        "width": 13, "height": 4,
        "rotate": 5
    },
    "Field 4B_right": {     # Right field top
        "x": 51, "y": 65,
        "width": 13, "height": 4,
        "rotate": 5
    },

    # 4A = bottom diamond
    "Field 4A_left": {      # Left field bottom
        "x": 36, "y": 72,
        "width": 13, "height": 4,
        "rotate": 5
    },
    "Field 4A_right": {     # Right field bottom
        "x": 51, "y": 74,
        "width": 13, "height": 4,
        "rotate": 5
    },
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

    # Standard divisions: "3/4 Boys", "5/6 Girls", "7/8 Boys Travel"
    match = re.search(r"(\d+(?:/\d+)*\s+(Boys|Girls)(?:\s+Travel)?)", description)
    if match:
        return match.group(1)

    # Kindergarten variants
    if any(k in description for k in [
        "Kindergarten", "Kinder", "K Grade", "PreK/K", "KG"
    ]):
        return "Kindergarten"

    return ""



def get_positions_for_field(field_name):
    mapping = {
        "Field 1": ["Field 1_top", "Field 1_bottom"],
        "Field 2": ["Field 2_top", "Field 2_bottom"],
        "Field 3": ["Field 3_top", "Field 3_bottom"],
        "Field 4": ["Field 4_top", "Field 4_bottom"],

        "Field 1A": ["Field 1A_left", "Field 1A_right"],
        "Field 1B": ["Field 1B_left", "Field 1B_right"],
        "Field 2A": ["Field 2A_left", "Field 2A_right"],
        "Field 2B": ["Field 2B_left", "Field 2B_right"],
        "Field 4A": ["Field 4A_left", "Field 4A_right"],
        "Field 4B": ["Field 4B_left", "Field 4B_right"],
    }

    return mapping.get(field_name, [])





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
                    if c == "Gray":
                        # Match basic view behavior: use DEFAULT_COLOR_1
                        auto_map[c] = DEFAULT_COLOR_1
                    elif c in known_colors:
                        auto_map[c] = known_colors[c]
                    else:
                        auto_map[c] = DEFAULT_COLOR_1

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

    # Skip practices only
    if "Practice" in name:
        continue

    # Allow Kindergarten, Kickers, 1/2 divisions even without "vs."
    if "vs." not in name and not any(key in name for key in [
        "Kindergarten", "Kickers", "1/2", "3/4", "5/6", "7/8"
    ]):
        continue


    # Split teams if "vs." exists
    if "vs." in name:
        team1_raw, team2_raw = name.split("vs.")
        team1_raw = team1_raw.strip()
        team2_raw = team2_raw.strip()
    else:
        # Single-team formats (K, Kickers)
        team1_raw = name.strip()
        team2_raw = ""
    
    # Skip true travel teams ONLY if the entire name matches a travel town
    if team1_raw.strip() in travel_towns or team2_raw.strip() in travel_towns:
        continue

    # Skip travel divisions only
    division = extract_division(description)
    if "Travel" in division:
        continue

    time_label = local_start.strftime("%I:%M %p").lstrip("0")
    team1, color1 = parse_team(team1_raw)
    team2, color2 = parse_team(team2_raw) if team2_raw else ("", "Gray")
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
            color: #000;
            min-height: 22px;
            font-size: 0.75em;
            padding: 2px 4px;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            line-height: 1.1em;      /* allows wrapping */
            white-space: normal;     /* enables wrapping */
            overflow: hidden;        /* prevents overflow */
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

    f.write(f"<h1>Next Rec game day: {next_game_date.strftime('%A, %B %d')}</h1>\n")

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
