
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
import yfinance as yf
import pandas as pd
import numpy as np
import math

app = FastAPI(title="SST Yahoo Finance Stock Scanner", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your own domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScanRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, max_length=50)

def clamp(x, lo=0.0, hi=10.0):
    return float(max(lo, min(hi, x)))

def safe_float(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def analyze_ticker(ticker):
    ticker = ticker.strip().upper()
    if not ticker or len(ticker) > 15:
        raise ValueError("Invalid ticker")

    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y", interval="1d", auto_adjust=True)
    if hist is None or hist.empty or len(hist) < 60:
        raise ValueError("Insufficient Yahoo Finance price history")

    close = hist["Close"].dropna()
    high = hist["High"].reindex(close.index)
    low = hist["Low"].reindex(close.index)
    volume = hist["Volume"].reindex(close.index).fillna(0)

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    rsi = calculate_rsi(close)
    prev_close = close.shift(1)
    tr = pd.concat([(high-low), (high-prev_close).abs(), (low-prev_close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    last = safe_float(close.iloc[-1])
    e20, e50, e200 = safe_float(ema20.iloc[-1]), safe_float(ema50.iloc[-1]), safe_float(ema200.iloc[-1])
    rsi_now = safe_float(rsi.iloc[-1])
    atr_now = safe_float(atr.iloc[-1])
    avg_vol = safe_float(volume.tail(20).mean())
    rel_vol = (safe_float(volume.iloc[-1]) / avg_vol) if avg_vol and avg_vol > 0 else None
    change5 = safe_float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) >= 6 else None
    change20 = safe_float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) >= 21 else None

    # Technical score: trend alignment, RSI, recent momentum, and relative volume.
    tech = 5.0
    tech += 1.4 if last > e20 else -1.0
    tech += 1.4 if e20 > e50 else -1.0
    tech += 0.8 if e50 > e200 else -0.5
    if rsi_now is not None:
        tech += 0.8 if 52 <= rsi_now <= 68 else (0.2 if 45 <= rsi_now < 52 or 68 < rsi_now <= 74 else -0.8 if rsi_now < 40 or rsi_now > 80 else 0)
    if change5 is not None:
        tech += 0.5 if change5 > 1 else (-0.5 if change5 < -1 else 0)
    if rel_vol is not None:
        tech += 0.5 if rel_vol >= 1.5 and change5 and change5 > 0 else 0
    tech = round(clamp(tech), 1)

    # Swing score emphasizes 3-5 day trend continuation and manageable volatility.
    swing = 5.0
    swing += 1.2 if last > e20 else -1.0
    swing += 1.2 if e20 > e50 else -1.0
    swing += 0.8 if change5 is not None and change5 > 0 else -0.6
    swing += 0.8 if change20 is not None and change20 > 0 else -0.6
    if rsi_now is not None:
        swing += 0.6 if 50 <= rsi_now <= 70 else -0.5 if rsi_now < 40 or rsi_now > 78 else 0
    swing = round(clamp(swing), 1)

    # Fundamental score uses fields available from Yahoo Finance; missing data is not fabricated.
    info = {}
    try:
        info = stock.get_info() or {}
    except Exception:
        info = {}
    fund_components = []
    revenue_growth = safe_float(info.get("revenueGrowth"))
    earnings_growth = safe_float(info.get("earningsGrowth"))
    gross_margin = safe_float(info.get("grossMargins"))
    operating_margin = safe_float(info.get("operatingMargins"))
    debt_equity = safe_float(info.get("debtToEquity"))
    current_ratio = safe_float(info.get("currentRatio"))

    if revenue_growth is not None:
        fund_components.append(clamp(5 + revenue_growth * 10))
    if earnings_growth is not None:
        fund_components.append(clamp(5 + earnings_growth * 8))
    if gross_margin is not None:
        fund_components.append(clamp(gross_margin * 10))
    if operating_margin is not None:
        fund_components.append(clamp(5 + operating_margin * 10))
    if debt_equity is not None:
        fund_components.append(clamp(8 - debt_equity / 50))
    if current_ratio is not None:
        fund_components.append(clamp(current_ratio * 3))
    fund = round(float(np.mean(fund_components)), 1) if fund_components else None

    # Risk plan based on ATR. This is a calculation, not a guaranteed target.
    stop = round(last - 1.5 * atr_now, 2) if atr_now and atr_now > 0 else None
    target = round(last + 3.0 * atr_now, 2) if atr_now and atr_now > 0 else None
    rr = 2.0 if stop and target else None

    # Yahoo Finance does not provide a reliable news/social sentiment score here.
    # Do not invent an AI/sentiment score. The overall score renormalizes available factors.
    weighted = [(tech, 0.30), (swing, 0.50)]
    if fund is not None:
        weighted.append((fund, 0.20))
    else:
        # Reweight technical and swing scores when fundamentals are unavailable.
        weighted = [(tech, 0.375), (swing, 0.625)]
    total = round(sum(score * weight for score, weight in weighted), 1)

    if total >= 7.5 and swing >= 7 and last > e20 and e20 > e50:
        advice = "STRONG BUY"
    elif total >= 6.5 and swing >= 6:
        advice = "BUY"
    elif total >= 4.5:
        advice = "WATCH"
    else:
        advice = "AVOID"

    return {
        "ticker": ticker,
        "price": round(last, 2),
        "change_5d_pct": round(change5, 2) if change5 is not None else None,
        "change_20d_pct": round(change20, 2) if change20 is not None else None,
        "rsi14": round(rsi_now, 1) if rsi_now is not None else None,
        "relative_volume": round(rel_vol, 2) if rel_vol is not None else None,
        "ema20": round(e20, 2) if e20 is not None else None,
        "ema50": round(e50, 2) if e50 is not None else None,
        "ema200": round(e200, 2) if e200 is not None else None,
        "fundamental_score": fund,
        "sentiment_score": None,
        "technical_score": tech,
        "swing_score": swing,
        "total_score": total,
        "advice": advice,
        "entry": round(last, 2),
        "stop_loss": stop,
        "target_1": target,
        "risk_reward": "1:2.0" if rr else "N/A",
        "fundamentals_note": "Yahoo Finance fundamentals available" if fund is not None else "Fundamental data unavailable",
        "sentiment_note": "Not scored: Yahoo Finance price history alone cannot establish news/social sentiment",
        "data_date": str(close.index[-1].date()),
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/scan")
def scan(request: ScanRequest):
    results, errors = [], []
    for ticker in request.tickers:
        try:
            results.append(analyze_ticker(ticker))
        except Exception as exc:
            errors.append({"ticker": ticker.strip().upper(), "error": str(exc)})
    return {"results": results, "errors": errors}

app.mount("/", StaticFiles(directory="static", html=True), name="static")
