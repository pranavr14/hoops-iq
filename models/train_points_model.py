import pandas as pd

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


DATA_FILE = "data/training_features_2025_26.csv"


def train_points_model():
    df = pd.read_csv(DATA_FILE)

    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])

    df = df.sort_values("GAME_DATE").reset_index(drop=True)
    # Convert opponent team into numeric one-hot columns
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
        "PTS_LAST_10"
    ]

    opponent_features = [
        column for column in df.columns
        if column.startswith("OPP_")
    ]

    features = features + opponent_features	
    target = "PTS"

    X = df[features]
    y = df[target]

    split_index = int(len(df) * 0.80)

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    model = LinearRegression()

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    # Baseline: predict points using the player's last-5-game average
    baseline_predictions = X_test["PTS_LAST_5"]

    baseline_mae = mean_absolute_error(y_test, baseline_predictions)

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    rmse = mean_squared_error(
        y_test,
        predictions
    ) ** 0.5

    r2 = r2_score(
        y_test,
        predictions
    )

    print("HoopsIQ Points Model")
    print("--------------------")
    print()

    print(f"Training rows: {len(X_train)}")
    print(f"Testing rows: {len(X_test)}")

    print()
    print("Model Performance")
    print("-----------------")

    print(f"MAE:  {mae:.2f} points")
    print(f"RMSE: {rmse:.2f}")
    print(f"R²:   {r2:.3f}")


    print("Baseline Comparison")
    print("-------------------")
    print(f"Last-5 Average MAE: {baseline_mae:.2f} points")
    print(f"Linear Model MAE:   {mae:.2f} points")

    improvement = baseline_mae - mae

    print(f"Improvement:        {improvement:.2f} points")

    print()
    print("Sample Predictions")
    print("------------------")

    results = df.iloc[split_index:].copy()

    results["PREDICTED_PTS"] = predictions

    display_columns = [
        "PLAYER_NAME",
        "GAME_DATE",
        "MATCHUP",
        "PTS_LAST_5",
        "PTS_LAST_10",
        "PREDICTED_PTS",
        "PTS"
    ]

    print(
        results[display_columns]
        .head(20)
        .to_string(index=False)
    )


if __name__ == "__main__":
    train_points_model()
