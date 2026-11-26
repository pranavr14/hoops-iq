"""Refresh NBA schedule and completed player box scores from ESPN's public feed.

The updater runs once a day in GitHub Actions. It stores the full current-season
schedule and appends completed player stat lines to the model's training data.
"""

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/player_game_logs_2025_27.csv"
SCHEDULE_PATH = ROOT / "data/nba_schedule.json"
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
SCOREBOARD_URL = f"{ESPN_BASE}/scoreboard"
SUMMARY_URL = f"{ESPN_BASE}/summary"
HEADERS = {"User-Agent": "HoopsIQ/1.0 (NBA stats research project)", "Accept": "application/json"}
EASTERN = ZoneInfo("America/New_York")
ESPN_TO_NBA = {"GS": "GSW", "SA": "SAS", "NY": "NYK", "NO": "NOP", "WSH": "WAS"}
CSV_COLUMNS = [
    "PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "GAME_ID",
    "GAME_DATE", "MATCHUP", "MIN", "PTS", "REB", "AST", "FG3M",
    "STL", "BLK", "TOV", "SEASON",
]


def get_json(url: str) -> dict:
    request = Request(url, headers=HEADERS)
    last_error = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=40) as response:
                if response.status != 200:
                    raise RuntimeError(f"ESPN returned HTTP {response.status} for {url}")
                return json.load(response)
        except (URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not fetch ESPN data after retries: {url}") from last_error


def parse_date(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def nba_code(value: str) -> str:
    code = value.upper()
    return ESPN_TO_NBA.get(code, code)


def _schedule_games(payload: dict) -> list[dict]:
    games = []
    for event in payload.get("events", []):
        competition = (event.get("competitions") or [{}])[0]
        competitors = competition.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home or not away:
            continue
        status = event.get("status", {}).get("type", {})
        start = datetime.fromisoformat(str(event["date"]).replace("Z", "+00:00"))
        games.append({
            "gameId": str(event.get("id", "")),
            "gameDateTimeUTC": start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "gameStatus": {"pre": "1", "in": "2", "post": "3"}.get(status.get("state"), "1"),
            "gameStatusText": status.get("description", "Scheduled"),
            "homeTeam": {"teamTricode": nba_code(home.get("team", {}).get("abbreviation", ""))},
            "awayTeam": {"teamTricode": nba_code(away.get("team", {}).get("abbreviation", ""))},
        })
    return games


def fetch_schedule(today: date | None = None) -> dict:
    today = today or datetime.now(timezone.utc).astimezone(EASTERN).date()
    current = get_json(f"{SCOREBOARD_URL}?{urlencode({'dates': today.strftime('%Y%m%d')})}")
    calendars = (current.get("leagues") or [{}])[0].get("calendar", [])
    if not calendars:
        events = _schedule_games(current)
        if not events:
            raise RuntimeError("ESPN has no NBA schedule calendar or games for the current date.")
        return {"leagueSchedule": {"gameDates": [{"gameDate": today.isoformat(), "games": events}]}}

    existing_max = today - timedelta(days=1)
    if DATA_PATH.exists():
        with DATA_PATH.open(newline="", encoding="utf-8") as source:
            existing_max = max(
                (date.fromisoformat(row["GAME_DATE"]) for row in csv.DictReader(source)),
                default=existing_max,
            )
    first_day = min(today - timedelta(days=3), existing_max + timedelta(days=1))
    last_day = today + timedelta(days=35)
    calendar_days = sorted({
        datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(EASTERN).date()
        for value in calendars
    })
    query_days = [day for day in calendar_days if first_day <= day <= last_day]
    payloads = {today: current}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(get_json, f"{SCOREBOARD_URL}?{urlencode({'dates': day.strftime('%Y%m%d')})}"): day
            for day in query_days if day != today
        }
        for future in as_completed(futures):
            payloads[futures[future]] = future.result()

    by_date: dict[date, dict[str, dict]] = {}
    for query_day, payload in payloads.items():
        for game in _schedule_games(payload):
            game_date = datetime.fromisoformat(game["gameDateTimeUTC"].replace("Z", "+00:00")).astimezone(EASTERN).date()
            if not first_day <= game_date <= last_day:
                continue
            by_date.setdefault(game_date, {})[game["gameId"]] = game
    games_count = sum(map(len, by_date.values()))
    if not games_count:
        raise RuntimeError("ESPN schedule requests returned no games in the refresh window.")
    return {"leagueSchedule": {"gameDates": [
        {"gameDate": day.isoformat(), "games": list(day_games.values())}
        for day, day_games in sorted(by_date.items())
    ]}}


def is_final(game: dict) -> bool:
    return str(game.get("gameStatus")) == "3"


def number(value) -> int | float:
    if value in (None, "", "-"):
        return 0
    numeric = float(value)
    return int(numeric) if numeric.is_integer() else numeric


def minutes_as_decimal(value) -> float:
    text = str(value or "0").strip()
    if not text or text in {"-", "--"}:
        return 0.0
    if ":" in text:
        minutes, seconds = text.split(":", 1)
        return round(float(minutes) + float(seconds) / 60, 2)
    return float(text)


def _name_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def boxscore_rows(game: dict, name_to_player_id: dict[str, str]) -> list[dict]:
    game_id = str(game["gameId"])
    payload = get_json(f"{SUMMARY_URL}?{urlencode({'event': game_id})}")
    boxscore = payload.get("boxscore", {})
    teams = boxscore.get("players", [])
    if len(teams) < 2:
        raise RuntimeError(f"Box score for game {game_id} has no player stats.")
    game_time = datetime.fromisoformat(game["gameDateTimeUTC"].replace("Z", "+00:00"))
    game_date = game_time.date()
    season_year = game_date.year if game_date.month >= 7 else game_date.year - 1
    season = f"{season_year}-{(season_year + 1) % 100:02d}"
    home_code = nba_code(game["homeTeam"]["teamTricode"])
    away_code = nba_code(game["awayTeam"]["teamTricode"])
    rows = []

    for team in teams:
        team_info = team.get("team", {})
        team_code = nba_code(str(team_info.get("abbreviation", "")))
        if not team_code:
            raise RuntimeError(f"Box score for game {game_id} has no team code.")
        opponent = away_code if team_code == home_code else home_code
        marker = "vs." if team_code == home_code else "@"
        for stat_group in team.get("statistics", []):
            labels = stat_group.get("labels", [])
            if not labels:
                continue
            positions = {label: i for i, label in enumerate(labels)}
            for athlete in stat_group.get("athletes", []):
                if athlete.get("didNotPlay"):
                    continue
                player = athlete.get("athlete", {})
                name = player.get("displayName") or player.get("fullName")
                espn_id = str(player.get("id", ""))
                stats = athlete.get("stats", [])
                if not name or not stats:
                    continue
                known_id = name_to_player_id.get(_name_key(name))
                player_id = known_id or f"espn:{espn_id}"
                get = lambda key: stats[positions[key]] if key in positions and positions[key] < len(stats) else 0
                # Box-score strings include made-attempted pairs; 3PT takes the first value.
                threes = str(get("3PT")).split("-", 1)[0]
                rows.append({
                    "PLAYER_ID": player_id,
                    "PLAYER_NAME": name,
                    "TEAM_ABBREVIATION": team_code,
                    "GAME_ID": game_id,
                    "GAME_DATE": game_date.isoformat(),
                    "MATCHUP": f"{team_code} {marker} {opponent}",
                    "MIN": minutes_as_decimal(get("MIN")),
                    "PTS": number(get("PTS")),
                    "REB": number(get("REB")),
                    "AST": number(get("AST")),
                    "FG3M": number(threes),
                    "STL": number(get("STL")),
                    "BLK": number(get("BLK")),
                    "TOV": number(get("TO")),
                    "SEASON": season,
                })
            break
    if not rows:
        raise RuntimeError(f"Box score for game {game_id} returned no player rows.")
    return rows


def atomic_json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(payload, temporary, separators=(",", ":"))
        temporary.write("\n")
        temp_name = temporary.name
    os.replace(temp_name, path)


def append_new_games(schedule: dict) -> int:
    with DATA_PATH.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames or []
        if not set(CSV_COLUMNS).issubset(fieldnames):
            raise RuntimeError("Player game log CSV is missing expected columns.")
        existing_rows = list(reader)
    existing_keys = {(str(row["GAME_ID"]), str(row["PLAYER_ID"])) for row in existing_rows}
    game_ids_with_rows = {game_id for game_id, _ in existing_keys}
    name_to_player_id = {}
    for row in existing_rows:
        name_to_player_id.setdefault(_name_key(row["PLAYER_NAME"]), str(row["PLAYER_ID"]))
    games = [game for day in schedule["leagueSchedule"]["gameDates"] for game in day["games"]]
    missing_games = [game for game in games if is_final(game) and game["gameId"] not in game_ids_with_rows]
    if not missing_games:
        return 0

    appended, failures = [], []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(boxscore_rows, game, name_to_player_id): game["gameId"] for game in missing_games}
        for future in as_completed(futures):
            game_id = futures[future]
            try:
                appended.extend(future.result())
            except (URLError, TimeoutError, ValueError, KeyError, RuntimeError, OSError) as exc:
                failures.append(f"{game_id}: {exc}")
    if failures:
        raise RuntimeError(f"Could not fetch {len(failures)} of {len(missing_games)} completed games; refusing partial refresh. {'; '.join(failures[:5])}")

    new_rows, new_keys = [], set()
    for row in appended:
        key = (row["GAME_ID"], row["PLAYER_ID"])
        if key not in existing_keys and key not in new_keys:
            new_rows.append(row)
            new_keys.add(key)
    fieldnames = list(dict.fromkeys([*CSV_COLUMNS, *fieldnames]))
    with tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8", dir=DATA_PATH.parent, delete=False) as temporary:
        writer = csv.DictWriter(temporary, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)
        writer.writerows(new_rows)
        temp_name = temporary.name
    os.replace(temp_name, DATA_PATH)
    return len(new_rows)


def set_output(key: str, value: str) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"{key}={value}\n")


def main() -> None:
    schedule = fetch_schedule()
    schedule_changed = not SCHEDULE_PATH.exists() or json.loads(SCHEDULE_PATH.read_text(encoding="utf-8")) != schedule
    if schedule_changed:
        atomic_json_write(SCHEDULE_PATH, schedule)
    games_added = append_new_games(schedule)
    changed = schedule_changed or games_added > 0
    set_output("games_added", str(games_added))
    set_output("schedule_changed", str(schedule_changed).lower())
    set_output("data_changed", str(changed).lower())
    latest_date = max((parse_date(game["gameDateTimeUTC"]) for day in schedule["leagueSchedule"]["gameDates"] for game in day["games"] if is_final(game)), default=None)
    print(f"ESPN NBA schedule processed. Added {games_added} player rows; schedule changed: {schedule_changed}; latest completed game: {latest_date or 'unknown'}.")


if __name__ == "__main__":
    main()
