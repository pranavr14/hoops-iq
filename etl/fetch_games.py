import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BALLDONTLIE_API_KEY")

URL = "https://api.balldontlie.io/v1/games"

headers = {
    "Authorization": API_KEY
}

params = {
    "seasons[]": 2025,
    "per_page": 10
}

response = requests.get(
    URL,
    headers=headers,
    params=params
)

if response.status_code == 200:
    data = response.json()

    print("Game API request successful!")
    print()

    for game in data["data"]:
        print(
            game["date"],
            "-",
            game["home_team"]["full_name"],
            "vs",
            game["visitor_team"]["full_name"],
            "-",
            game["home_team_score"],
            ":",
            game["visitor_team_score"]
        )

else:
    print("Request failed:", response.status_code)
    print(response.text)

