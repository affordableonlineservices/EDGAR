"""
AI-Powered Options Trading Assistant — Streamlit Dashboard
Multi-ticker + Strategy-aware AI + Oil Futures Dashboard

Install:
    pip install streamlit yfinance groq pandas plotly --break-system-packages

Run:
    streamlit run dashboard.py

Then open: http://localhost:8501
"""
import streamlit as st

# PASSWORD PROTECTION
def check_password():
    """Returns `True` if the user had the correct password."""
    
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    
    if st.session_state.password_correct:
        return True
    
    with st.form("password_form"):
        password = st.text_input("Enter password:", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted and password == "Xx222032Ss27$$":
            st.session_state.password_correct = True
            st.rerun()
        elif submitted:
            st.error("❌ Incorrect password")
            return False
    
    return False

if not check_password():
    st.stop()

# REST OF YOUR DASHBOARD CODE GOES BELOW THIS LINE
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from groq import Groq

# Alpaca SDK — install with: pip install alpaca-trade-api --break-system-packages
try:
    import alpaca_trade_api as tradeapi
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Options Trader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] {
    background-color: #0a0a0f;
    color: #e2e8f0;
    font-family: 'JetBrains Mono', monospace;
}
.main .block-container { padding: 1.5rem 2rem; max-width: 1400px; }

