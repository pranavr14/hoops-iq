
from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_FILE = PROJECT_ROOT / "data/player_game_logs_2025_27.csv"
MODEL_DIR = PROJECT_ROOT / "models/artifacts"

MODEL_FILES = {
    "predicted_points": "points_model_v2.joblib",
    "predicted_rebounds": "rebounds_model_v2.joblib",
    "predicted_assists": "assists_model_v2.joblib",
    "predicted_threes": "threes_model_v2.joblib",
}


def predict_multi_stats(player_name, opponent, game_date, home_game):
    player_name = player_name.strip()
    opponent = opponent.strip().upper()

    # Load the four trained models.
    bundles = {
        key: joblib.load(MODEL_DIR / filename)
        for key, filename in MODEL_FILES.items()
    }

    features = bundles["predicted_points"]["features"]

    # Ensure every model expects the same feature columns.
    for bundle in bundles.values():
        if bundle["features"] != features:
            raise ValueError("V2 model feature lists do not match.")

    # Load both seasons of NBA game logs.
    df = pd.read_csv(
        DATA_FILE,
        dtype={"PLAYER_ID": "string"}
    )

    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    target_date = pd.to_datetime(
        game_date,
        format="%Y-%m-%d"
    )

    if not df["PLAYER_NAME"].str.casefold().eq(
        player_name.casefold()
    ).any():
        raise ValueError(f"Unknown player: {player_name}.")

    # Never use games on or after the prediction date.
    history = df[df["GAME_DATE"] < target_date].copy()

    history["OPPONENT"] = (
        history["MATCHUP"].str.split().str[-1]
    )

    player_games = history[
        history["PLAYER_NAME"].str.casefold()
        == player_name.casefold()
    ].sort_values("GAME_DATE")

    if len(player_games) < 10:
        raise ValueError(
            "Player needs at least 10 previous games."
        )

    if player_games["PLAYER_ID"].nunique() != 1:
        raise ValueError(
            "Multiple player IDs match this name."
        )

    opponent_column = f"OPP_{opponent}"

    if opponent_column not in features:
        raise ValueError(
            f"Opponent {opponent} is not supported."
        )

    opponent_games = history[
        history["OPPONENT"] == opponent
    ]

    if opponent_games.empty:
        raise ValueError(
            f"No historical games found against {opponent}."
        )

    last_5 = player_games.tail(5)
    last_10 = player_games.tail(10)

    last_game_date = player_games["GAME_DATE"].iloc[-1]

    actual_days_rest = (
        target_date - last_game_date
    ).days

    # Match the capped rest feature used in v2 training.
    modeled_days_rest = min(actual_days_rest, 14)

    # NBA seasons are labeled by their starting year.
    # October is used as the season boundary.
    season_start = (
        target_date.year
        if target_date.month >= 10
        else target_date.year - 1
    )

    target_season = (
        f"{season_start}-{(season_start + 1) % 100:02d}"
    )

    previous_season = str(
        player_games["SEASON"].iloc[-1]
    )

    offseason_break = int(
        previous_season != target_season
    )

    # Build the same 43-feature input used in training.
    feature_values = {
        feature: 0.0
        for feature in features
    }

    feature_values.update({
        "HOME_GAME": int(home_game),
        "DAYS_REST": modeled_days_rest,
        "OFFSEASON_BREAK": offseason_break,
        "PTS_LAST_5": last_5["PTS"].mean(),
        "REB_LAST_5": last_5["REB"].mean(),
        "AST_LAST_5": last_5["AST"].mean(),
        "FG3M_LAST_5": last_5["FG3M"].mean(),
        "MIN_LAST_5": last_5["MIN"].mean(),
        "PTS_LAST_10": last_10["PTS"].mean(),
        "REB_LAST_10": last_10["REB"].mean(),
        "AST_LAST_10": last_10["AST"].mean(),
        "FG3M_LAST_10": last_10["FG3M"].mean(),
        "OPP_PTS_ALLOWED_AVG": opponent_games["PTS"].mean(),
    })

    feature_values[opponent_column] = 1

    X = pd.DataFrame(
        [feature_values],
        columns=features
    )

    # Generate all four predictions.
    predictions = {}

    for key, bundle in bundles.items():
        prediction = float(
            bundle["model"].predict(X)[0]
        )

        # NBA box-score statistics cannot be negative.
        predictions[key] = round(
            max(0.0, prediction),
            1
        )

    warnings = []

    if actual_days_rest > 30:
        warnings.append(
            "Long gap since the player's last game. "
            "Prediction may be unreliable."
        )

    if target_season not in set(df["SEASON"]):
        warnings.append(
            "The requested season is not represented "
            "in the training dataset."
        )

    return {
        "player_name": str(
            player_games["PLAYER_NAME"].iloc[-1]
        ),
        "opponent": opponent,
        "game_date": target_date.strftime("%Y-%m-%d"),
        "home_game": bool(home_game),
        **predictions,
        "pts_last_5": round(float(last_5["PTS"].mean()), 1),
        "pts_last_10": round(float(last_10["PTS"].mean()), 1),
        "days_rest": int(actual_days_rest),
        "modeled_days_rest": int(modeled_days_rest),
        "offseason_break": offseason_break,
        "warnings": warnings,
    }
