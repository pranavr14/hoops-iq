import os

import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression


DATA_FILE = "data/training_features_2025_26.csv"
MODEL_FILE = "models/artifacts/points_model_v1.joblib"


def train_production_model():
    df = pd.read_csv(DATA_FILE)

    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    df = df.sort_values("GAME_DATE").reset_index(drop=True)

    # Convert opponent teams into one-hot numeric columns.
    opponent_dummies = pd.get_dummies(
        df["OPPONENT"],
        prefix="OPP",
        dtype=int
    )

    df = pd.concat(
        [df, opponent_dummies],
        axis=1
    )

    features = [
        "HOME_GAME",
        "DAYS_REST",
        "PTS_LAST_5",
        "REB_LAST_5",
        "AST_LAST_5",
        "FG3M_LAST_5",
        "MIN_LAST_5",
        "PTS_LAST_10",
        "OPP_PTS_ALLOWED_AVG",
    ]

    opponent_features = [
        column for column in df.columns
        if column.startswith("OPP_")
        and column != "OPP_PTS_ALLOWED_AVG"
    ]

    features = features + opponent_features

    df = df.dropna(
        subset=["OPP_PTS_ALLOWED_AVG"]
    ).reset_index(drop=True)

    X = df[features]
    y = df["PTS"]

    # Model v1 was selected through chronological validation.
    # Retrain it on all available historical data for production use.
    model = LinearRegression()
    model.fit(X, y)

    model_bundle = {
        "model": model,
        "features": features,
        "target": "PTS",
        "version": "v1",
        "training_rows": len(df)
    }

    os.makedirs(
        os.path.dirname(MODEL_FILE),
        exist_ok=True
    )

    joblib.dump(
        model_bundle,
        MODEL_FILE
    )

    print("HoopsIQ Production Model")
    print("------------------------")
    print(f"Model version: v1")
    print(f"Model type: Linear Regression")
    print(f"Training rows: {len(df)}")
    print(f"Features: {len(features)}")
    print(f"Saved to: {MODEL_FILE}")


if __name__ == "__main__":
    train_production_model()
