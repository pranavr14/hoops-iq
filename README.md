# HoopsIQ

HoopsIQ is an NBA player performance forecasting application that uses historical basketball statistics, data analytics, and machine learning to predict upcoming player stat lines.

The project is built for educational sports analytics and is not intended for betting, wagering, or gambling.

## Initial Prediction Targets

- Points
- Assists
- Rebounds
- Three-pointers made

## Planned Features

- Historical NBA player and game data
- Recent-performance trends
- Opponent-based analysis
- Player stat forecasting
- Prediction ranges
- Model performance tracking
- Explainable prediction factors

## Planned Tech Stack

- Python
- Pandas
- PostgreSQL
- scikit-learn
- FastAPI
- React
- TypeScript

## Project Status

🚧 In development; the V2 prediction API and frontend deployment configuration are ready for a public demo.

## Run the prediction API

From the project directory, start the server with the existing virtual environment:

```bash
cd ~/hoops-iq
.venv/bin/python -m uvicorn backend.main:app --reload
```

Keep that terminal running, then open http://127.0.0.1:8000/docs.
Use **POST /predict → Try it out**, enter the example below, and click **Execute**:

```json
{
  "player_name": "LeBron James",
  "opponent": "MIL",
  "game_date": "2026-01-09",
  "home_game": true
}
```

The response includes predicted points, last-5 and last-10 scoring averages,
days since the last game, and any long-gap warning. Opponents use NBA team
abbreviations. Only games before the requested date contribute to features.
Unknown players, unsupported opponents, and insufficient history return HTTP 400;
invalid request fields return HTTP 422. GET /health returns `{"status":"ok"}`
when the API is running (it does not check model or data readiness).

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

The CSV data and trained models stay out of Git. The release asset contains only the game-log CSV required by the V2 API and its four V2 model files. To refresh the bundle, replace the release asset and update its SHA-256 value in `scripts/download_runtime_assets.py`.

### Frontend on Vercel

1. Import this repository and set the Vercel project root directory to `frontend`; select the `feature/prediction-pipeline` production branch.
2. Vercel uses `frontend/vercel.json` to build with `npm run build` and publish `dist`.
3. Add the `VITE_API_URL` environment variable with the Render API base URL (no trailing slash), then redeploy.

Vercel's free Hobby plan is intended for personal, non-commercial projects. Keep `.env`, datasets, model files, and temporary backups out of Git.
