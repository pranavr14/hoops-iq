"""Refresh the current NBA schedule and completed player box scores.

This runs in GitHub Actions after the previous night's games. It reads NBA's
public CDN schedule and per-game box scores, appends new player game rows, and
stores the current season schedule for the prediction API.
"""

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/player_game_logs_2025_27.csv"
SCHEDULE_PATH = ROOT / "data/nba_schedule.json"
SCHEDULE_URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
BOXSCORE_URL = "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
NBA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/",
}
CSV_COLUMNS = [
    "PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "GAME_ID",
    "GAME_DATE", "MATCHUP", "MIN", "PTS", "REB", "AST", "FG3M",
    "STL", "BLK", "TOV", "SEASON",
]


def get_json(url: str) -> dict:
    request = Request(url, headers=NBA_HEADERS)
    last_error = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(
                        f"NBA CDN returned HTTP {response.status} for {url}"
                    )
                return json.load(response)
        except (URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not fetch NBA data after retries: {url}") from last_error


def parse_date(value: str) -> date:
    value = value.strip()
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(value[:10], pattern).date()
        except ValueError:
            pass
    if "T" in value:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    raise ValueError(f"Unsupported NBA schedule date: {value!r}")


def schedule_games(schedule: dict) -> tuple[dict, list[tuple[date, dict]]]:
    league_schedule = schedule.get("leagueSchedule")
    if not isinstance(league_schedule, dict):
        raise RuntimeError("NBA schedule response has no leagueSchedule object.")

    game_dates = league_schedule.get("gameDates")
    if not isinstance(game_dates, list) or not game_dates:
        raise RuntimeError("NBA schedule response has no gameDates.")

    normalized = {"leagueSchedule": league_schedule}
    games: list[tuple[date, dict]] = []
    for day in game_dates:
        bucket_date = parse_date(str(day["gameDate"]))
        for game in day.get("games", []):
            games.append((bucket_date, game))
    if not games:
        raise RuntimeError("NBA schedule response contains no games.")
    return normalized, games


def is_final(game: dict) -> bool:
    status = game.get("gameStatus")
    if str(status) == "3":
        return True
    status_text = str(game.get("gameStatusText", "")).casefold()
    return status_text.startswith("final")


def minutes_as_decimal(value) -> float:
    if value is None or value == "":
        return 0.0
    text = str(value)
    iso = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", text)
    if iso:
        hours, minutes, seconds = iso.groups()
        return round(
            int(hours or 0) * 60 + int(minutes or 0) + float(seconds or 0) / 60,
            2,
        )
    if ":" in text:
        minutes, seconds = text.split(":", 1)
        return round(float(minutes) + float(seconds) / 60, 2)
    return float(text)


def number(value) -> int | float:
    if value in (None, ""):
        return 0
    numeric = float(value)
    return int(numeric) if numeric.is_integer() else numeric


def boxscore_rows(game_date: date, game_id: str) -> list[dict]:
    payload = get_json(BOXSCORE_URL.format(game_id=game_id))
    game = payload.get("game")
    if not isinstance(game, dict) or str(game.get("gameStatus")) != "3":
        raise RuntimeError(f"Box score for game {game_id} is not final yet.")

    rows = []
    home = game.get("homeTeam", {})
    away = game.get("awayTeam", {})
    home_code = str(home.get("teamTricode", "")).upper()
    away_code = str(away.get("teamTricode", "")).upper()
    if not home_code or not away_code:
        raise RuntimeError(f"Box score for game {game_id} is missing team codes.")
    season_year = int(game_date.year if game_date.month >= 7 else game_date.year - 1)
    season = f"{season_year}-{(season_year + 1) % 100:02d}"

    for side, team, opponent, matchup_marker in (
        ("home", home, away_code, "vs."),
        ("away", away, home_code, "@"),
    ):
        team_code = str(team.get("teamTricode", "")).upper()
        for player in team.get("players", []):
            stats = player.get("statistics") or {}
            if str(player.get("played", "1")) == "0" or not stats:
                continue
            person_id = player.get("personId")
            name = player.get("name")
            if person_id is None or not name:
                continue
            rows.append({
                "PLAYER_ID": str(person_id),
                "PLAYER_NAME": str(name),
                "TEAM_ABBREVIATION": team_code,
                "GAME_ID": str(game_id),
                "GAME_DATE": game_date.isoformat(),
                "MATCHUP": f"{team_code} {matchup_marker} {opponent}",
                "MIN": minutes_as_decimal(stats.get("minutes")),
                "PTS": number(stats.get("points")),
                "REB": number(stats.get("reboundsTotal")),
                "AST": number(stats.get("assists")),
                "FG3M": number(stats.get("threePointersMade")),
                "STL": number(stats.get("steals")),
                "BLK": number(stats.get("blocks")),
                "TOV": number(stats.get("turnovers")),
                "SEASON": season,
            })
    return rows


def atomic_json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        json.dump(payload, temporary, separators=(",", ":"))
        temporary.write("\n")
        temp_name = temporary.name
    os.replace(temp_name, path)


def append_new_games(games: list[tuple[date, dict]]) -> int:
    with DATA_PATH.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames or []
        if not set(CSV_COLUMNS).issubset(fieldnames):
            raise RuntimeError("Player game log CSV is missing expected columns.")
        existing_rows = list(reader)

    existing_keys = {
        (str(row["GAME_ID"]), str(row["PLAYER_ID"]))
        for row in existing_rows
    }
    existing_game_ids = {game_id for game_id, _ in existing_keys}
    missing_games = [
        (game_date, game)
        for game_date, game in games
        if is_final(game)
        and str(game.get("gameId", ""))
        and str(game["gameId"]) not in existing_game_ids
    ]

    if not missing_games:
        return 0

    appended: list[dict] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(
                boxscore_rows,
                game_date,
                str(game["gameId"]),
            ): str(game["gameId"])
            for game_date, game in missing_games
        }
        for future in as_completed(futures):
            game_id = futures[future]
            try:
                appended.extend(future.result())
            except (URLError, TimeoutError, ValueError, KeyError, RuntimeError, OSError) as exc:
                failures.append(f"{game_id}: {exc}")

    if failures:
        sample = "; ".join(failures[:5])
        raise RuntimeError(
            f"Could not fetch {len(failures)} of {len(missing_games)} "
            f"completed games; refusing a partial refresh. {sample}"
        )
    if not appended:
        raise RuntimeError(
            "Completed games were found but no player box-score rows were returned."
        )

    new_keys = set()
    unique_rows = []
    for row in appended:
        key = (row["GAME_ID"], row["PLAYER_ID"])
        if key not in existing_keys and key not in new_keys:
            unique_rows.append(row)
            new_keys.add(key)

    fieldnames = list(dict.fromkeys([*CSV_COLUMNS, *fieldnames]))
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", newline="", encoding="utf-8", dir=DATA_PATH.parent,
        delete=False,
    ) as temporary:
        writer = csv.DictWriter(temporary, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)
        writer.writerows(unique_rows)
        temp_name = temporary.name
    os.replace(temp_name, DATA_PATH)
    return len(unique_rows)


def set_output(key: str, value: str) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"{key}={value}\n")


def main() -> None:
    schedule_payload = get_json(SCHEDULE_URL)
    normalized_schedule, games = schedule_games(schedule_payload)
    schedule_changed = not SCHEDULE_PATH.exists() or json.loads(
        SCHEDULE_PATH.read_text(encoding="utf-8")
    ) != normalized_schedule
    if schedule_changed:
        atomic_json_write(SCHEDULE_PATH, normalized_schedule)

    games_added = append_new_games(games)
    changed = schedule_changed or games_added > 0
    set_output("games_added", str(games_added))
    set_output("schedule_changed", str(schedule_changed).lower())
    set_output("data_changed", str(changed).lower())
    latest_date = max(
        (game_date for game_date, game in games if is_final(game)),
        default=None,
    )
    print(
        f"Current NBA schedule processed. Added {games_added} player rows; "
        f"schedule changed: {schedule_changed}; "
        f"latest completed game: {latest_date or 'unknown'}."
    )


if __name__ == "__main__":
    main()
