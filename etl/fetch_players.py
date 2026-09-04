import requests

URL = "https://api.balldontlie.io/v1/players"

headers = {
    "Authorization": "YOUR_API_KEY_HERE"
}

response = requests.get(URL, headers=headers)

if response.status_code == 200:
    data = response.json()

    print("API request successful!")
    print()

    for player in data["data"][:10]:
        print(
            player["first_name"],
            player["last_name"],
            "-",
            player["position"]
        )

else:
    print("Request failed:", response.status_code)
    print(response.text)
