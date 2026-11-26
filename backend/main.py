"""Run from the project root: python -m uvicorn backend.main:app --reload."""
from pathlib import Path
import pandas as pd
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from models.predict_points import predict_points
from models.predict_multi_stats_v2 import predict_multi_stats


app = FastAPI(title="HoopsIQ API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class PredictionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    player_name: str = Field(min_length=1, max_length=100)
    opponent: str = Field(min_length=1, max_length=30,
                          description="NBA team abbreviation, e.g. MIL")
    game_date: date = Field(description="Prediction date in YYYY-MM-DD format")
    home_game: StrictBool


class PredictionResponse(BaseModel):
    player_name: str
    opponent: str
    game_date: date
    home_game: bool
    predicted_points: float
    pts_last_5: float
    pts_last_10: float
    days_rest: int
    warnings: list[str]

# NEW: HoopsIQ v2 response model


class MultiStatPredictionResponse(BaseModel):
    player_name: str
    opponent: str
    game_date: date
    home_game: bool

    predicted_points: float
    predicted_rebounds: float
    predicted_assists: float
    predicted_threes: float

    pts_last_5: float
    pts_last_10: float
    days_rest: int
    modeled_days_rest: int
    offseason_break: int
    warnings: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/players")
def get_players():
    data_file = (
        Path(__file__).resolve().parents[1]
        / "data/player_game_logs_2025_27.csv"
    )

    df = pd.read_csv(
        data_file,
        usecols=["PLAYER_NAME"]
    )

    players = sorted(
        df["PLAYER_NAME"].dropna().unique().tolist()
    )

    return {"players": players}


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    try:
        return predict_points(
            player_name=request.player_name,
            opponent=request.opponent,
            game_date=request.game_date.isoformat(),
            home_game=request.home_game,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/predict/v2", response_model=MultiStatPredictionResponse)
def predict_v2(request: PredictionRequest):
    try:
        return predict_multi_stats(
            player_name=request.player_name,
            opponent=request.opponent,
            game_date=request.game_date.isoformat(),
            home_game=request.home_game,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc
