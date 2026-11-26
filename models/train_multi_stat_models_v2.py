
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error


DATA_FILE = "data/training_features_v2.csv"
MODEL_DIR = Path("models/artifacts")

TARGETS = {
    "PTS": ("PTS_LAST_5", "points_model_v2.joblib"),
    "REB": ("REB_LAST_5", "rebounds_model_v2.joblib"),
    "AST": ("AST_LAST_5", "assists_model_v2.joblib"),
    "FG3M": ("FG3M_LAST_5", "threes_model_v2.joblib"),
}


def train_models():
    df = pd.read_csv(DATA_FILE)

    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    df = df.sort_values(
        ["GAME_DATE", "PLAYER_ID"]
    ).reset_index(drop=True)

    # Convert opponents into numeric one-hot features.
    opponent_dummies = pd.get_dummies(
        df["OPPONENT"],
        prefix="OPP",
        dtype=int
    )

    df = pd.concat([df, opponent_dummies], axis=1)

    features = [
        "HOME_GAME",
        "DAYS_REST",
        "OFFSEASON_BREAK",
        "PTS_LAST_5",
        "REB_LAST_5",
        "AST_LAST_5",
        "FG3M_LAST_5",
        "MIN_LAST_5",
        "PTS_LAST_10",
        "REB_LAST_10",
        "AST_LAST_10",
        "FG3M_LAST_10",
        "OPP_PTS_ALLOWED_AVG",
    ]

    opponent_features = [
        column for column in opponent_dummies.columns
    ]

    features += opponent_features

    # Remove records missing model inputs.
    df = df.dropna(
        subset=features + list(TARGETS.keys())
    ).reset_index(drop=True)

    # Split chronologically by date, not randomly.
    # All games on a given date stay in the same split.
    unique_dates = df["GAME_DATE"].drop_duplicates()
    cutoff_index = int(len(unique_dates) * 0.80)
    cutoff_date = unique_dates.iloc[cutoff_index]

    train_df = df[df["GAME_DATE"] < cutoff_date]
    test_df = df[df["GAME_DATE"] >= cutoff_date]

    print("HoopsIQ v2 - Multi-Stat Model Training")
    print("--------------------------------------")
    print(f"Total usable rows: {len(df):,}")
    print(f"Training rows: {len(train_df):,}")
    print(f"Validation rows: {len(test_df):,}")
    print(f"Validation starts: {cutoff_date.date()}")
    print(f"Features: {len(features)}")
    print()

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    for target, (baseline_column, filename) in TARGETS.items():
        # Train only on earlier games for evaluation.
        validation_model = LinearRegression()
        validation_model.fit(
            train_df[features],
            train_df[target]
        )

        predictions = validation_model.predict(
            test_df[features]
        )

        model_mae = mean_absolute_error(
            test_df[target],
            predictions
        )

        baseline_mae = mean_absolute_error(
            test_df[target],
            test_df[baseline_column]
        )

        improvement = baseline_mae - model_mae

        print(f"{target} Prediction Model")
        print(f"  Linear Regression MAE: {model_mae:.4f}")
        print(f"  Last-5 Baseline MAE:   {baseline_mae:.4f}")
        print(f"  Improvement:           {improvement:+.4f}")

        # Once evaluated, retrain using all available
        # historical games for the saved production candidate.
        final_model = LinearRegression()
        final_model.fit(df[features], df[target])

        model_bundle = {
            "model": final_model,
            "features": features,
            "target": target,
            "version": "v2",
            "training_rows": len(df),
            "validation_mae": model_mae,
            "baseline_mae": baseline_mae,
            "validation_start": str(cutoff_date.date()),
        }

        output_path = MODEL_DIR / filename
        joblib.dump(model_bundle, output_path)

        print(f"  Saved: {output_path}")
        print()

    print("All four HoopsIQ v2 models trained successfully!")


if __name__ == "__main__":
    train_models()
