SST Yahoo Finance Stock Scanner 2.0
Files
`main.py`: FastAPI backend. Downloads Yahoo Finance history and calculates scores.
`index.html`: Dark SST-style scanner frontend.
`requirements.txt`: Python dependencies.
Run locally
Install Python 3.10+.
In this folder run:
`python -m venv .venv`
Activate the environment.
Windows PowerShell: `.venv\Scripts\Activate.ps1`
Install:
`pip install -r requirements.txt`
Start:
`uvicorn main:app --reload`
Open `http://127.0.0.1:8000`
Put `index.html` in a folder named `static` and add these lines to `main.py` before starting:
`from fastapi.staticfiles import StaticFiles`
`app.mount("/", StaticFiles(directory="static", html=True), name="static")`
(Alternatively serve index.html separately from the same origin and configure the API URL.)
Important
Yahoo Finance is accessed server-side with `yfinance`; it cannot run directly in a Weebly HTML embed.
For Weebly, deploy this Python backend to Render or another Python host, then change `fetch("/api/scan"...` in `index.html` to your deployed API URL. Configure CORS in `main.py` to allow only your Weebly domain.
This Yahoo-only implementation does NOT claim to calculate news/social sentiment. Sentiment is explicitly shown as not scored rather than fabricated.
Fundamental fields can be missing for some tickers. When they are missing, the overall score reweights technical and swing factors.
Yahoo Finance data may be delayed, incomplete, rate-limited, or subject to provider terms. Review applicable terms before commercial use.
Scores are heuristic research indicators, not probabilities of profit or investment advice.