.dash-header {
    font-family: 'Syne', sans-serif;
    font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;
    background: linear-gradient(135deg, #00ff88 0%, #00d4ff 50%, #7c3aed 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.dash-sub { font-size: 0.75rem; color: #475569; letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 1.5rem; }

/* Oil accent color: amber */
.oil-header {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem; font-weight: 800; letter-spacing: 0.05em;
    background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}

.metric-card {
    background: #0f1117; border: 1px solid #1e2535;
    border-radius: 8px; padding: 1.2rem 1.5rem;
    position: relative; overflow: hidden;
}
.metric-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #00ff88, #00d4ff);
}
.metric-card-oil::before {
    background: linear-gradient(90deg, #f59e0b, #ef4444) !important;
}
.metric-label { font-size: 0.65rem; color: #475569; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.4rem; }
.metric-value { font-family: 'Syne', sans-serif; font-size: 1.8rem; font-weight: 700; color: #f1f5f9; line-height: 1; }
.metric-delta-pos { color: #00ff88; font-size: 0.85rem; }
.metric-delta-neg { color: #ff4757; font-size: 0.85rem; }
.metric-delta-neu { color: #94a3b8; font-size: 0.85rem; }
.metric-delta-oil { color: #f59e0b; font-size: 0.85rem; }

.section-title {
    font-family: 'Syne', sans-serif; font-size: 0.7rem; font-weight: 700;
    letter-spacing: 0.2em; text-transform: uppercase; color: #00d4ff;
    border-bottom: 1px solid #1e2535; padding-bottom: 0.5rem; margin: 1.5rem 0 1rem 0;
}
.section-title-oil {
    font-family: 'Syne', sans-serif; font-size: 0.7rem; font-weight: 700;
    letter-spacing: 0.2em; text-transform: uppercase; color: #f59e0b;
    border-bottom: 1px solid #2a1f0a; padding-bottom: 0.5rem; margin: 1.5rem 0 1rem 0;
}

.verdict-go     { display:inline-block; background:rgba(0,255,136,0.12); border:1px solid #00ff88; color:#00ff88; font-family:'Syne',sans-serif; font-weight:800; font-size:1.4rem; padding:0.6rem 2rem; border-radius:6px; letter-spacing:0.1em; }
.verdict-nogo   { display:inline-block; background:rgba(255,71,87,0.12);  border:1px solid #ff4757; color:#ff4757; font-family:'Syne',sans-serif; font-weight:800; font-size:1.4rem; padding:0.6rem 2rem; border-radius:6px; letter-spacing:0.1em; }
.verdict-review { display:inline-block; background:rgba(251,191,36,0.12); border:1px solid #fbbf24; color:#fbbf24; font-family:'Syne',sans-serif; font-weight:800; font-size:1.4rem; padding:0.6rem 2rem; border-radius:6px; letter-spacing:0.1em; }

.mini-go     { background:rgba(0,255,136,0.12); border:1px solid #00ff8855; color:#00ff88; padding:0.1rem 0.5rem; border-radius:4px; font-size:0.7rem; font-weight:700; }
.mini-nogo   { background:rgba(255,71,87,0.12);  border:1px solid #ff475755; color:#ff4757; padding:0.1rem 0.5rem; border-radius:4px; font-size:0.7rem; font-weight:700; }
.mini-review { background:rgba(251,191,36,0.12); border:1px solid #fbbf2455; color:#fbbf24; padding:0.1rem 0.5rem; border-radius:4px; font-size:0.7rem; font-weight:700; }

.pill-bull { background:rgba(0,255,136,0.15); color:#00ff88; border:1px solid #00ff8844; padding:0.2rem 0.8rem; border-radius:20px; font-size:0.8rem; }
.pill-bear { background:rgba(255,71,87,0.15);  color:#ff4757; border:1px solid #ff475744; padding:0.2rem 0.8rem; border-radius:20px; font-size:0.8rem; }
.pill-neut { background:rgba(148,163,184,0.15); color:#94a3b8; border:1px solid #94a3b844; padding:0.2rem 0.8rem; border-radius:20px; font-size:0.8rem; }

.strategy-box { background:#0f1117; border:1px solid #7c3aed44; border-radius:8px; padding:1rem; border-left:3px solid #7c3aed; margin-bottom:0.5rem; }
.strategy-label { font-size:0.65rem; color:#7c3aed; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.4rem; }

.align-yes     { background:rgba(0,255,136,0.12); border:1px solid #00ff8844; color:#00ff88; padding:0.2rem 0.6rem; border-radius:4px; font-size:0.75rem; }
.align-no      { background:rgba(255,71,87,0.12);  border:1px solid #ff475744; color:#ff4757; padding:0.2rem 0.6rem; border-radius:4px; font-size:0.75rem; }
.align-partial { background:rgba(251,191,36,0.12); border:1px solid #fbbf2444; color:#fbbf24; padding:0.2rem 0.6rem; border-radius:4px; font-size:0.75rem; }

/* Oil instrument badge */
.oil-badge-futures { background:rgba(245,158,11,0.12); border:1px solid #f59e0b55; color:#f59e0b; padding:0.15rem 0.6rem; border-radius:4px; font-size:0.7rem; font-weight:700; }
.oil-badge-etf     { background:rgba(99,102,241,0.12);  border:1px solid #6366f155; color:#818cf8; padding:0.15rem 0.6rem; border-radius:4px; font-size:0.7rem; font-weight:700; }
.oil-badge-micro   { background:rgba(236,72,153,0.12);  border:1px solid #ec489955; color:#f472b6; padding:0.15rem 0.6rem; border-radius:4px; font-size:0.7rem; font-weight:700; }

/* Oil info card */
.oil-info-card {
    background: #0f1117;
    border: 1px solid #2a1f0a;
    border-left: 3px solid #f59e0b;
    border-radius: 8px; padding: 1rem 1.2rem; margin-bottom: 0.5rem;
}

/* Alpaca tab styles */
.alpaca-header {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem; font-weight: 800; letter-spacing: 0.05em;
    background: linear-gradient(135deg, #facc15 0%, #f97316 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.section-title-alpaca {
    font-family: 'Syne', sans-serif; font-size: 0.7rem; font-weight: 700;
    letter-spacing: 0.2em; text-transform: uppercase; color: #facc15;
    border-bottom: 1px solid #2a200a; padding-bottom: 0.5rem; margin: 1.5rem 0 1rem 0;
}
.alpaca-card {
    background: #0f1117; border: 1px solid #2a200a;
    border-left: 3px solid #facc15;
    border-radius: 8px; padding: 1rem 1.2rem; margin-bottom: 0.5rem;
}
.trade-buy  { background:rgba(0,255,136,0.10); border:1px solid #00ff8844; color:#00ff88; padding:0.15rem 0.6rem; border-radius:4px; font-size:0.7rem; font-weight:700; }
.trade-sell { background:rgba(255,71,87,0.10);  border:1px solid #ff475744; color:#ff4757; padding:0.15rem 0.6rem; border-radius:4px; font-size:0.7rem; font-weight:700; }
.trade-neutral { background:rgba(148,163,184,0.10); border:1px solid #94a3b844; color:#94a3b8; padding:0.15rem 0.6rem; border-radius:4px; font-size:0.7rem; font-weight:700; }
.pnl-pos { color: #00ff88; font-weight: 700; }
.pnl-neg { color: #ff4757; font-weight: 700; }
.pnl-neu { color: #94a3b8; }

.risk-item { background:rgba(255,71,87,0.06); border-left:2px solid #ff4757; padding:0.5rem 0.8rem; margin:0.4rem 0; font-size:0.82rem; color:#cbd5e1; border-radius:0 4px 4px 0; }
.warn-box  { background:rgba(251,191,36,0.08); border:1px solid #fbbf2444; border-radius:6px; padding:0.8rem 1rem; color:#fbbf24; font-size:0.8rem; margin:0.5rem 0; }
.info-box  { background:rgba(0,212,255,0.06); border:1px solid #00d4ff33; border-radius:6px; padding:0.8rem 1rem; color:#94a3b8; font-size:0.78rem; margin-top:1rem; }

section[data-testid="stSidebar"] { background: #0a0a0f; border-right: 1px solid #1e2535; }
section[data-testid="stSidebar"] .stTextInput input,
section[data-testid="stSidebar"] .stNumberInput input {
    background: #0f1117 !important; border: 1px solid #1e2535 !important;
    color: #e2e8f0 !important; font-family: 'JetBrains Mono', monospace !important;
}
section[data-testid="stSidebar"] .stTextArea textarea {
    background: #0f1117 !important; border: 1px solid #7c3aed55 !important;
    color: #e2e8f0 !important; font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}

.stButton > button {
    width: 100%; background: linear-gradient(135deg, #00ff88, #00d4ff) !important;
    color: #0a0a0f !important; font-family: 'Syne', sans-serif !important;
    font-weight: 800 !important; font-size: 1rem !important;
    letter-spacing: 0.05em !important; border: none !important;
    border-radius: 6px !important; padding: 0.7rem !important;
}
.stButton > button:hover { opacity: 0.85 !important; }
.stDataFrame { border: 1px solid #1e2535 !important; border-radius: 6px; }
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
GROQ_MODEL   = "llama-3.3-70b-versatile"
MAX_RISK_PCT = 0.05
MIN_VOLUME   = 100

# Oil instruments config
OIL_INSTRUMENTS = {
    "CL=F":  {"name": "WTI Crude Oil",         "type": "futures", "unit": "$/bbl", "has_options": False},
    "BZ=F":  {"name": "Brent Crude Oil",        "type": "futures", "unit": "$/bbl", "has_options": False},
    "MCL=F": {"name": "Micro WTI Crude (MCL)",  "type": "micro",   "unit": "$/bbl", "has_options": False},
    "USO":   {"name": "US Oil Fund ETF",         "type": "etf",     "unit": "$/share","has_options": True},
    "UCO":   {"name": "2x Crude Oil ETF",        "type": "etf",     "unit": "$/share","has_options": True},
}

SYSTEM_PROMPT = """
You are a professional options trading analyst. Analyze the provided market data and give a structured trade recommendation.

STRICT RULES — never violate these:
1. NEVER use N/A, missing, or null values as bullish or bearish signals. If data is missing, say "Insufficient data."
2. MAX LOSS for a long call or put = 100% of premium paid × 100 shares. Never define it any other way.
3. Always state the DTE (days to expiration) explicitly in your analysis.
4. If DTE < 7, flag the trade as HIGH RISK due to extreme theta decay and do not recommend it.
5. Base sentiment ONLY on: 5-day % change, 30-day % change, IV level, and volume/OI flow.
6. If a user strategy is provided, evaluate how well this trade aligns with it and explain specifically why.
7. Keep your reasoning concise and grounded in the data. No speculation.
8. Always output valid JSON only — no markdown, no preamble, no explanation outside the JSON.

OUTPUT FORMAT (strict JSON):
{
  "sentiment": "Bullish | Bearish | Neutral",
  "sentiment_reasoning": "...",
  "dte_warning": "...",
  "recommended_contract_type": "Call | Put",
  "recommended_strike": 000.0,
  "recommended_expiry": "YYYY-MM-DD",
  "entry_rationale": "...",
  "strategy_alignment": "Yes | No | Partial",
  "strategy_alignment_reasoning": "...",
  "key_risks": ["risk 1", "risk 2", "risk 3"],
  "verdict": "GO | NO-GO | REVIEW",
  "verdict_reasoning": "..."
}
"""

OIL_AI_PROMPT = """
You are an expert commodities and oil markets analyst. Analyze the provided crude oil market data across all instruments and give a concise market summary and trade outlook.

STRICT RULES:
1. Base analysis only on the data provided — no speculation.
2. Compare WTI vs Brent spread and explain what it signals.
3. If ETF options data is provided, give a specific options trade idea for USO or UCO.
4. If user strategy is provided, evaluate if an oil trade fits it.
5. Output valid JSON only — no markdown, no preamble.

OUTPUT FORMAT (strict JSON):
{
  "wti_outlook": "Bullish | Bearish | Neutral",
  "brent_outlook": "Bullish | Bearish | Neutral",
  "wti_brent_spread_analysis": "...",
  "mcl_note": "...",
  "market_summary": "...",
  "uso_trade_idea": "...",
  "uco_trade_idea": "...",
  "strategy_fit": "Yes | No | Partial | N/A",
  "strategy_fit_reasoning": "...",
  "key_risks": ["risk 1", "risk 2", "risk 3"],
  "overall_verdict": "GO | NO-GO | REVIEW",
  "verdict_reasoning": "..."
}
"""

# ─────────────────────────────────────────────
# FILE PERSISTENCE — Oil Strategy
# ─────────────────────────────────────────────
OIL_STRATEGY_FILE = Path(__file__).parent / "oil_strategy.txt"

def load_oil_strategy() -> str:
    try:
        if OIL_STRATEGY_FILE.exists():
            return OIL_STRATEGY_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""

def save_oil_strategy(text: str) -> bool:
    try:
        OIL_STRATEGY_FILE.write_text(text.strip(), encoding="utf-8")
        return True
    except Exception:
        return False

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "watchlist"           not in st.session_state: st.session_state.watchlist           = ["NVDA", "AAPL", "SPY"]
if "active_ticker"       not in st.session_state: st.session_state.active_ticker       = "NVDA"
if "results_cache"       not in st.session_state: st.session_state.results_cache       = {}
if "oil_data_cache"      not in st.session_state: st.session_state.oil_data_cache      = {}
if "oil_analysis"        not in st.session_state: st.session_state.oil_analysis        = None
if "oil_chat_history"    not in st.session_state: st.session_state.oil_chat_history    = []
if "oil_strategy_text"   not in st.session_state: st.session_state.oil_strategy_text   = load_oil_strategy()
if "alpaca_orders"       not in st.session_state: st.session_state.alpaca_orders       = None
if "alpaca_positions"    not in st.session_state: st.session_state.alpaca_positions    = None
if "alpaca_account"      not in st.session_state: st.session_state.alpaca_account      = None
if "alpaca_loaded"       not in st.session_state: st.session_state.alpaca_loaded       = False

# ─────────────────────────────────────────────
# DATA FUNCTIONS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_stock_data(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    hist  = stock.history(period="35d")
    if hist.empty or len(hist) < 2:
        raise ValueError(f"Insufficient price history for {ticker}")
    current       = hist["Close"].iloc[-1]
    price_5d_ago  = hist["Close"].iloc[-5]  if len(hist) >= 5  else None
    price_30d_ago = hist["Close"].iloc[-30] if len(hist) >= 30 else None
    change_5d     = round((current - price_5d_ago)  / price_5d_ago  * 100, 2) if price_5d_ago  else None
    change_30d    = round((current - price_30d_ago) / price_30d_ago * 100, 2) if price_30d_ago else None
    if change_5d is None or change_30d is None:
        raise ValueError("Could not compute price changes.")
    info = stock.info
    return {
        "ticker": ticker.upper(), "current_price": round(current, 2),
        "change_5d_pct": change_5d, "change_30d_pct": change_30d,
        "avg_volume": info.get("averageVolume","N/A"), "market_cap": info.get("marketCap","N/A"),
        "sector": info.get("sector","N/A"), "history": hist,
    }

@st.cache_data(ttl=300, show_spinner=False)
def get_oil_price_data(symbol: str) -> dict:
    """Fetch price data for any oil instrument (futures or ETF)."""
    ticker = yf.Ticker(symbol)
    hist   = ticker.history(period="35d")
    if hist.empty or len(hist) < 2:
        raise ValueError(f"No data for {symbol}")
    current       = hist["Close"].iloc[-1]
    price_5d_ago  = hist["Close"].iloc[-5]  if len(hist) >= 5  else None
    price_30d_ago = hist["Close"].iloc[-30] if len(hist) >= 30 else None
    change_5d     = round((current - price_5d_ago)  / price_5d_ago  * 100, 2) if price_5d_ago  else None
    change_30d    = round((current - price_30d_ago) / price_30d_ago * 100, 2) if price_30d_ago else None
    return {
        "symbol":         symbol,
        "current_price":  round(current, 2),
        "change_5d_pct":  change_5d,
        "change_30d_pct": change_30d,
        "history":        hist,
    }

@st.cache_data(ttl=300, show_spinner=False)
def get_valid_expiries(ticker: str, min_dte: int, max_dte: int) -> list:
    stock = yf.Ticker(ticker)
    today = datetime.today().date()
    valid = []
    for exp in stock.options:
        exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
        dte = (exp_date - today).days
        if min_dte <= dte <= max_dte:
            valid.append({"expiry": exp, "dte": dte})
    return sorted(valid, key=lambda x: x["dte"])

@st.cache_data(ttl=300, show_spinner=False)
def get_options_data(ticker: str, expiry: str, current_price: float) -> dict:
    stock = yf.Ticker(ticker)
    chain = stock.option_chain(expiry)
    cols  = ["strike","lastPrice","bid","ask","impliedVolatility","delta","gamma","theta","volume","openInterest"]
    calls = chain.calls[[c for c in cols if c in chain.calls.columns]].copy()
    puts  = chain.puts[[c  for c in cols if c in chain.puts.columns]].copy()
    if "volume" in calls.columns:
        calls = calls[calls["volume"].fillna(0) > MIN_VOLUME]
        puts  = puts[puts["volume"].fillna(0)   > MIN_VOLUME]
    calls["dist"] = abs(calls["strike"] - current_price)
    puts["dist"]  = abs(puts["strike"]  - current_price)
    calls = calls.sort_values("dist").head(5).drop(columns="dist")
    puts  = puts.sort_values("dist").head(5).drop(columns="dist")
    return {"expiry": expiry, "top_calls": calls.fillna(0).to_dict("records"), "top_puts": puts.fillna(0).to_dict("records")}

def calculate_position(portfolio_size: float, premium: float) -> dict:
    max_risk = portfolio_size * MAX_RISK_PCT
    cost_per = round(premium * 100, 2)
    num      = max(1, int(max_risk / cost_per)) if cost_per > 0 else 1
    total    = round(num * cost_per, 2)
    return {
        "portfolio_size": portfolio_size, "max_risk_dollars": round(max_risk, 2),
        "premium_per_share": premium, "cost_per_contract": cost_per,
        "num_contracts": num, "total_cost": total, "max_loss": total,
        "profit_target_20pct": round(total * 0.20, 2),
        "profit_target_50pct": round(total * 0.50, 2),
    }

def run_ai_analysis(api_key: str, stock_data: dict, options_data: dict, dte: int, strategy: str) -> dict:
    client = Groq(api_key=api_key)
    sd = {k: v for k, v in stock_data.items() if k != "history"}
    strat_block = f"\nUSER STRATEGY:\n{strategy.strip()}\n" if strategy.strip() else "\nUSER STRATEGY: Not provided.\n"
    msg = f"""Analyze this options trade:
STOCK: {json.dumps(sd, indent=2)}
OPTIONS (expiry: {options_data['expiry']}, DTE: {dte}):
Calls: {json.dumps(options_data['top_calls'], indent=2)}
Puts:  {json.dumps(options_data['top_puts'], indent=2)}
{strat_block}"""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": msg}],
        temperature=0.2, max_tokens=1200,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw)

def run_oil_ai_analysis(api_key: str, oil_data: dict, strategy: str) -> dict:
    """Send all oil instrument data to Groq for a unified oil market analysis."""
    client = Groq(api_key=api_key)
    # Strip history objects before sending
    clean = {sym: {k: v for k, v in d.items() if k != "history"} for sym, d in oil_data.items()}
    strat_block = f"\nUSER STRATEGY:\n{strategy.strip()}\n" if strategy.strip() else "\nUSER STRATEGY: Not provided.\n"
    msg = f"""Analyze this crude oil market data:
{json.dumps(clean, indent=2)}
{strat_block}"""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "system", "content": OIL_AI_PROMPT}, {"role": "user", "content": msg}],
        temperature=0.2, max_tokens=1200,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw)

OIL_CHAT_SYSTEM_PROMPT = """
You are an expert crude oil and energy futures trading strategist. You help traders develop, refine, and evaluate oil futures trading strategies — specifically for WTI (CL), Brent (BZ), and Micro WTI (MCL) contracts.

STRICT RULES:
1. Base your analysis only on the market data and strategy context provided. Do not speculate.
2. When market data is available, reference specific prices, spreads, and % changes in your answers.
3. Be concise and actionable. No fluff.
4. If the user's strategy is provided, tailor every answer to align with or constructively challenge it.
5. Always flag relevant risks specific to futures trading (leverage, rollover, margin, contango/backwardation).
6. Never give generic answers — always ground your response in the oil market context provided.
7. Format your response in plain text. No JSON. No markdown headers.
"""

def run_oil_chat(api_key: str, user_message: str, chat_history: list,
                 oil_strategy: str, oil_data: dict) -> str:
    client = Groq(api_key=api_key)
    # Build context block from loaded oil data
    clean = {sym: {k: v for k, v in d.items() if k != "history"}
             for sym, d in oil_data.items() if d is not None} if oil_data else {}
    context_block = f"\nCURRENT OIL MARKET DATA:\n{json.dumps(clean, indent=2)}\n" if clean else "\nCURRENT OIL MARKET DATA: Not loaded yet.\n"
    strat_block   = f"\nUSER'S FUTURES STRATEGY:\n{oil_strategy.strip()}\n" if oil_strategy.strip() else "\nUSER'S FUTURES STRATEGY: Not provided.\n"

    messages = [{"role": "system", "content": OIL_CHAT_SYSTEM_PROMPT + context_block + strat_block}]
    for turn in chat_history[-8:]:  # keep last 8 turns for context
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=GROQ_MODEL, messages=messages, temperature=0.3, max_tokens=800,
    )
    return response.choices[0].message.content.strip()

# ─────────────────────────────────────────────
# ALPACA FUNCTIONS
# ─────────────────────────────────────────────
def get_alpaca_client(api_key: str, secret_key: str, paper: bool = True):
    base_url = "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"
    return tradeapi.REST(api_key, secret_key, base_url, api_version="v2")

def fetch_alpaca_data(api_key: str, secret_key: str, paper: bool, days_back: int = 90):
    """Fetch account, positions, and order history from Alpaca."""
    api = get_alpaca_client(api_key, secret_key, paper)

    # Account
    account = api.get_account()
    account_data = {
        "equity":          float(account.equity),
        "cash":            float(account.cash),
        "buying_power":    float(account.buying_power),
        "portfolio_value": float(account.portfolio_value),
        "pnl_today":       float(account.equity) - float(account.last_equity),
        "pnl_today_pct":   ((float(account.equity) - float(account.last_equity)) / float(account.last_equity) * 100)
                           if float(account.last_equity) > 0 else 0.0,
        "status":          account.status,
    }

    # Open positions
    positions = api.list_positions()
    position_rows = []
    for p in positions:
        unrealized_pnl = float(p.unrealized_pl)
        cost_basis     = float(p.cost_basis)
        pnl_pct        = (unrealized_pnl / cost_basis * 100) if cost_basis != 0 else 0.0
        position_rows.append({
            "Symbol":        p.symbol,
            "Qty":           float(p.qty),
            "Side":          p.side,
            "Avg Entry":     float(p.avg_entry_price),
            "Current Price": float(p.current_price),
            "Market Value":  float(p.market_value),
            "Unrealized P&L":unrealized_pnl,
            "P&L %":         round(pnl_pct, 2),
        })

    # Closed / filled orders
    after_dt = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    orders   = api.list_orders(status="filled", after=after_dt, limit=500, direction="desc")
    order_rows = []
    for o in orders:
        filled_qty   = float(o.filled_qty) if o.filled_qty else 0
        filled_price = float(o.filled_avg_price) if o.filled_avg_price else 0.0
        notional     = filled_qty * filled_price
        order_rows.append({
            "Date":          pd.to_datetime(o.filled_at).strftime("%Y-%m-%d %H:%M") if o.filled_at else "—",
            "Symbol":        o.symbol,
            "Side":          o.side.upper(),
            "Type":          o.order_type,
            "Qty":           filled_qty,
            "Filled Price":  filled_price,
            "Notional":      round(notional, 2),
            "Status":        o.status,
            "Order ID":      o.id[:8] + "…",
        })

    return account_data, position_rows, order_rows

def compute_pnl_summary(order_rows: list) -> dict:
    """Compute realized P&L by matching buys and sells per symbol (FIFO)."""
    df = pd.DataFrame(order_rows) if order_rows else pd.DataFrame()
    if df.empty:
        return {"realized_pnl": 0.0, "win_rate": 0.0, "total_trades": 0, "winners": 0, "losers": 0}

    # Group by symbol and compute simple round-trip P&L
    realized = 0.0
    winners = losers = 0
    buy_queues = {}  # symbol -> list of (qty, price)

    for _, row in df.sort_values("Date").iterrows():
        sym   = row["Symbol"]
        side  = row["Side"]
        qty   = float(row["Qty"])
        price = float(row["Filled Price"])

        if side == "BUY":
            buy_queues.setdefault(sym, []).append((qty, price))
        elif side == "SELL":
            remaining = qty
            while remaining > 0 and buy_queues.get(sym):
                b_qty, b_price = buy_queues[sym][0]
                matched = min(remaining, b_qty)
                pnl     = matched * (price - b_price)
                realized += pnl
                if pnl >= 0: winners += 1
                else:        losers  += 1
                remaining -= matched
                if matched >= b_qty:
                    buy_queues[sym].pop(0)
                else:
                    buy_queues[sym][0] = (b_qty - matched, b_price)

    total = winners + losers
    return {
        "realized_pnl": round(realized, 2),
        "win_rate":      round(winners / total * 100, 1) if total > 0 else 0.0,
        "total_trades":  total,
        "winners":       winners,
        "losers":        losers,
    }

# ─────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────
def price_chart(hist, ticker, color="#00d4ff", fill_color="rgba(0,212,255,0.05)"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines",
        line=dict(color=color, width=2), fill="tozeroy", fillcolor=fill_color, name=ticker))
    fig.update_layout(paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f",
        font=dict(family="JetBrains Mono", color="#475569", size=11),
        margin=dict(l=10,r=10,t=10,b=10), height=200,
        xaxis=dict(showgrid=False, showline=False, zeroline=False),
