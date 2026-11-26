
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data")

season_files = {
    "2025-26": DATA_DIR / "player_game_logs_2025_26.csv",
    "2026-27": DATA_DIR / "player_game_logs_2026_27.csv",
}

frames = []

for season, file_path in season_files.items():
    df = pd.read_csv(
        file_path,
        dtype={"PLAYER_ID": "string", "GAME_ID": "string"},
    )

    df["SEASON"] = season
    frames.append(df)

combined = pd.concat(frames, ignore_index=True)

# Standardize dates across both seasons.
combined["GAME_DATE"] = (
    pd.to_datetime(combined["GAME_DATE"])
    .dt.strftime("%Y-%m-%d")
)

# Keep one record per player per game.
combined = combined.drop_duplicates(
    subset=["PLAYER_ID", "GAME_ID"]
)

# Put games in chronological order.
combined = combined.sort_values(
    ["GAME_DATE", "PLAYER_ID"]
).reset_index(drop=True)

output_path = DATA_DIR / "player_game_logs_2025_27.csv"
combined.to_csv(output_path, index=False)

print("HoopsIQ Combined NBA Dataset")
print("----------------------------")
print(combined.groupby("SEASON").size().to_string())
print()
print(f"Total player-game records: {len(combined):,}")
print(f"Saved to: {output_path}")
