from nba_api.stats.endpoints import playergamelogs


def fetch_player_game_logs():
    game_logs = playergamelogs.PlayerGameLogs(
        season_nullable="2025-26",
        season_type_nullable="Regular Season"
    )

    df = game_logs.get_data_frames()[0]

    columns_to_keep = [
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ABBREVIATION",
        "GAME_ID",
        "GAME_DATE",
        "MATCHUP",
        "MIN",
        "PTS",
        "REB",
        "AST",
        "FG3M",
        "STL",
        "BLK",
        "TOV"
    ]

    df = df[columns_to_keep]

    print("NBA player game stats request successful!")
    print()
    print(df.head(10).to_string(index=False))
    output_path = "data/player_game_logs_2025_26.csv"
    df.to_csv(output_path, index=False)

    print()
    print(f"Saved {len(df)} rows to {output_path}")

if __name__ == "__main__":
    fetch_player_game_logs()
