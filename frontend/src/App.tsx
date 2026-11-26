
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

const teams = [
  'ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE',
  'DAL', 'DEN', 'DET', 'GSW', 'HOU', 'IND',
  'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN',
  'NOP', 'NYK', 'OKC', 'ORL', 'PHI', 'PHX',
  'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS',
]


type PredictionResponse = {
  predicted_points: number
  predicted_rebounds: number
  predicted_assists: number
  predicted_threes: number
  detail?: string
}


function App() {
  const [player, setPlayer] = useState('LeBron James')
  const [players, setPlayers] = useState<string[]>([])
  const [opponent, setOpponent] = useState('MIL')
  const [gameDate, setGameDate] = useState(() => {
    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')

    return `${year}-${month}-${day}`
  })
  const [homeGame, setHomeGame] = useState(true)
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')


  useEffect(() => {
    async function loadPlayers() {
      try {
        const response = await fetch(
          'http://127.0.0.1:8000/players'
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
  }, [])

  async function handlePredict(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setPrediction(null)

    try {
      const response = await fetch('http://127.0.0.1:8000/predict/v2', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          player_name: player.trim(),
          opponent,
          game_date: gameDate,
          home_game: homeGame,
        }),
      })

      const data: PredictionResponse = await response.json()

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
            NBA player scoring predictions powered by machine learning,
            historical performance, and matchup statistics.
          </p>
        </section>

        <section className="dashboard">
          <div className="panel">
            <div className="panel-heading">
              <h2>NBA Player Stat Predictor</h2>
              <p>Enter a matchup to predict points, rebounds, assists, and threes.</p>
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
                />

                <datalist id="nba-players">
                  {players.map((name) => (
                    <option key={name} value={name} />
                  ))}
                </datalist>

              </div>

              <div className="field-row">
                <div className="field">
                  <label htmlFor="opponent">Opponent</label>
                  <select
                    id="opponent"
                    value={opponent}
                    onChange={(e) => setOpponent(e.target.value)}
                  >
                    {teams.map((team) => (
                      <option key={team} value={team}>
                        {team}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="field">
                  <label htmlFor="date">Game Date</label>
                  <input
                    id="date"
                    type="date"
                    value={gameDate}
                    onChange={(e) => setGameDate(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="field">
                <label htmlFor="location">Game Location</label>
                <select
                  id="location"
                  value={homeGame ? 'home' : 'away'}
                  onChange={(e) =>
                    setHomeGame(e.target.value === 'home')
                  }
                >
                  <option value="home">Home Game</option>
                  <option value="away">Away Game</option>
                </select>
              </div>

              <button
                className="predict-button"
                type="submit"
                disabled={loading}
              >
                {loading ? 'Calculating...' : 'Predict Player Stats →'}
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

                <p className="result-player">{player}</p>
                <p className="result-matchup">
                  vs. {opponent} · {homeGame ? 'Home' : 'Away'}
                </p>
              </div>
            ) : (

              <div className="empty-result">
                <div className="basketball-icon">🏀</div>
                <h3>Your prediction awaits</h3>
                <p>
                  Select a player and matchup, then click
                  Predict Player Stats to see the model's projections.
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
            <h3>4.95 Points</h3>
          </div>
          <div className="metric">
            <p>MODEL FEATURES</p>
            <h3>43</h3>
          </div>
        </section>

        <footer className="footer">
          <p>
            HoopsIQ · NBA Player Performance Analytics
          </p>
          <p>
            Model v2 trained on 2025–26 and early 2026–27 NBA data.
            Historical predictions are not independent evaluations.
          </p>
        </footer>
      </main>
    </div>
  )
}

export default App
