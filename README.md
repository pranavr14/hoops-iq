# HoopsIQ

HoopsIQ is an NBA player performance forecasting application that uses historical basketball statistics, data analytics, and machine learning to predict upcoming player stat lines.

The project is built for educational sports analytics and is not intended for betting, wagering, or gambling.

## Initial Prediction Targets

- Points
- Assists
- Rebounds
- Three-pointers made

## Current Features

- Searchable NBA player selection
- Automatic next-game lookup from the current-season schedule
- Four projections: points, rebounds, assists, and three-pointers made
- Daily game-log refresh and model retraining after completed games
- Model/data freshness shown in the app

## Tech Stack

- Python
- Pandas
- scikit-learn
- FastAPI
- React
- TypeScript

## Project Status

HoopsIQ is deployed as a public demo. The React app is hosted on Vercel and the prediction API is hosted on Render.

## Run the prediction API

From the project directory, start the server with the existing virtual environment:

```bash
cd ~/hoops-iq
.venv/bin/python -m uvicorn backend.main:app --reload
```

Keep that terminal running, then open http://127.0.0.1:8000/docs. The live `POST /predict/next` endpoint accepts only a player name and finds that player's next scheduled game automatically:

```json
{
  "player_name": "LeBron James"
}
```

The API returns the opponent, date, home/away status, and predicted points,
rebounds, assists, and threes. `POST /predict/v2` remains available for explicit
matchups. `GET /status` returns the latest game-log date and current model metrics.
`GET /health` checks whether the API process is running.

## Automatic data updates

The GitHub Actions workflow `.github/workflows/update-nba-data.yml` runs daily
after the previous night's games and can also be started manually from the
repository's Actions tab. It downloads the current schedule and completed game
box scores from ESPN's public NBA data feed, adds new player rows, rebuilds features, and
re-trains the four stat models. When the refresh succeeds, it updates the runtime
bundle and commits the new schedule/data to the production branch. Render then
deploys the API with the refreshed data and Vercel rebuilds the app.

The refresh uses ESPN's public JSON NBA schedule and box-score feeds without an
API key or paid subscription. Each run refreshes recent game days plus the next
35 days of scheduled games. If a refresh cannot be completed, the workflow fails
without publishing a partial game-log update.
The player-to-team lookup follows each player's most recently recorded game, so
a trade is reflected after the player appears in a game for the new team.

The command-line interface remains available:

```bash
.venv/bin/python models/predict_points.py --player "LeBron James" --opponent MIL --date 2026-01-09 --home
```

Without `--home`, the command-line prediction is for an away game.

## Deploy the public demo

The intended deployment uses a free Render web service for the FastAPI backend and a Vercel static site for the React frontend. Free Render services can sleep after inactivity, so the first API request after a quiet period may take longer.

### Backend on Render

1. Import this repository's `feature/prediction-pipeline` branch as a Render Blueprint. Render reads the root `render.yaml` file and uses the free plan in the Ohio region.
2. The build installs `requirements.txt`, then downloads and checksum-verifies the runtime bundle from the GitHub Release tagged `hoops-iq-runtime-v2`.
3. After the first deploy, copy the API's `https://…onrender.com` URL. Set `FRONTEND_ORIGINS` to the Vercel site's exact origin if it differs from the default in `render.yaml`.

The current game-log CSV and schedule are committed to the production branch so
the daily workflow can update them. Trained model files stay out of Git in the
`hoops-iq-runtime-v2` GitHub Release asset; the workflow replaces that bundle
and pins its new SHA-256 value in `scripts/download_runtime_assets.py`.

### Frontend on Vercel

1. Import this repository and set the Vercel project root directory to `frontend`; select the `feature/prediction-pipeline` production branch.
2. Vercel uses `frontend/vercel.json` to build with `npm run build` and publish `dist`.
3. Add the `VITE_API_URL` environment variable with the Render API base URL (no trailing slash), then redeploy.

Vercel's free Hobby plan is intended for personal, non-commercial projects. Keep `.env`, datasets, model files, and temporary backups out of Git.
