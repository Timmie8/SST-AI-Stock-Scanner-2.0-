SST Streamlit Scanner
A Streamlit Community Cloud version of the SST Yahoo Finance scanner.
Files
- app.py — complete Streamlit application
- requirements.txt — Python dependencies
Deploy on Streamlit Community Cloud
1. Create a new GitHub repository, for example sst-streamlit-scanner.
2. Upload app.py and requirements.txt to the repository root.
3. Open https://share.streamlit.io/ and sign in with GitHub.
4. Select Create app.
5. Choose the repository, branch (usually main) and main file path app.py.
6. Click Deploy.
No API key is required for the current Yahoo Finance integration.
Notes
- This app is designed to run on Streamlit Community Cloud; do not use the previous FastAPI main.py deployment instructions.
- Yahoo Finance data can be delayed, incomplete, rate-limited or changed without notice.
- Scores are rule-based heuristics, not calibrated AI probabilities or guarantees of profit.
- Sentiment scoring is not included because price history alone cannot establish news or social sentiment.
- Backtest and paper-trade before using any signal with real capital.
