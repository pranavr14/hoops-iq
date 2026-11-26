import argparse
from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT_ROOT / "data/player_game_logs_2025_26.csv"
MODEL_FILE = PROJECT_ROOT / "models/artifacts/points_model_v1.joblib"


def predict_points(player_name, opponent, game_date, home_game):
    player_name = player_name.strip()
    opponent = opponent.strip().upper()

    # Load the trained model and its exact feature list.
    bundle = joblib.load(MODEL_FILE)

    # Load historical NBA game logs.
    df = pd.read_csv(DATA_FILE)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])

    target_date = pd.to_datetime(
        game_date,
        format="%Y-%m-%d"
    )

    if not df["PLAYER_NAME"].str.casefold().eq(player_name.casefold()).any():
        raise ValueError(f"Unknown player: {player_name}.")

    # Never use games on or after the prediction date.
    history = df[df["GAME_DATE"] < target_date].copy()

    history["OPPONENT"] = (
        history["MATCHUP"].str.split().str[-1]
    )

    # Find the player's previous games.
    player_games = history[
        history["PLAYER_NAME"].str.casefold()
        == player_name.casefold()
    ].sort_values("GAME_DATE")

    if len(player_games) < 10:
        raise ValueError(
            "Player needs at least 10 previous games "
            "for a prediction."
        )

    if player_games["PLAYER_ID"].nunique() != 1:
        raise ValueError(
            "Multiple player IDs match this name."
        )

    opponent = opponent.upper()
    opponent_column = f"OPP_{opponent}"

    if opponent_column not in bundle["features"]:
        raise ValueError(
            f"Opponent {opponent} is not supported "
            "by this model."
        )

    # Calculate opponent statistics from earlier dates.
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

    days_rest = (target_date - last_game_date).days

    # Initialize features in the exact order used in training.
    features = {
        feature: 0.0
        for feature in bundle["features"]
    }

    features.update({
        "HOME_GAME": int(home_game),
        "DAYS_REST": days_rest,
        "PTS_LAST_5": last_5["PTS"].mean(),
        "REB_LAST_5": last_5["REB"].mean(),
        "AST_LAST_5": last_5["AST"].mean(),
        "FG3M_LAST_5": last_5["FG3M"].mean(),
        "MIN_LAST_5": last_5["MIN"].mean(),
        "PTS_LAST_10": last_10["PTS"].mean(),
        "OPP_PTS_ALLOWED_AVG": opponent_games["PTS"].mean(),
    })

    features[opponent_column] = 1

    X = pd.DataFrame(
        [features],
        columns=bundle["features"]
    )

    prediction = bundle["model"].predict(X)[0]

    return {
        "player_name": str(player_games["PLAYER_NAME"].iloc[-1]),
        "opponent": opponent,
        "game_date": target_date.strftime("%Y-%m-%d"),
        "home_game": bool(home_game),
        "predicted_points": float(prediction),
        "pts_last_5": float(last_5["PTS"].mean()),
        "pts_last_10": float(last_10["PTS"].mean()),
        "days_rest": int(days_rest),
        "warnings": [
            "Long gap since the player's last game. Prediction may be unreliable."
        ] if days_rest > 30 else [],
    }


def print_prediction(result):
    """Keep human-readable output for command-line use."""
    print()
    print("HoopsIQ Points Prediction")
    print("-------------------------")
    print(f"Player: {result['player_name']}")
    print(f"Opponent: {result['opponent']}")
    print(f"Game date: {result['game_date']}")
    print(f"Location: {'Home' if result['home_game'] else 'Away'}")
    print(f"Last-5 points average: {result['pts_last_5']:.2f}")
    print(f"Last-10 points average: {result['pts_last_10']:.2f}")
    print(f"Days since last game: {result['days_rest']}")
    print()
    print(f"Predicted points: {result['predicted_points']:.2f}")
    for warning in result["warnings"]:
        print()
        print(f"Warning: {warning}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--player", required=True)
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--home", action="store_true")

    args = parser.parse_args()

    result = predict_points(
        player_name=args.player,
        opponent=args.opponent,
        game_date=args.date,
        home_game=args.home
    )

    print_prediction(result)
