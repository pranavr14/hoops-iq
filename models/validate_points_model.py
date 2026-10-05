import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error


DATA_FILE = "data/training_features_2025_26.csv"


def validate_points_model():
    df = pd.read_csv(DATA_FILE)

    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])

    df = df.sort_values("GAME_DATE").reset_index(drop=True)

    # Convert opponent team into numeric one-hot columns.
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
    target = "PTS"

    df = df.dropna(
        subset=["OPP_PTS_ALLOWED_AVG"]
    ).reset_index(drop=True)

    unique_dates = (
        df["GAME_DATE"]
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    # Expanding-window validation:
    # train on 50%, 60%, 70%, 80%, and 90% of dates,
    # then test on the following 10% of dates.
    boundaries = [
        0.50,
        0.60,
        0.70,
        0.80,
        0.90,
        1.00
    ]

    validation_results = []

    for fold in range(5):
        train_end_position = int(
            len(unique_dates) * boundaries[fold]
        )

        test_end_position = int(
            len(unique_dates) * boundaries[fold + 1]
        )

        test_start_date = unique_dates.iloc[
            train_end_position
        ]

        if test_end_position < len(unique_dates):
            test_end_date = unique_dates.iloc[
                test_end_position
            ]

            train_df = df[
                df["GAME_DATE"] < test_start_date
            ]

            test_df = df[
                (df["GAME_DATE"] >= test_start_date)
                & (df["GAME_DATE"] < test_end_date)
            ]
        else:
            train_df = df[
                df["GAME_DATE"] < test_start_date
            ]

            test_df = df[
                df["GAME_DATE"] >= test_start_date
            ]

        X_train = train_df[features]
        X_test = test_df[features]

        y_train = train_df[target]
        y_test = test_df[target]

        linear_model = LinearRegression()
        linear_model.fit(
            X_train,
            y_train
        )

        linear_predictions = linear_model.predict(
            X_test
        )

        linear_mae = mean_absolute_error(
            y_test,
            linear_predictions
        )

        rf_model = RandomForestRegressor(
            n_estimators=200,
            max_depth=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        )

        rf_model.fit(
            X_train,
            y_train
        )

        rf_predictions = rf_model.predict(
            X_test
        )

        rf_mae = mean_absolute_error(
            y_test,
            rf_predictions
        )

        baseline_predictions = X_test["PTS_LAST_5"]

        baseline_mae = mean_absolute_error(
            y_test,
            baseline_predictions
        )

        validation_results.append({
            "Fold": fold + 1,
            "Train End": train_df["GAME_DATE"].max().date(),
            "Test Start": test_df["GAME_DATE"].min().date(),
            "Test End": test_df["GAME_DATE"].max().date(),
            "Train Rows": len(train_df),
            "Test Rows": len(test_df),
            "Linear MAE": linear_mae,
            "RF MAE": rf_mae,
            "Baseline MAE": baseline_mae
        })

    results_df = pd.DataFrame(validation_results)

    print()
    print("HoopsIQ Time-Series Validation")
    print("------------------------------")
    print(
        results_df.to_string(
            index=False,
            formatters={
                "Linear MAE": "{:.4f}".format,
                "RF MAE": "{:.4f}".format,
                "Baseline MAE": "{:.4f}".format
            }
        )
    )

    print()
    print("Average Performance")
    print("-------------------")
    print(
        f"Linear Regression MAE: "
        f"{results_df['Linear MAE'].mean():.4f}"
    )
    print(
        f"Random Forest MAE:     "
        f"{results_df['RF MAE'].mean():.4f}"
    )
    print(
        f"Last-5 Baseline MAE:   "
        f"{results_df['Baseline MAE'].mean():.4f}"
    )


if __name__ == "__main__":
    validate_points_model()
