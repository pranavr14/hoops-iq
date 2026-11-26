import pandas as pd


INPUT_FILE = "data/player_game_logs_2025_27.csv"
OUTPUT_FILE = "data/training_features_v2.csv"


def build_features():
    df = pd.read_csv(INPUT_FILE)

    # Convert game date into a real date
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])

    # Sort each player's games from oldest to newest
    df = df.sort_values(
        by=["PLAYER_ID", "GAME_DATE"]
    ).reset_index(drop=True)

    # Determine whether the player was at home
    df["HOME_GAME"] = (
        df["MATCHUP"].str.contains("vs.")
    ).astype(int)
    # Extract opponent team abbreviation from MATCHUP
    df["OPPONENT"] = df["MATCHUP"].apply(
        lambda matchup: matchup.split()[-1]
    )

    # Calculate opponent averages using only earlier game dates.
    opponent_daily = (
        df.groupby(["OPPONENT", "GAME_DATE"])["PTS"]
        .agg(total_points="sum", player_games="count")
        .reset_index()
        .sort_values(["OPPONENT", "GAME_DATE"])
    )

    opponent_daily["prior_points"] = (
        opponent_daily.groupby("OPPONENT")["total_points"].cumsum()
        - opponent_daily["total_points"]
    )

    opponent_daily["prior_player_games"] = (
        opponent_daily.groupby("OPPONENT")["player_games"].cumsum()
        - opponent_daily["player_games"]
    )

    opponent_daily["OPP_PTS_ALLOWED_AVG"] = (
        opponent_daily["prior_points"]
        / opponent_daily["prior_player_games"]
    )

    df = df.merge(
        opponent_daily[["OPPONENT", "GAME_DATE", "OPP_PTS_ALLOWED_AVG"]],
        on=["OPPONENT", "GAME_DATE"],
        how="left",
        validate="many_to_one",
    )

    # Group players after the merge for rolling statistics.
    player_groups = df.groupby("PLAYER_ID")

    # Rolling averages use ONLY games before the game being predicted
    df["PTS_LAST_5"] = player_groups["PTS"].transform(
        lambda x: x.shift(1).rolling(5).mean()
    )

    df["REB_LAST_5"] = player_groups["REB"].transform(
        lambda x: x.shift(1).rolling(5).mean()
    )

    df["AST_LAST_5"] = player_groups["AST"].transform(
        lambda x: x.shift(1).rolling(5).mean()
    )

    df["FG3M_LAST_5"] = player_groups["FG3M"].transform(
        lambda x: x.shift(1).rolling(5).mean()
    )

    df["MIN_LAST_5"] = player_groups["MIN"].transform(
        lambda x: x.shift(1).rolling(5).mean()
    )

    df["PTS_LAST_10"] = player_groups["PTS"].transform(
        lambda x: x.shift(1).rolling(10).mean()
    )

    df["REB_LAST_10"] = player_groups["REB"].transform(
        lambda x: x.shift(1).rolling(10).mean()
    )

    df["AST_LAST_10"] = player_groups["AST"].transform(
        lambda x: x.shift(1).rolling(10).mean()
    )

    df["FG3M_LAST_10"] = player_groups["FG3M"].transform(
        lambda x: x.shift(1).rolling(10).mean()
    )

    # Recent scoring trend: positive = heating up, negative = cooling down
    df["PTS_TREND"] = df["PTS_LAST_5"] - df["PTS_LAST_10"]

    # Identify when a player moves into a new NBA season
    previous_season = player_groups["SEASON"].shift(1)

    df["OFFSEASON_BREAK"] = (
        previous_season.notna()
        & df["SEASON"].ne(previous_season)
    ).astype(int)

    # Cap long gaps so they don't dominate the rest feature
    df["DAYS_REST_RAW"] = player_groups["GAME_DATE"].diff().dt.days
    df["DAYS_REST"] = df["DAYS_REST_RAW"].clip(upper=14)

    # Remove rows where we don't yet have enough prior games
    df = df.dropna(
        subset=[
            "PTS_LAST_5",
            "REB_LAST_5",
            "AST_LAST_5",
            "FG3M_LAST_5",
            "MIN_LAST_5",
            "PTS_LAST_10",
            "DAYS_REST"
        ]
    )

    # Keep useful training columns
    training_columns = [
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ABBREVIATION",
        "GAME_ID",
        "GAME_DATE",
        "SEASON",
        "MATCHUP",
        "OPPONENT",
        "OPP_PTS_ALLOWED_AVG",
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
        "PTS_TREND",
        "PTS",
        "REB",
        "AST",
        "FG3M"
    ]

    training_df = df[training_columns]

    training_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("Feature engineering successful!")
    print()
    print(f"Created {len(training_df)} training rows.")
    print(f"Saved to {OUTPUT_FILE}")
    print()
    print(training_df.head(10).to_string(index=False))


if __name__ == "__main__":
    build_features()
