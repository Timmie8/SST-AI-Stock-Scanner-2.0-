
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="SST AI Swing Scanner",
    page_icon="🐂",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background-color: #080b0d;
    color: #f3f5f6;
}
h1, h2, h3 {
    color: #00c27a;
}
div[data-testid="stMetric"] {
    background: #11191d;
    border: 1px solid #26343a;
    padding: 14px;
    border-radius: 10px;
}
.stButton > button {
    background: #00a86b;
    color: white;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

st.title("🐂 SST AI Swing Scanner")
st.caption("Yahoo Finance Data | 3–5 Day Swing Trading")

st.warning(
    "Scores are rule-based indicators, not validated "
    "AI predictions or guarantees of profit."
)


def safe_num(value):
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()

    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    rsi = rsi.mask((loss == 0) & (gain > 0), 100)
    rsi = rsi.mask((gain == 0) & (loss > 0), 0)

    return rsi


@st.cache_data(ttl=300)
def get_stock_data(symbol):
    ticker = yf.Ticker(symbol)

    hist = ticker.history(
        period="1y",
        interval="1d",
        auto_adjust=True
    )

    if hist is None or hist.empty or len(hist) < 60:
        raise ValueError("Insufficient Yahoo Finance data")

    hist = hist.dropna(subset=["Close"]).copy()

    close = hist["Close"]

    hist["EMA20"] = close.ewm(
        span=20, adjust=False
    ).mean()

    hist["EMA50"] = close.ewm(
        span=50, adjust=False
    ).mean()

    hist["EMA200"] = close.ewm(
        span=200, adjust=False
    ).mean()

    hist["RSI14"] = calculate_rsi(close)

    previous = close.shift(1)

    true_range = pd.concat([
        hist["High"] - hist["Low"],
        (hist["High"] - previous).abs(),
        (hist["Low"] - previous).abs()
    ], axis=1).max(axis=1)

    hist["ATR14"] = true_range.rolling(14).mean()
    hist["AVG_VOLUME"] = hist["Volume"].rolling(20).mean()

    try:
        info = ticker.get_info() or {}
    except Exception:
        info = {}

    return hist, info


def score_stock(hist, info):

    last = hist.iloc[-1]

    price = safe_num(last["Close"])
    ema20 = safe_num(last["EMA20"])
    ema50 = safe_num(last["EMA50"])
    ema200 = safe_num(last["EMA200"])
    rsi = safe_num(last["RSI14"])
    atr = safe_num(last["ATR14"])

    volume = safe_num(last["Volume"])
    avg_volume = safe_num(last["AVG_VOLUME"])

    rel_volume = (
        volume / avg_volume
        if avg_volume and avg_volume > 0
        else None
    )

    return5 = (
        (hist["Close"].iloc[-1] /
         hist["Close"].iloc[-6] - 1) * 100
    )

    return20 = (
        (hist["Close"].iloc[-1] /
         hist["Close"].iloc[-21] - 1) * 100
    )

    # TECHNICAL SCORE

    technical = 0

    technical += 2 if price > ema20 else 0
    technical += 2 if ema20 > ema50 else 0
    technical += 1.5 if ema50 > ema200 else 0

    if rsi is not None:
        if 50 <= rsi <= 70:
            technical += 1.5
        elif 45 <= rsi < 50:
            technical += 0.5

    technical += 1 if return5 > 0 else 0
    technical += 1 if return20 > 0 else 0

    if rel_volume is not None and rel_volume >= 1.2:
        technical += 1

    technical = min(10, technical)

    # SWING SCORE

    swing = 0

    swing += 2 if price > ema20 else 0
    swing += 2 if ema20 > ema50 else 0
    swing += 1.5 if return5 > 0 else 0
    swing += 1.5 if return20 > 0 else 0

    if rsi is not None and 50 <= rsi <= 68:
        swing += 1

    if rel_volume is not None and rel_volume >= 1:
        swing += 1

    swing += 1 if price > ema200 else 0

    swing = min(10, swing)

    # FUNDAMENTAL SCORE

    fundamentals = []

    fields = [
        ("revenueGrowth", lambda x: 5 + np.clip(x * 10, -5, 5)),
        ("earningsGrowth", lambda x: 5 + np.clip(x * 8, -5, 5)),
        ("grossMargins", lambda x: np.clip(x * 10, 0, 10)),
        ("operatingMargins", lambda x: np.clip(5 + x * 10, 0, 10)),
        ("debtToEquity", lambda x: np.clip(10 - x / 30, 0, 10)),
        ("currentRatio", lambda x: np.clip(x * 3, 0, 10))
    ]

    for field, calculation in fields:
        value = safe_num(info.get(field))
        if value is not None:
            fundamentals.append(float(calculation(value)))

    fundamental = (
        float(np.mean(fundamentals))
        if fundamentals else None
    )

    # OVERALL SCORE

    if fundamental is None:
        overall = technical * 0.375 + swing * 0.625
    else:
        overall = (
            technical * 0.30
            + swing * 0.50
            + fundamental * 0.20
        )

    # TRADING SIGNAL

    if (
        overall >= 7.5
        and swing >= 7
        and price > ema20 > ema50
    ):
        signal = "STRONG BUY"

    elif overall >= 6.5 and swing >= 6:
        signal = "BUY"

    elif overall >= 4.5:
        signal = "WATCH"

    else:
        signal = "AVOID"

    stop = price - 1.5 * atr if atr else None
    target = price + 3 * atr if atr else None

    return {
        "price": price,
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "rsi": rsi,
        "atr": atr,
        "rel_volume": rel_volume,
        "return5": return5,
        "return20": return20,
        "technical": technical,
        "swing": swing,
        "fundamental": fundamental,
        "overall": overall,
        "signal": signal,
        "stop": stop,
        "target": target
    }


# SIDEBAR

with st.sidebar:
    st.header("SST Scanner")

    ticker_input = st.text_area(
        "Enter stock tickers",
        "NVDA, SOFI, AVGO, ORCL, PLTR"
    )

    scan_button = st.button(
        "RUN SST SCAN",
        use_container_width=True
    )


# RUN SCANNER

if scan_button:

    symbols = list(dict.fromkeys(
        x.strip().upper()
        for x in ticker_input.replace("\n", ",").split(",")
        if x.strip()
    ))

    results = []
    errors = []

    progress = st.progress(0)

    for index, symbol in enumerate(symbols):

        try:
            hist, info = get_stock_data(symbol)
            result = score_stock(hist, info)

            result["ticker"] = symbol
            result["company"] = (
                info.get("shortName")
                or info.get("longName")
                or symbol
            )

            results.append(result)

        except Exception as error:
            errors.append(f"{symbol}: {error}")

        progress.progress((index + 1) / len(symbols))

    progress.empty()

    if results:

        results.sort(
            key=lambda x: x["overall"],
            reverse=True
        )

        st.subheader("SST Scan Results")

        rows = []

        for r in results:
            rows.append({
                "Ticker": r["ticker"],
                "Company": r["company"],
                "Signal": r["signal"],
                "Overall": round(r["overall"], 1),
                "Swing": round(r["swing"], 1),
                "Technical": round(r["technical"], 1),
                "Fundamental": (
                    round(r["fundamental"], 1)
                    if r["fundamental"] is not None
                    else "N/A"
                ),
                "Price": round(r["price"], 2),
                "RSI": (
                    round(r["rsi"], 1)
                    if r["rsi"] is not None
                    else "N/A"
                )
            })

        df = pd.DataFrame(rows)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        selected = st.selectbox(
            "Select stock for detailed analysis",
            [r["ticker"] for r in results]
        )

        r = next(
            x for x in results
            if x["ticker"] == selected
        )

        st.divider()

        st.subheader(
            f"{r['ticker']} - {r['company']}"
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("SIGNAL", r["signal"])
        c2.metric("OVERALL", f"{r['overall']:.1f}/10")
        c3.metric("SWING SCORE", f"{r['swing']:.1f}/10")
        c4.metric("TECHNICAL", f"{r['technical']:.1f}/10")

        st.subheader("Trade Setup")

        c1, c2, c3 = st.columns(3)

        c1.metric("Entry", f"${r['price']:.2f}")

        c2.metric(
            "Stop Loss",
            f"${r['stop']:.2f}" if r["stop"] else "N/A"
        )

        c3.metric(
            "Target",
            f"${r['target']:.2f}" if r["target"] else "N/A"
        )

        st.subheader("Technical Indicators")

        st.write(
            f"EMA20: ${r['ema20']:.2f} | "
            f"EMA50: ${r['ema50']:.2f} | "
            f"EMA200: ${r['ema200']:.2f}"
        )

        st.write(
            f"RSI: {r['rsi']:.2f}" if r["rsi"] is not None
            else "RSI: N/A"
        )

        st.write(
            f"5-day return: {r['return5']:.2f}%"
        )

        st.write(
            f"20-day return: {r['return20']:.2f}%"
        )

        st.write(
            f"Relative volume: {r['rel_volume']:.2f}x"
            if r["rel_volume"] is not None
            else "Relative volume: N/A"
        )

        st.caption(
            "Stop and target are indicative ATR-based levels, "
            "not personalized trade instructions."
        )

        st.info(
            "Sentiment analysis is not included. "
            "Yahoo price history alone cannot reliably measure "
            "news or social sentiment."
        )

        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="SST_Scanner_Results.csv",
            mime="text/csv"
        )

    else:
        st.error("No stock data could be retrieved.")

    if errors:
        with st.expander("Scan warnings"):
            for error in errors:
                st.write(error)

else:

    st.subheader("Welcome to SST AI Swing Scanner")

    st.write(
        "Enter your US stock tickers in the sidebar "
        "and click RUN SST SCAN."
    )

    st.markdown("""
    **Scanner components**

    - Technical score
    - Swing trading score
    - Fundamental score (when available)
    - BUY / STRONG BUY / WATCH / AVOID
    - Entry price
    - Stop loss
    - Target price
    - EMA20 / EMA50 / EMA200
    - RSI and relative volume
    """)

