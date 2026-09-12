import pandas as pd


INPUT_FILE = "data/player_game_logs_2025_26.csv"
OUTPUT_FILE = "data/training_features_2025_26.csv"


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


    # Group data by player
    player_groups = df.groupby("PLAYER_ID")
    
    # Group data by opponent
    opponent_groups = df.groupby("OPPONENT")

    # Average points scored against this opponent in prior games only
    df["OPP_PTS_ALLOWED_AVG"] = opponent_groups["PTS"].transform(
        lambda x: x.shift(1).expanding().mean()
    )
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

    # Calculate days of rest since previous game
    df["DAYS_REST"] = player_groups["GAME_DATE"].diff().dt.days

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
        "MATCHUP",
        "OPPONENT",
	"OPP_PTS_ALLOWED_AVG",
        "HOME_GAME",
        "DAYS_REST",
        "PTS_LAST_5",
        "REB_LAST_5",
        "AST_LAST_5",
        "FG3M_LAST_5",
        "MIN_LAST_5",
        "PTS_LAST_10",
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
