"""Resolve a player's next scheduled matchup from the refreshed NBA schedule."""

import json
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT_ROOT / "data/player_game_logs_2025_27.csv"
SCHEDULE_FILE = PROJECT_ROOT / "data/nba_schedule.json"
EASTERN = ZoneInfo("America/New_York")


def _parse_schedule_date(value: str) -> date:
    value = value.strip()
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(value[:10], pattern).date()
        except ValueError:
            pass
    if "T" in value:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    raise ValueError(f"Unsupported schedule date: {value!r}")


def _team_code(game: dict, side: str) -> str:
    team = game.get(f"{side}Team")
    if isinstance(team, dict):
        return str(team.get("teamTricode", "")).upper()
    return str(game.get(f"{side}Team_teamTricode", "")).upper()


def find_next_matchup(player_name: str) -> dict:
    player_name = player_name.strip()
    if not player_name:
        raise ValueError("Enter a player's name.")
    if not SCHEDULE_FILE.is_file():
        raise ValueError(
            "The NBA schedule has not been refreshed yet. Try again after the daily data update."
        )

    data = pd.read_csv(DATA_FILE, dtype={"PLAYER_ID": "string"})
    matches = data[
        data["PLAYER_NAME"].astype(str).str.casefold() == player_name.casefold()
    ].copy()
    if matches.empty:
        raise ValueError(f"Unknown player: {player_name}.")

    matches["GAME_DATE"] = pd.to_datetime(matches["GAME_DATE"], errors="coerce")
    latest_date = matches["GAME_DATE"].max()
    latest_rows = matches[matches["GAME_DATE"] == latest_date]
    teams = latest_rows["TEAM_ABBREVIATION"].dropna().astype(str).unique()
    if len(teams) != 1:
        raise ValueError(
            f"Could not determine one current team for {player_name}."
        )
    team_code = teams[0].upper()

    schedule = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
    league_schedule = schedule.get("leagueSchedule", {})
    now_utc = datetime.now(timezone.utc)
    today = now_utc.astimezone(EASTERN).date()
    upcoming = []
    for day in league_schedule.get("gameDates", []):
        game_date = _parse_schedule_date(str(day["gameDate"]))
        if game_date < today:
            continue
        for game in day.get("games", []):
            status = str(game.get("gameStatus", ""))
            status_text = str(game.get("gameStatusText", "")).casefold()
            if status != "1" and not status_text.startswith("scheduled"):
                continue
            start_text = game.get("gameDateTimeUTC") or game.get("gameTimeUTC")
            if start_text:
                try:
                    start_time = datetime.fromisoformat(
                        str(start_text).replace("Z", "+00:00")
                    )
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=timezone.utc)
                    if start_time <= now_utc:
                        continue
                except ValueError:
                    # If the feed changes its clock format, keep using the
                    # schedule status and date instead of breaking lookups.
                    pass
            home = _team_code(game, "home")
            away = _team_code(game, "away")
            if team_code not in (home, away):
                continue
            opponent = away if team_code == home else home
            if not opponent:
                continue
            upcoming.append((game_date, game, opponent, team_code == home))

    if not upcoming:
        raise ValueError(
            f"No upcoming game is listed for {player_name}'s latest team ({team_code})."
        )

    game_date, game, opponent, home_game = min(
        upcoming, key=lambda item: (item[0], str(item[1].get("gameId", "")))
    )
    return {
        "player_name": str(latest_rows.iloc[-1]["PLAYER_NAME"]),
        "team": team_code,
        "opponent": opponent,
        "game_date": game_date.isoformat(),
        "home_game": home_game,
        "game_id": str(game.get("gameId", "")),
        "player_last_game_date": latest_date.date().isoformat(),
    }
