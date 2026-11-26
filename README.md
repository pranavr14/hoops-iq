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

🚧 In development

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
