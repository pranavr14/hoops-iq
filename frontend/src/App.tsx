
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type PredictionResponse = {
  player_name: string
  team: string
  opponent: string
  game_date: string
  home_game: boolean
  game_id: string
  player_last_game_date: string
  predicted_points: number
  predicted_rebounds: number
  predicted_assists: number
  predicted_threes: number
  warnings: string[]
  detail?: string
}

type DataStatus = {
  stats_through: string
  model_validation_mae: number
  model_features: number
  schedule_available: boolean
}

const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

function formatDate(value: string) {
  return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}


function App() {
  const [player, setPlayer] = useState('LeBron James')
  const [players, setPlayers] = useState<string[]>([])
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null)
  const [dataStatus, setDataStatus] = useState<DataStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')


  useEffect(() => {
    async function loadPlayers() {
      try {
        const response = await fetch(
          `${apiUrl}/players`
        )

        if (!response.ok) {
          throw new Error('Failed to load players')
        }

        const data: { players: string[] } =
          await response.json()

        setPlayers(data.players)
      } catch (error) {
        console.error('Unable to load NBA players:', error)
      }
    }

    loadPlayers()

    async function loadDataStatus() {
      try {
        const response = await fetch(`${apiUrl}/status`)
        if (response.ok) {
          setDataStatus(await response.json() as DataStatus)
        }
      } catch (error) {
        console.error('Unable to load NBA data freshness:', error)
      }
    }

    loadDataStatus()
  }, [])

  async function handlePredict(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setPrediction(null)

    try {
      const response = await fetch(`${apiUrl}/predict/next`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          player_name: player.trim(),
        }),
      })

      const data = await response.json() as PredictionResponse

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : `Prediction request failed (${response.status})`
        )
      }



      const values = [
        data.predicted_points,
        data.predicted_rebounds,
        data.predicted_assists,
        data.predicted_threes,
      ]

      if (
        values.some(
          (value) =>
            typeof value !== 'number' ||
            !Number.isFinite(value)
        )
      ) {
        throw new Error(
          'The backend did not return valid multi-stat predictions.'
        )
      }

      setPrediction(data)

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to connect to the prediction server.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="navbar">
        <div className="logo">
          <span className="logo-ball">🏀</span>
          HOOPS<span className="logo-accent">IQ</span>
        </div>
        <span className="model-badge">Model v2 · NBA Analytics</span>
      </header>

      <main className="container">
        <section className="hero">
          <p className="eyebrow">DATA-DRIVEN BASKETBALL INTELLIGENCE</p>
          <h1>
            Predict the game.
            <br />
            <span>Back it with data.</span>
          </h1>
          <p className="hero-description">
            Choose a player. HoopsIQ finds their next scheduled game and
            projects points, rebounds, assists, and threes using updated game logs.
          </p>
        </section>

        <section className="dashboard">
          <div className="panel">
            <div className="panel-heading">
              <h2>NBA Player Stat Predictor</h2>
              <p>Type or select a player. HoopsIQ finds the next matchup automatically.</p>
            </div>

            <form onSubmit={handlePredict}>
              <div className="field">
                <label htmlFor="player">NBA Player</label>

                <input
                  id="player"
                  type="text"
                  list="nba-players"
                  value={player}
                  onChange={(e) => setPlayer(e.target.value)}
                  placeholder="Search NBA players..."
                  required
                  autoComplete="off"
                />

                <datalist id="nba-players">
                  {players.map((name) => (
                    <option key={name} value={name} />
                  ))}
                </datalist>

              </div>

              <button
                className="predict-button"
                type="submit"
                disabled={loading}
              >
                {loading ? 'Finding next matchup...' : 'Find Next Matchup & Predict →'}
              </button>
            </form>

            {error && <p className="error-message">{error}</p>}
          </div>

          <div className="panel result-panel">
            <div className="panel-heading">
              <h2>Prediction Result</h2>
              <p>HoopsIQ machine learning projection</p>
            </div>


            {prediction !== null ? (
              <div className="prediction-content prediction-content-v2">
                <p className="result-label">PROJECTED BOX SCORE</p>

                <div className="stat-grid">
                  <div className="stat-card stat-card-primary">
                    <span className="stat-label">POINTS</span>
                    <span className="stat-value">
                      {prediction.predicted_points.toFixed(1)}
                    </span>
                  </div>

                  <div className="stat-card">
                    <span className="stat-label">REBOUNDS</span>
                    <span className="stat-value">
                      {prediction.predicted_rebounds.toFixed(1)}
                    </span>
                  </div>

                  <div className="stat-card">
                    <span className="stat-label">ASSISTS</span>
                    <span className="stat-value">
                      {prediction.predicted_assists.toFixed(1)}
                    </span>
                  </div>

                  <div className="stat-card">
                    <span className="stat-label">3-POINTERS MADE</span>
                    <span className="stat-value">
                      {prediction.predicted_threes.toFixed(1)}
                    </span>
                  </div>
                </div>

                <p className="result-player">{prediction.player_name}</p>
                <p className="result-matchup">
                  {prediction.team} {prediction.home_game ? 'vs.' : '@'} {prediction.opponent}
                  {' · '}{prediction.home_game ? 'Home' : 'Away'}{' · '}{formatDate(prediction.game_date)}
                </p>
                {prediction.warnings.length > 0 && (
                  <ul className="prediction-warnings">
                    {prediction.warnings.map((warning) => <li key={warning}>{warning}</li>)}
                  </ul>
                )}
              </div>
            ) : (

              <div className="empty-result">
                <div className="basketball-icon">🏀</div>
                <h3>Your prediction awaits</h3>
                <p>
                  Enter a player and HoopsIQ will find their next scheduled game.
                </p>
              </div>
            )}
          </div>
        </section>

        <section className="metrics">
          <div className="metric">
            <p>MODEL TYPE</p>
            <h3>Linear Regression</h3>
          </div>
          <div className="metric">
            <p>VALIDATION MAE</p>
            <h3>{dataStatus ? `${dataStatus.model_validation_mae.toFixed(2)} Points` : 'Loading…'}</h3>
          </div>
          <div className="metric">
            <p>MODEL FEATURES</p>
            <h3>{dataStatus?.model_features ?? '—'}</h3>
          </div>
        </section>

        <footer className="footer">
          <p>
            HoopsIQ · NBA Player Performance Analytics
          </p>
          <p>
            {dataStatus
              ? `Game stats current through ${formatDate(dataStatus.stats_through)}. Data and models refresh automatically each day after completed games.`
              : 'Checking the latest NBA data…'}
            {' '}Predictions are estimates, not guarantees.
          </p>
        </footer>
      </main>
    </div>
  )
}

export default App
