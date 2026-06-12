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

# ─────────────────────────────────────────────
# MOBILE CONFIG EXPANDER
# ─────────────────────────────────────────────
st.markdown("---")
with st.expander("⚙️  CONFIG SETTINGS", expanded=False):
    st.markdown('<div style="color:#00ff88;font-weight:bold;">Essential Settings</div>', unsafe_allow_html=True)
    groq_key_m = st.text_input("🔑 Groq API Key", type="password", key="groq_key_m")
    portfolio_m = st.text_input("💰 Portfolio Size", value="10000 USD", key="portfolio_m")
    min_dte_m = st.slider("Min DTE", 1, 60, 7, key="min_dte_m")
    max_dte_m = st.slider("Max DTE", 1, 365, 45, key="max_dte_m")
    st.markdown('<div style="color:#facc15;font-size:0.85rem;margin-top:1rem;">Alpaca (Optional)</div>', unsafe_allow_html=True)
    alpaca_key_m = st.text_input("Alpaca API Key", type="password", key="alpaca_key_m")
    alpaca_secret_m = st.text_input("Alpaca Secret", type="password", key="alpaca_secret_m")
st.markdown("---")


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
        yaxis=dict(showgrid=True, gridcolor="#1e2535", zeroline=False), showlegend=False)
    return fig

def multi_oil_chart(oil_data_dict: dict) -> go.Figure:
    """Overlay WTI, Brent, MCL on one normalized chart (indexed to 100)."""
    colors = {"CL=F": "#f59e0b", "BZ=F": "#ef4444", "MCL=F": "#f472b6", "USO": "#818cf8", "UCO": "#34d399"}
    fig    = go.Figure()
    for sym, data in oil_data_dict.items():
        if data is None: continue
        hist = data.get("history")
        if hist is None or hist.empty: continue
        base  = hist["Close"].iloc[0]
        norm  = (hist["Close"] / base) * 100
        label = OIL_INSTRUMENTS.get(sym, {}).get("name", sym)
        fig.add_trace(go.Scatter(
            x=hist.index, y=norm, mode="lines", name=label,
            line=dict(color=colors.get(sym, "#94a3b8"), width=2),
        ))
    fig.add_hline(y=100, line_dash="dot", line_color="#1e2535", line_width=1)
    fig.update_layout(
        paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f",
        font=dict(family="JetBrains Mono", color="#475569", size=11),
        margin=dict(l=10,r=10,t=30,b=10), height=280,
        xaxis=dict(showgrid=False, showline=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#1e2535", zeroline=False, title="Indexed (base=100)"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8", size=10)),
        title=dict(text="35-Day Performance — All Oil Instruments (Indexed)", font=dict(color="#475569", size=11), x=0.01),
    )
    return fig

def options_chart(calls, puts, current_price):
    if not calls and not puts: return None
    fig = go.Figure()
    if calls:
        df_c   = pd.DataFrame(calls)
        oi_col = "openInterest" if "openInterest" in df_c.columns else "volume"
        fig.add_trace(go.Bar(x=df_c["strike"], y=df_c[oi_col], name="Calls OI", marker_color="rgba(0,255,136,0.7)"))
    if puts:
        df_p   = pd.DataFrame(puts)
        oi_col = "openInterest" if "openInterest" in df_p.columns else "volume"
        fig.add_trace(go.Bar(x=df_p["strike"], y=df_p[oi_col], name="Puts OI",  marker_color="rgba(255,71,87,0.7)"))
    fig.add_vline(x=current_price, line_dash="dot", line_color="#fbbf24", line_width=1.5,
                  annotation_text=f"  ${current_price}", annotation_font_color="#fbbf24", annotation_font_size=10)
    fig.update_layout(paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f",
        font=dict(family="JetBrains Mono", color="#475569", size=10),
        margin=dict(l=10,r=10,t=10,b=10), height=220, barmode="group", showlegend=True,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8", size=10)),
        xaxis=dict(showgrid=False, title="Strike"),
        yaxis=dict(showgrid=True, gridcolor="#1e2535", title="Open Interest"))
    return fig

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="dash-header" style="font-size:1.3rem;">⚡ CONFIG</div>', unsafe_allow_html=True)

    groq_key  = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    portfolio = st.number_input("Portfolio Size ($)", value=10000, step=1000, min_value=1000)
    min_dte   = st.slider("Min DTE", min_value=1, max_value=30,  value=7)
    max_dte   = st.slider("Max DTE", min_value=7, max_value=120, value=45)

    # ── Alpaca credentials ────────────────────
    st.markdown('<div style="height:0.6rem"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.65rem; color:#facc15; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.4rem;">🦙 Alpaca Credentials</div>', unsafe_allow_html=True)
    alpaca_key    = st.text_input("Alpaca API Key",    type="password", placeholder="PK…", key="alpaca_key_input")
    alpaca_secret = st.text_input("Alpaca Secret Key", type="password", placeholder="…",   key="alpaca_secret_input")
    alpaca_paper  = st.checkbox("Paper Trading Account", value=True, key="alpaca_paper_chk")
    alpaca_days   = st.slider("History (days)", min_value=7, max_value=365, value=90, key="alpaca_days_slider")

    st.markdown('<div style="height:0.6rem"></div>', unsafe_allow_html=True)
    st.markdown('<div class="strategy-label">📋 My Trading Strategy</div>', unsafe_allow_html=True)
    strategy = st.text_area(
        label="strategy_input", label_visibility="collapsed",
        placeholder=(
            "Describe your strategy so the AI can align its advice...\n\n"
            "Examples:\n"
            "• I buy calls when RSI > 60 and price is above 20 EMA\n"
            "• I sell covered calls on stocks I already own\n"
            "• I trade momentum breakouts, 2–3 week holds\n"
            "• I prefer low IV, buy before earnings\n"
            "• I only trade SPY/QQQ with defined risk spreads"
        ),
        height=140, key="strategy_text",
    )

    # ── Watchlist ────────────────────────────
    st.markdown('<div style="height:0.4rem"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.65rem; color:#00d4ff; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.4rem;">📌 Watchlist</div>', unsafe_allow_html=True)

    col_add, col_btn = st.columns([3, 1])
    with col_add:
        new_ticker = st.text_input("add_ticker", label_visibility="collapsed", placeholder="Add ticker...").upper().strip()
    with col_btn:
        st.markdown('<div style="height:0.35rem"></div>', unsafe_allow_html=True)
        if st.button("＋", key="add_btn"):
            if new_ticker and new_ticker not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_ticker)
                st.rerun()

    to_remove = None
    for t in st.session_state.watchlist:
        cached      = st.session_state.results_cache.get(t, {})
        verdict_str = ""
        if cached.get("analysis"):
            v         = cached["analysis"].get("verdict", "")
            mini_cls  = {"GO": "mini-go", "NO-GO": "mini-nogo"}.get(v, "mini-review")
            price_str = f'${cached["stock"]["current_price"]}' if cached.get("stock") else ""
            verdict_str = f'<span class="{mini_cls}">{v}</span> <span style="color:#475569;font-size:0.7rem;">{price_str}</span>'
        is_active    = (t == st.session_state.active_ticker)
        border_color = "#00d4ff" if is_active else "#1e2535"
        name_color   = "#00d4ff" if is_active else "#94a3b8"
        col_t, col_x = st.columns([5, 1])
        with col_t:
            st.markdown(f"""
            <div style="background:#0f1117; border:1px solid {border_color}; border-radius:6px;
                        padding:0.5rem 0.8rem; margin-bottom:0.3rem;">
                <span style="font-family:'Syne',sans-serif; font-weight:700; color:{name_color}; font-size:0.9rem;">{t}</span>
                <span style="float:right">{verdict_str}</span>
            </div>""", unsafe_allow_html=True)
            if st.button(f"Select {t}", key=f"sel_{t}", use_container_width=True):
                st.session_state.active_ticker = t
                st.rerun()
        with col_x:
            st.markdown('<div style="height:0.3rem"></div>', unsafe_allow_html=True)
            if st.button("✕", key=f"rm_{t}"):
                to_remove = t

    if to_remove:
        st.session_state.watchlist = [t for t in st.session_state.watchlist if t != to_remove]
        if to_remove in st.session_state.results_cache:
            del st.session_state.results_cache[to_remove]
        if st.session_state.active_ticker == to_remove:
            st.session_state.active_ticker = st.session_state.watchlist[0] if st.session_state.watchlist else ""
        st.rerun()

    st.markdown('<div style="height:0.4rem"></div>', unsafe_allow_html=True)
    col_run, col_all = st.columns(2)
    with col_run: run_one = st.button("▶ Analyze", help="Analyze active ticker")
    with col_all: run_all = st.button("⚡ All",    help="Analyze all tickers")

    st.markdown('<div class="info-box">⚠️ Not financial advice.<br>Options trading involves significant risk.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown('<div class="dash-header">AI OPTIONS TRADING ASSISTANT</div>', unsafe_allow_html=True)
st.markdown('<div class="dash-sub">Groq · yfinance · Multi-ticker · Strategy-aware AI · Oil Futures</div>', unsafe_allow_html=True)

if not groq_key and (run_one or run_all):
    st.error("⛔ Enter your Groq API key in the sidebar.")
    st.stop()

# ─────────────────────────────────────────────
# PIPELINE — Options
# ─────────────────────────────────────────────
def analyze_ticker(ticker: str):
    with st.spinner(f"Fetching {ticker} data..."):
        try:    stock_data = get_stock_data(ticker)
        except Exception as e:
            st.error(f"❌ {ticker} stock error: {e}"); return
    with st.spinner(f"Loading {ticker} options chain..."):
        try:
            expiries = get_valid_expiries(ticker, min_dte, max_dte)
            if not expiries:
                st.error(f"❌ {ticker}: No expiries found between {min_dte}–{max_dte} DTE."); return
            chosen       = expiries[0]
            options_data = get_options_data(ticker, chosen["expiry"], stock_data["current_price"])
        except Exception as e:
            st.error(f"❌ {ticker} options error: {e}"); return
    atm_call    = options_data["top_calls"][0] if options_data["top_calls"] else None
    atm_premium = atm_call.get("lastPrice") if atm_call else None
    if not atm_premium or atm_premium == 0: atm_premium = 1.00
    position = calculate_position(float(portfolio), float(atm_premium))
    with st.spinner(f"Running AI analysis for {ticker}..."):
        try:    analysis = run_ai_analysis(groq_key, stock_data, options_data, chosen["dte"], strategy)
        except Exception as e:
            st.error(f"❌ {ticker} AI error: {e}"); return
    st.session_state.results_cache[ticker] = {
        "stock": stock_data, "options": options_data,
        "position": position, "analysis": analysis, "chosen": chosen,
    }

if run_one and st.session_state.active_ticker:
    analyze_ticker(st.session_state.active_ticker)
    st.rerun()
if run_all:
    for t in st.session_state.watchlist:
        analyze_ticker(t)
    st.rerun()

# ─────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────
tab_options, tab_oil, tab_alpaca = st.tabs(["📈 Options Dashboard", "🛢️ Oil Futures", "🦙 Alpaca Trade History"])

# ══════════════════════════════════════════════
# TAB 1 — OPTIONS DASHBOARD (existing content)
# ══════════════════════════════════════════════
with tab_options:

    if not st.session_state.watchlist:
        st.markdown("""
        <div style="background:#0f1117; border:1px dashed #1e2535; border-radius:10px;
                    padding:3rem; text-align:center; color:#334155; font-size:0.9rem; margin-top:2rem;">
            <div style="font-size:3rem; margin-bottom:1rem;">📋</div>
            Add tickers to your watchlist in the sidebar, then click <strong style="color:#00d4ff">▶ Analyze</strong>
        </div>""", unsafe_allow_html=True)
    else:
        # Watchlist summary bar
        if st.session_state.results_cache:
            st.markdown('<div class="section-title">📌 Watchlist Summary</div>', unsafe_allow_html=True)
            summary_cols = st.columns(min(len(st.session_state.watchlist), 6))
            for i, t in enumerate(st.session_state.watchlist):
                cached = st.session_state.results_cache.get(t, {})
                with summary_cols[i % len(summary_cols)]:
                    if cached:
                        v       = cached["analysis"].get("verdict","?")
                        price   = cached["stock"]["current_price"]
                        chg5    = cached["stock"]["change_5d_pct"]
                        v_cls   = {"GO":"verdict-go","NO-GO":"verdict-nogo"}.get(v,"verdict-review")
                        c_cls   = "metric-delta-pos" if chg5 >= 0 else "metric-delta-neg"
                        c_txt   = f"+{chg5:.2f}%" if chg5 >= 0 else f"{chg5:.2f}%"
                        ab      = "border-color:#00d4ff !important;" if t == st.session_state.active_ticker else ""
                        st.markdown(f"""
                        <div class="metric-card" style="{ab}">
                            <div class="metric-label">{t}</div>
                            <div class="metric-value" style="font-size:1.4rem;">${price}</div>
                            <div class="{c_cls}" style="font-size:0.75rem;">{c_txt} (5d)</div>
                            <div style="margin-top:0.5rem"><span class="{v_cls}" style="font-size:0.8rem;padding:0.2rem 0.6rem;">{v}</span></div>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="metric-card" style="opacity:0.4;">
                            <div class="metric-label">{t}</div>
                            <div style="color:#334155; font-size:0.8rem; margin-top:0.5rem;">Not analyzed</div>
                        </div>""", unsafe_allow_html=True)

        # Active ticker detail
        active = st.session_state.active_ticker
        result = st.session_state.results_cache.get(active)

        if not result:
            st.markdown(f"""
            <div style="background:#0f1117; border:1px dashed #1e2535; border-radius:10px;
                        padding:2.5rem; text-align:center; color:#334155; font-size:0.9rem; margin-top:1rem;">
                <div style="font-size:2rem; margin-bottom:0.8rem;">📊</div>
                <strong style="color:#475569">{active}</strong> — click <strong style="color:#00d4ff">▶ Analyze</strong> to run
            </div>""", unsafe_allow_html=True)
        else:
            stock_data   = result["stock"]
            options_data = result["options"]
            position     = result["position"]
            analysis     = result["analysis"]
            chosen       = result["chosen"]

            st.markdown(f'<div class="section-title">📈 {active} — Detail View</div>', unsafe_allow_html=True)
            c1,c2,c3,c4,c5 = st.columns(5)

            def delta_class(val):
                if val is None: return "metric-delta-neu","–"
                return ("metric-delta-pos", f"+{val:.2f}%") if val >= 0 else ("metric-delta-neg", f"{val:.2f}%")

            with c1:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Current Price</div>
                    <div class="metric-value">${stock_data['current_price']}</div>
                    <div class="metric-delta-neu">{active}</div></div>""", unsafe_allow_html=True)
            cls5,txt5 = delta_class(stock_data["change_5d_pct"])
            with c2:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">5-Day Change</div>
                    <div class="metric-value">{abs(stock_data['change_5d_pct']):.2f}%</div>
                    <div class="{cls5}">{txt5}</div></div>""", unsafe_allow_html=True)
            cls30,txt30 = delta_class(stock_data["change_30d_pct"])
            with c3:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">30-Day Change</div>
                    <div class="metric-value">{abs(stock_data['change_30d_pct']):.2f}%</div>
                    <div class="{cls30}">{txt30}</div></div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Expiry / DTE</div>
                    <div class="metric-value" style="font-size:1.2rem;">{chosen['expiry']}</div>
                    <div class="metric-delta-neu">{chosen['dte']} days</div></div>""", unsafe_allow_html=True)
            verdict     = analysis.get("verdict","REVIEW")
            verdict_cls = {"GO":"verdict-go","NO-GO":"verdict-nogo"}.get(verdict,"verdict-review")
            with c5:
                st.markdown(f"""<div class="metric-card" style="display:flex;flex-direction:column;justify-content:center;align-items:center;">
                    <div class="metric-label">AI Verdict</div>
                    <div class="{verdict_cls}" style="margin-top:0.4rem">{verdict}</div></div>""", unsafe_allow_html=True)

            st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

            cl, cr = st.columns([3,2])
            with cl:
                st.markdown('<div class="section-title">📈 Price History (35d)</div>', unsafe_allow_html=True)
                st.plotly_chart(price_chart(stock_data["history"], active), use_container_width=True, config={"displayModeBar":False})
            with cr:
                st.markdown('<div class="section-title">📊 Options Open Interest</div>', unsafe_allow_html=True)
                oi_fig = options_chart(options_data["top_calls"], options_data["top_puts"], stock_data["current_price"])
                if oi_fig: st.plotly_chart(oi_fig, use_container_width=True, config={"displayModeBar":False})
                else: st.markdown('<div class="warn-box">No OI data available.</div>', unsafe_allow_html=True)

            col_ai, col_pos = st.columns([3,2])
            with col_ai:
                st.markdown('<div class="section-title">🤖 AI Analysis</div>', unsafe_allow_html=True)
                sent     = analysis.get("sentiment","Neutral")
                sent_cls = {"Bullish":"pill-bull","Bearish":"pill-bear"}.get(sent,"pill-neut")
                st.markdown(f'<span class="{sent_cls}">{sent}</span>', unsafe_allow_html=True)
                st.markdown(f'<div style="color:#94a3b8;font-size:0.82rem;margin:0.6rem 0 1rem 0;">{analysis.get("sentiment_reasoning","")}</div>', unsafe_allow_html=True)
                rec_type   = analysis.get("recommended_contract_type","N/A")
                rec_strike = analysis.get("recommended_strike","N/A")
                rec_exp    = analysis.get("recommended_expiry","N/A")
                type_color = "#00ff88" if rec_type=="Call" else "#ff4757"
                st.markdown(f"""
                <div style="background:#0f1117;border:1px solid #1e2535;border-radius:6px;padding:1rem;margin-bottom:0.8rem;">
                    <div style="font-size:0.65rem;color:#475569;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem;">Recommended Trade</div>
                    <span style="color:{type_color};font-family:'Syne',sans-serif;font-weight:700;font-size:1.1rem;">{rec_type}</span>
                    <span style="color:#94a3b8;font-size:0.85rem;"> · Strike <span style="color:#f1f5f9">${rec_strike}</span> · Exp <span style="color:#f1f5f9">{rec_exp}</span></span>
                    <div style="color:#64748b;font-size:0.78rem;margin-top:0.5rem;">{analysis.get('entry_rationale','')}</div>
                </div>""", unsafe_allow_html=True)
                strat_align  = analysis.get("strategy_alignment","")
                strat_reason = analysis.get("strategy_alignment_reasoning","")
                if strategy.strip() and strat_align:
                    align_cls = {"Yes":"align-yes","No":"align-no"}.get(strat_align,"align-partial")
                    st.markdown(f"""
                    <div class="strategy-box">
                        <div class="strategy-label">📋 Strategy Alignment</div>
                        <div style="display:flex;align-items:flex-start;gap:0.6rem;">
                            <span class="{align_cls}" style="white-space:nowrap;margin-top:0.1rem">{strat_align}</span>
                            <span style="color:#94a3b8;font-size:0.78rem;">{strat_reason}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)
                if analysis.get("dte_warning"):
                    st.markdown(f'<div class="warn-box">⚠️ {analysis["dte_warning"]}</div>', unsafe_allow_html=True)
                st.markdown('<div style="font-size:0.65rem;color:#475569;letter-spacing:0.1em;text-transform:uppercase;margin:0.8rem 0 0.4rem 0;">Key Risks</div>', unsafe_allow_html=True)
                for risk in analysis.get("key_risks",[]):
                    st.markdown(f'<div class="risk-item">⚡ {risk}</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="color:#94a3b8;font-size:0.8rem;margin-top:1rem;padding-top:0.8rem;border-top:1px solid #1e2535;">{analysis.get("verdict_reasoning","")}</div>', unsafe_allow_html=True)

            with col_pos:
                st.markdown('<div class="section-title">💰 Position Sizing</div>', unsafe_allow_html=True)
                def pos_row(label, value):
                    st.markdown(f"""<div style="display:flex;justify-content:space-between;padding:0.45rem 0;border-bottom:1px solid #1a1f2e;">
                        <span style="color:#475569;font-size:0.78rem;">{label}</span>
                        <span style="color:#e2e8f0;font-size:0.82rem;font-weight:600;">{value}</span></div>""", unsafe_allow_html=True)
                pos_row("Portfolio Size",  f"${position['portfolio_size']:,.2f}")
                pos_row("Max Risk (5%)",   f"${position['max_risk_dollars']:,.2f}")
                pos_row("Premium / Share", f"${position['premium_per_share']:.2f}")
                pos_row("Cost / Contract", f"${position['cost_per_contract']:.2f}")
                pos_row("# Contracts",     str(position["num_contracts"]))
                pos_row("Total Cost",      f"${position['total_cost']:,.2f}")
                st.markdown(f"""
                <div style="background:rgba(255,71,87,0.08);border:1px solid #ff475733;border-radius:6px;padding:0.7rem 1rem;margin:0.8rem 0;display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:#ff4757;font-size:0.78rem;">⛔ MAX LOSS</span>
                    <span style="color:#ff4757;font-family:'Syne',sans-serif;font-weight:700;font-size:1.1rem;">${position['max_loss']:,.2f}</span>
                </div>
                <div style="background:rgba(0,255,136,0.06);border:1px solid #00ff8833;border-radius:6px;padding:0.5rem 1rem;margin:0.4rem 0;display:flex;justify-content:space-between;">
                    <span style="color:#00ff88;font-size:0.78rem;">🎯 Target +20%</span>
                    <span style="color:#00ff88;font-weight:600;">${position['profit_target_20pct']:,.2f}</span>
                </div>
                <div style="background:rgba(0,255,136,0.06);border:1px solid #00ff8833;border-radius:6px;padding:0.5rem 1rem;margin:0.4rem 0;display:flex;justify-content:space-between;">
                    <span style="color:#00ff88;font-size:0.78rem;">🎯 Target +50%</span>
                    <span style="color:#00ff88;font-weight:600;">${position['profit_target_50pct']:,.2f}</span>
                </div>""", unsafe_allow_html=True)

            st.markdown('<div class="section-title">📋 Options Chain — Top Contracts</div>', unsafe_allow_html=True)
            tc, tp = st.tabs(["📞 Calls","📉 Puts"])
            display_cols = ["strike","lastPrice","bid","ask","impliedVolatility","delta","volume","openInterest"]
            def format_chain(data):
                df   = pd.DataFrame(data)
                cols = [c for c in display_cols if c in df.columns]
                df   = df[cols].copy()
                df.rename(columns={"strike":"Strike","lastPrice":"Last","bid":"Bid","ask":"Ask",
                                    "impliedVolatility":"IV","delta":"Delta","volume":"Volume","openInterest":"OI"}, inplace=True)
                if "IV" in df.columns:
                    df["IV"] = df["IV"].apply(lambda x: f"{x*100:.1f}%" if isinstance(x,float) else x)
                return df
            with tc:
                if options_data["top_calls"]: st.dataframe(format_chain(options_data["top_calls"]), use_container_width=True, hide_index=True)
                else: st.markdown('<div class="warn-box">No liquid call contracts found.</div>', unsafe_allow_html=True)
            with tp:
                if options_data["top_puts"]: st.dataframe(format_chain(options_data["top_puts"]), use_container_width=True, hide_index=True)
                else: st.markdown('<div class="warn-box">No liquid put contracts found.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 2 — OIL FUTURES DASHBOARD
# ══════════════════════════════════════════════
with tab_oil:

    st.markdown('<div class="oil-header">🛢️ Crude Oil Markets</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.72rem; color:#64748b; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:1.2rem;">WTI · Brent · Micro WTI (MCL) · USO · UCO</div>', unsafe_allow_html=True)

    # Instrument legend
    lcols = st.columns(5)
    badge_map = {"futures": "oil-badge-futures", "micro": "oil-badge-micro", "etf": "oil-badge-etf"}
    type_label = {"futures": "FUTURES", "micro": "MICRO", "etf": "ETF"}
    for i, (sym, info) in enumerate(OIL_INSTRUMENTS.items()):
        with lcols[i]:
            badge_cls = badge_map[info["type"]]
            st.markdown(f"""
            <div style="background:#0f1117;border:1px solid #2a1f0a;border-radius:6px;padding:0.6rem 0.8rem;margin-bottom:0.4rem;">
                <div style="font-family:'Syne',sans-serif;font-weight:700;color:#f1f5f9;font-size:0.85rem;">{sym}</div>
                <div style="color:#64748b;font-size:0.7rem;margin:0.15rem 0;">{info['name']}</div>
                <span class="{badge_cls}">{type_label[info['type']]}</span>
                {'<span style="margin-left:0.3rem;font-size:0.65rem;color:#475569;">options ✓</span>' if info['has_options'] else ''}
            </div>""", unsafe_allow_html=True)

    # Load oil data button
    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
    col_load, col_ai_btn, _ = st.columns([2, 2, 4])
    with col_load:
        load_oil = st.button("🔄 Load Oil Data", key="load_oil")
    with col_ai_btn:
        analyze_oil = st.button("🤖 AI Oil Analysis", key="analyze_oil",
                                help="Requires Groq API key and oil data loaded first")

    # ── Fetch oil data ──────────────────────
    if load_oil:
        with st.spinner("Fetching oil market data..."):
            for sym in OIL_INSTRUMENTS:
                try:
                    st.session_state.oil_data_cache[sym] = get_oil_price_data(sym)
                except Exception as e:
                    st.session_state.oil_data_cache[sym] = None
                    st.warning(f"⚠️ Could not load {sym}: {e}")
        st.rerun()

    # ── Run oil AI ──────────────────────────
    if analyze_oil:
        if not groq_key:
            st.error("⛔ Enter your Groq API key in the sidebar.")
        elif not st.session_state.oil_data_cache:
            st.error("⛔ Load oil data first.")
        else:
            with st.spinner("Running AI oil market analysis..."):
                try:
                    valid_data = {k: v for k, v in st.session_state.oil_data_cache.items() if v is not None}
                    st.session_state.oil_analysis = run_oil_ai_analysis(groq_key, valid_data, strategy)
                except Exception as e:
                    st.error(f"❌ Oil AI error: {e}")
            st.rerun()

    # ── Display oil price cards ─────────────
    if not st.session_state.oil_data_cache:
        st.markdown("""
        <div style="background:#0f1117;border:1px dashed #2a1f0a;border-radius:10px;
                    padding:3rem;text-align:center;color:#334155;font-size:0.9rem;margin-top:1rem;">
            <div style="font-size:3rem;margin-bottom:1rem;">🛢️</div>
            Click <strong style="color:#f59e0b">🔄 Load Oil Data</strong> to fetch live crude oil prices
        </div>""", unsafe_allow_html=True)
    else:
        # Price metric cards
        st.markdown('<div class="section-title-oil">💲 Live Prices</div>', unsafe_allow_html=True)
        price_cols = st.columns(5)
        for i, (sym, info) in enumerate(OIL_INSTRUMENTS.items()):
            data = st.session_state.oil_data_cache.get(sym)
            with price_cols[i]:
                if data:
                    chg5    = data.get("change_5d_pct")
                    chg30   = data.get("change_30d_pct")
                    c5_cls  = "metric-delta-pos" if (chg5 or 0) >= 0 else "metric-delta-neg"
                    c30_cls = "metric-delta-pos" if (chg30 or 0) >= 0 else "metric-delta-neg"
                    c5_txt  = f"+{chg5:.2f}%" if chg5 and chg5 >= 0 else f"{chg5:.2f}%" if chg5 else "N/A"
                    c30_txt = f"+{chg30:.2f}%" if chg30 and chg30 >= 0 else f"{chg30:.2f}%" if chg30 else "N/A"
                    st.markdown(f"""
                    <div class="metric-card metric-card-oil">
                        <div class="metric-label">{sym}</div>
                        <div class="metric-value" style="font-size:1.5rem;">${data['current_price']:.2f}</div>
                        <div class="{c5_cls}" style="font-size:0.75rem;">{c5_txt} 5d</div>
                        <div class="{c30_cls}" style="font-size:0.72rem;color:#64748b;">{c30_txt} 30d</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="metric-card" style="opacity:0.4;">
                        <div class="metric-label">{sym}</div>
                        <div style="color:#334155;font-size:0.8rem;margin-top:0.5rem;">Load failed</div>
                    </div>""", unsafe_allow_html=True)

        # WTI / Brent spread
        wti   = st.session_state.oil_data_cache.get("CL=F")
        brent = st.session_state.oil_data_cache.get("BZ=F")
        if wti and brent:
            spread     = round(brent["current_price"] - wti["current_price"], 2)
            sprd_color = "#f59e0b" if spread > 0 else "#ff4757"
            st.markdown(f"""
            <div style="background:#0f1117;border:1px solid #2a1f0a;border-radius:6px;padding:0.7rem 1.2rem;
                        margin:0.5rem 0;display:flex;align-items:center;gap:1.5rem;">
                <span style="color:#64748b;font-size:0.75rem;letter-spacing:0.1em;text-transform:uppercase;">Brent–WTI Spread</span>
                <span style="color:{sprd_color};font-family:'Syne',sans-serif;font-weight:700;font-size:1.2rem;">${spread:+.2f}/bbl</span>
                <span style="color:#475569;font-size:0.75rem;">{"Brent premium (normal contango)" if spread > 0 else "WTI premium (unusual backwardation)"}</span>
            </div>""", unsafe_allow_html=True)

        # Overlay price chart
        st.markdown('<div class="section-title-oil">📈 35-Day Performance — All Instruments (Indexed)</div>', unsafe_allow_html=True)
        valid_oil = {k: v for k, v in st.session_state.oil_data_cache.items() if v is not None}
        if valid_oil:
            st.plotly_chart(multi_oil_chart(valid_oil), use_container_width=True, config={"displayModeBar": False})

        # Individual charts
        st.markdown('<div class="section-title-oil">📊 Individual Price Charts</div>', unsafe_allow_html=True)
        chart_colors = {"CL=F":"#f59e0b","BZ=F":"#ef4444","MCL=F":"#f472b6","USO":"#818cf8","UCO":"#34d399"}
        fill_colors  = {"CL=F":"rgba(245,158,11,0.05)","BZ=F":"rgba(239,68,68,0.05)",
                        "MCL=F":"rgba(244,114,182,0.05)","USO":"rgba(129,140,248,0.05)","UCO":"rgba(52,211,153,0.05)"}
        chart_syms = [s for s in OIL_INSTRUMENTS if st.session_state.oil_data_cache.get(s)]
        for row_start in range(0, len(chart_syms), 3):
            row_syms = chart_syms[row_start:row_start+3]
            chart_cols = st.columns(len(row_syms))
            for j, sym in enumerate(row_syms):
                data = st.session_state.oil_data_cache[sym]
                with chart_cols[j]:
                    info = OIL_INSTRUMENTS[sym]
                    st.markdown(f'<div style="font-size:0.7rem;color:#64748b;margin-bottom:0.3rem;">{info["name"]}</div>', unsafe_allow_html=True)
                    fig = price_chart(data["history"], sym,
                                      color=chart_colors.get(sym,"#94a3b8"),
                                      fill_color=fill_colors.get(sym,"rgba(148,163,184,0.05)"))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        # USO / UCO options chains
        etf_syms = [s for s in ["USO","UCO"] if st.session_state.oil_data_cache.get(s)]
        if etf_syms:
            st.markdown('<div class="section-title-oil">📋 ETF Options Chains (USO / UCO)</div>', unsafe_allow_html=True)
            etf_tabs = st.tabs([f"{'📞' if i==0 else '📉'} {s}" for i, s in enumerate(etf_syms)])
            for i, sym in enumerate(etf_syms):
                with etf_tabs[i]:
                    current = st.session_state.oil_data_cache[sym]["current_price"]
                    with st.spinner(f"Loading {sym} options..."):
                        try:
                            exp_list = get_valid_expiries(sym, min_dte, max_dte)
                            if exp_list:
                                opt = get_options_data(sym, exp_list[0]["expiry"], current)
                                st.markdown(f'<div style="color:#64748b;font-size:0.75rem;margin-bottom:0.5rem;">Expiry: {opt["expiry"]} · {exp_list[0]["dte"]} DTE</div>', unsafe_allow_html=True)
                                oi_fig2 = options_chart(opt["top_calls"], opt["top_puts"], current)
                                if oi_fig2:
                                    st.plotly_chart(oi_fig2, use_container_width=True, config={"displayModeBar":False})
                                t_c, t_p = st.tabs(["Calls","Puts"])
                                def fmt(data):
                                    df = pd.DataFrame(data)
                                    cols = [c for c in ["strike","lastPrice","bid","ask","impliedVolatility","delta","volume","openInterest"] if c in df.columns]
                                    df = df[cols].copy()
                                    df.rename(columns={"strike":"Strike","lastPrice":"Last","bid":"Bid","ask":"Ask",
                                                        "impliedVolatility":"IV","delta":"Delta","volume":"Volume","openInterest":"OI"}, inplace=True)
                                    if "IV" in df.columns:
                                        df["IV"] = df["IV"].apply(lambda x: f"{x*100:.1f}%" if isinstance(x,float) else x)
                                    return df
                                with t_c:
                                    if opt["top_calls"]: st.dataframe(fmt(opt["top_calls"]), use_container_width=True, hide_index=True)
                                with t_p:
                                    if opt["top_puts"]: st.dataframe(fmt(opt["top_puts"]), use_container_width=True, hide_index=True)
                            else:
                                st.markdown(f'<div class="warn-box">No expiries found for {sym} in {min_dte}–{max_dte} DTE range.</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.markdown(f'<div class="warn-box">⚠️ Could not load {sym} options: {e}</div>', unsafe_allow_html=True)

        # AI Oil Analysis results
        if st.session_state.oil_analysis:
            oa = st.session_state.oil_analysis
            st.markdown('<div class="section-title-oil">🤖 AI Oil Market Analysis</div>', unsafe_allow_html=True)

            oa_cols = st.columns(3)
            def outlook_badge(o):
                cls = {"Bullish":"pill-bull","Bearish":"pill-bear"}.get(o,"pill-neut")
                return f'<span class="{cls}">{o}</span>'

            with oa_cols[0]:
                st.markdown(f"""<div class="oil-info-card">
                    <div class="metric-label">WTI Outlook</div>
                    {outlook_badge(oa.get('wti_outlook','Neutral'))}
                </div>""", unsafe_allow_html=True)
            with oa_cols[1]:
                st.markdown(f"""<div class="oil-info-card">
                    <div class="metric-label">Brent Outlook</div>
                    {outlook_badge(oa.get('brent_outlook','Neutral'))}
                </div>""", unsafe_allow_html=True)
            with oa_cols[2]:
                ov = oa.get("overall_verdict","REVIEW")
                ov_cls = {"GO":"verdict-go","NO-GO":"verdict-nogo"}.get(ov,"verdict-review")
                st.markdown(f"""<div class="oil-info-card" style="text-align:center;">
                    <div class="metric-label">Overall Verdict</div>
                    <span class="{ov_cls}" style="font-size:1.1rem;padding:0.3rem 1rem;">{ov}</span>
                </div>""", unsafe_allow_html=True)

            st.markdown(f"""
            <div class="oil-info-card" style="margin-top:0.5rem;">
                <div class="metric-label">Spread Analysis</div>
                <div style="color:#94a3b8;font-size:0.82rem;">{oa.get('wti_brent_spread_analysis','')}</div>
            </div>
            <div class="oil-info-card">
                <div class="metric-label">Market Summary</div>
                <div style="color:#94a3b8;font-size:0.82rem;">{oa.get('market_summary','')}</div>
            </div>""", unsafe_allow_html=True)

            if oa.get("mcl_note"):
                st.markdown(f"""<div class="oil-info-card">
                    <div class="metric-label">Micro WTI (MCL) Note</div>
                    <div style="color:#f472b6;font-size:0.82rem;">{oa.get('mcl_note','')}</div>
                </div>""", unsafe_allow_html=True)

            trade_col1, trade_col2 = st.columns(2)
            with trade_col1:
                if oa.get("uso_trade_idea"):
                    st.markdown(f"""<div class="oil-info-card">
                        <div class="metric-label">USO Trade Idea</div>
                        <div style="color:#818cf8;font-size:0.82rem;">{oa.get('uso_trade_idea','')}</div>
                    </div>""", unsafe_allow_html=True)
            with trade_col2:
                if oa.get("uco_trade_idea"):
                    st.markdown(f"""<div class="oil-info-card">
                        <div class="metric-label">UCO Trade Idea</div>
                        <div style="color:#34d399;font-size:0.82rem;">{oa.get('uco_trade_idea','')}</div>
                    </div>""", unsafe_allow_html=True)

            if strategy.strip() and oa.get("strategy_fit"):
                sf     = oa.get("strategy_fit","N/A")
                sf_cls = {"Yes":"align-yes","No":"align-no"}.get(sf,"align-partial")
                st.markdown(f"""
                <div class="strategy-box" style="margin-top:0.5rem;">
                    <div class="strategy-label">📋 Strategy Fit</div>
                    <div style="display:flex;align-items:flex-start;gap:0.6rem;">
                        <span class="{sf_cls}" style="white-space:nowrap">{sf}</span>
                        <span style="color:#94a3b8;font-size:0.78rem;">{oa.get('strategy_fit_reasoning','')}</span>
                    </div>
                </div>""", unsafe_allow_html=True)

            st.markdown('<div style="font-size:0.65rem;color:#475569;letter-spacing:0.1em;text-transform:uppercase;margin:0.8rem 0 0.4rem 0;">Key Risks</div>', unsafe_allow_html=True)
            for risk in oa.get("key_risks",[]):
                st.markdown(f'<div class="risk-item">⚡ {risk}</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="color:#94a3b8;font-size:0.8rem;margin-top:0.8rem;padding-top:0.8rem;border-top:1px solid #1e2535;">{oa.get("verdict_reasoning","")}</div>', unsafe_allow_html=True)

        # ── My Strategy + AI Chat ──────────────────
        st.markdown('<div class="section-title-oil">📋 My Futures Strategy & AI Chat</div>', unsafe_allow_html=True)

        chat_left, chat_right = st.columns([2, 3])

        with chat_left:
            st.markdown("""
            <div style="background:#0f1117;border:1px solid #2a1f0a;border-left:3px solid #f59e0b;
                        border-radius:8px;padding:1rem 1.2rem;margin-bottom:0.8rem;">
                <div style="font-size:0.65rem;color:#f59e0b;letter-spacing:0.12em;
                            text-transform:uppercase;margin-bottom:0.6rem;">📋 My Oil / Futures Strategy</div>
                <div style="font-size:0.75rem;color:#64748b;margin-bottom:0.5rem;">
                    Describe your approach — the AI will tailor every response to it.
                </div>
            </div>""", unsafe_allow_html=True)

            oil_strategy_input = st.text_area(
                label="oil_strategy_label", label_visibility="collapsed",
                placeholder=(
                    "Examples:\n"
                    "• I trade Micro WTI (MCL) to limit margin exposure\n"
                    "• I follow WTI/Brent spread to time entries\n"
                    "• I hold 1–3 days, no overnight risk on full CL\n"
                    "• I use USO puts as a hedge on my energy portfolio\n"
                    "• I watch EIA inventory reports every Wednesday"
                ),
                height=180,
                value=st.session_state.oil_strategy_text,
                key="oil_strategy_area",
            )

            col_save, col_clear = st.columns(2)
            with col_save:
                if st.button("💾 Save Strategy", key="save_oil_strat"):
                    st.session_state.oil_strategy_text = oil_strategy_input
                    if save_oil_strategy(oil_strategy_input):
                        st.success("✅ Strategy saved to disk!")
                    else:
                        st.warning("⚠️ Saved in session only — could not write to disk.")
            with col_clear:
                if st.button("🗑️ Clear Chat", key="clear_oil_chat"):
                    st.session_state.oil_chat_history = []
                    st.rerun()

            # Quick prompt chips
            st.markdown('<div style="font-size:0.65rem;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;margin:0.8rem 0 0.4rem 0;">⚡ Quick Questions</div>', unsafe_allow_html=True)
            quick_prompts = [
                "Is now a good time to go long MCL?",
                "What does the WTI/Brent spread tell me?",
                "What are the risks of holding MCL overnight?",
                "How does contango affect my futures trade?",
                "When is the next EIA inventory report?",
            ]
            for qp in quick_prompts:
                if st.button(qp, key=f"qp_{qp[:20]}"):
                    if not groq_key:
                        st.error("⛔ Enter your Groq API key in the sidebar.")
                    else:
                        st.session_state.oil_chat_history.append({"role": "user", "content": qp})
                        with st.spinner("Thinking..."):
                            try:
                                reply = run_oil_chat(
                                    groq_key, qp,
                                    st.session_state.oil_chat_history[:-1],
                                    st.session_state.oil_strategy_text,
                                    st.session_state.oil_data_cache,
                                )
                                st.session_state.oil_chat_history.append({"role": "assistant", "content": reply})
                            except Exception as e:
                                st.error(f"❌ AI error: {e}")
                    st.rerun()

        with chat_right:
            st.markdown("""
            <div style="background:#0f1117;border:1px solid #2a1f0a;border-left:3px solid #f59e0b;
                        border-radius:8px;padding:0.8rem 1.2rem;margin-bottom:0.8rem;">
                <div style="font-size:0.65rem;color:#f59e0b;letter-spacing:0.12em;text-transform:uppercase;">
                    🤖 AI Futures Strategy Chat
                </div>
                <div style="font-size:0.72rem;color:#475569;margin-top:0.3rem;">
                    Ask anything about oil futures, MCL trading, market conditions, or your strategy.
                    Load oil data first for market-aware answers.
                </div>
            </div>""", unsafe_allow_html=True)

            # Chat history display
            chat_container = st.container()
            with chat_container:
                if not st.session_state.oil_chat_history:
                    st.markdown("""
                    <div style="background:#0a0a0f;border:1px dashed #2a1f0a;border-radius:8px;
                                padding:2rem;text-align:center;color:#334155;font-size:0.85rem;">
                        <div style="font-size:2rem;margin-bottom:0.5rem;">🛢️</div>
                        Ask a question or pick a quick prompt to start chatting
                    </div>""", unsafe_allow_html=True)
                else:
                    for turn in st.session_state.oil_chat_history:
                        if turn["role"] == "user":
                            st.markdown(f"""
                            <div style="background:#0f1117;border:1px solid #1e2535;border-radius:8px;
                                        padding:0.7rem 1rem;margin:0.4rem 0;
                                        border-left:3px solid #00d4ff;">
                                <div style="font-size:0.6rem;color:#00d4ff;letter-spacing:0.1em;
                                            text-transform:uppercase;margin-bottom:0.3rem;">You</div>
                                <div style="color:#e2e8f0;font-size:0.82rem;">{turn["content"]}</div>
                            </div>""", unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="background:#0f1117;border:1px solid #2a1f0a;border-radius:8px;
                                        padding:0.7rem 1rem;margin:0.4rem 0;
                                        border-left:3px solid #f59e0b;">
                                <div style="font-size:0.6rem;color:#f59e0b;letter-spacing:0.1em;
                                            text-transform:uppercase;margin-bottom:0.3rem;">🤖 AI</div>
                                <div style="color:#cbd5e1;font-size:0.82rem;line-height:1.6;
                                            white-space:pre-wrap;">{turn["content"]}</div>
                            </div>""", unsafe_allow_html=True)

            # Chat input
            st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
            user_input = st.text_input(
                label="chat_input_label", label_visibility="collapsed",
                placeholder="Ask about MCL, WTI, your strategy, oil market conditions...",
                key="oil_chat_input",
            )
            send_cols = st.columns([5, 1])
            with send_cols[1]:
                send_btn = st.button("Send ➤", key="send_oil_chat")

            if send_btn and user_input.strip():
                if not groq_key:
                    st.error("⛔ Enter your Groq API key in the sidebar.")
                else:
                    st.session_state.oil_chat_history.append({"role": "user", "content": user_input.strip()})
                    with st.spinner("Thinking..."):
                        try:
                            reply = run_oil_chat(
                                groq_key,
                                user_input.strip(),
                                st.session_state.oil_chat_history[:-1],
                                st.session_state.oil_strategy_text,
                                st.session_state.oil_data_cache,
                            )
                            st.session_state.oil_chat_history.append({"role": "assistant", "content": reply})
                        except Exception as e:
                            st.error(f"❌ AI error: {e}")
                    st.rerun()

# ══════════════════════════════════════════════
# TAB 3 — ALPACA TRADE HISTORY
# ══════════════════════════════════════════════
with tab_alpaca:
    st.markdown('<div class="alpaca-header">🦙 ALPACA TRADE HISTORY</div>', unsafe_allow_html=True)
    st.markdown('<div class="dash-sub">Account · Open Positions · Filled Orders · P&L Summary</div>', unsafe_allow_html=True)

    if not ALPACA_AVAILABLE:
        st.error("⛔ `alpaca-trade-api` not installed. Run: `pip install alpaca-trade-api --break-system-packages`")
    elif not alpaca_key or not alpaca_secret:
        st.markdown("""
        <div style="background:#0f1117;border:1px dashed #2a200a;border-radius:10px;
                    padding:3rem;text-align:center;color:#475569;font-size:0.9rem;margin-top:1rem;">
            <div style="font-size:3rem;margin-bottom:1rem;">🦙</div>
            Enter your <strong style="color:#facc15">Alpaca API Key & Secret</strong> in the sidebar to load your trade history.
            <div style="font-size:0.75rem;margin-top:0.8rem;color:#334155;">
                Get keys at: alpaca.markets → Dashboard → API Keys
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        col_load, col_refresh = st.columns([2, 1])
        with col_load:
            load_btn = st.button("🔄 Load / Refresh Alpaca Data", key="load_alpaca")
        with col_refresh:
            if st.session_state.alpaca_loaded:
                st.markdown('<div style="color:#00ff88;font-size:0.8rem;padding-top:0.6rem;">✅ Data loaded</div>', unsafe_allow_html=True)

        if load_btn:
            with st.spinner("Connecting to Alpaca..."):
                try:
                    acct, positions, orders = fetch_alpaca_data(
                        alpaca_key, alpaca_secret, alpaca_paper, alpaca_days
                    )
                    st.session_state.alpaca_account   = acct
                    st.session_state.alpaca_positions = positions
                    st.session_state.alpaca_orders    = orders
                    st.session_state.alpaca_loaded    = True
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Alpaca connection error: {e}")

        if st.session_state.alpaca_loaded and st.session_state.alpaca_account:
            acct      = st.session_state.alpaca_account
            positions = st.session_state.alpaca_positions or []
            orders    = st.session_state.alpaca_orders    or []
            pnl_data  = compute_pnl_summary(orders)

            # ── Account Overview ──────────────────────────
            st.markdown('<div class="section-title-alpaca">💼 Account Overview</div>', unsafe_allow_html=True)
            a1, a2, a3, a4, a5 = st.columns(5)
            def _acct_card(col, label, value, delta_html=""):
                col.markdown(f"""
                <div class="metric-card" style="border-top:2px solid #facc15;">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value" style="font-size:1.4rem;">{value}</div>
                    {delta_html}
                </div>""", unsafe_allow_html=True)

            today_pnl     = acct["pnl_today"]
            today_pnl_pct = acct["pnl_today_pct"]
            pnl_cls       = "pnl-pos" if today_pnl >= 0 else "pnl-neg"
            pnl_sign      = "+" if today_pnl >= 0 else ""

            _acct_card(a1, "Portfolio Value",  f'${acct["portfolio_value"]:,.2f}')
            _acct_card(a2, "Equity",           f'${acct["equity"]:,.2f}')
            _acct_card(a3, "Cash",             f'${acct["cash"]:,.2f}')
            _acct_card(a4, "Buying Power",     f'${acct["buying_power"]:,.2f}')
            _acct_card(a5, "Today's P&L",
                       f'<span class="{pnl_cls}">{pnl_sign}${today_pnl:,.2f}</span>',
                       f'<div class="{pnl_cls}" style="font-size:0.8rem;">{pnl_sign}{today_pnl_pct:.2f}%</div>')

            # ── P&L Summary ───────────────────────────────
            st.markdown('<div class="section-title-alpaca">📊 Realized P&L Summary</div>', unsafe_allow_html=True)
            p1, p2, p3, p4, p5 = st.columns(5)

            rpnl      = pnl_data["realized_pnl"]
            rpnl_cls  = "pnl-pos" if rpnl >= 0 else "pnl-neg"
            rpnl_sign = "+" if rpnl >= 0 else ""

            p1.markdown(f"""
            <div class="alpaca-card">
                <div class="metric-label">Realized P&L ({alpaca_days}d)</div>
                <div class="metric-value" style="font-size:1.4rem;">
                    <span class="{rpnl_cls}">{rpnl_sign}${rpnl:,.2f}</span>
                </div>
            </div>""", unsafe_allow_html=True)
            p2.markdown(f"""
            <div class="alpaca-card">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value" style="font-size:1.4rem;">{pnl_data["win_rate"]}%</div>
            </div>""", unsafe_allow_html=True)
            p3.markdown(f"""
            <div class="alpaca-card">
                <div class="metric-label">Total Round-trips</div>
                <div class="metric-value" style="font-size:1.4rem;">{pnl_data["total_trades"]}</div>
            </div>""", unsafe_allow_html=True)
            p4.markdown(f"""
            <div class="alpaca-card">
                <div class="metric-label">Winners</div>
                <div class="metric-value" style="font-size:1.4rem; color:#00ff88;">{pnl_data["winners"]}</div>
            </div>""", unsafe_allow_html=True)
            p5.markdown(f"""
            <div class="alpaca-card">
                <div class="metric-label">Losers</div>
                <div class="metric-value" style="font-size:1.4rem; color:#ff4757;">{pnl_data["losers"]}</div>
            </div>""", unsafe_allow_html=True)

            # ── P&L chart ─────────────────────────────────
            if orders:
                df_orders = pd.DataFrame(orders)
                df_orders["Date"] = pd.to_datetime(df_orders["Date"], errors="coerce")
                df_daily = (
                    df_orders[df_orders["Side"] == "SELL"]
                    .groupby(df_orders["Date"].dt.date)["Notional"]
                    .sum()
                    .reset_index()
                    .rename(columns={"Date": "date", "Notional": "volume"})
                )
                if not df_daily.empty:
                    fig_vol = go.Figure()
                    fig_vol.add_trace(go.Bar(
                        x=df_daily["date"], y=df_daily["volume"],
                        marker_color="#facc15", opacity=0.75, name="Sell Volume"
                    ))
                    fig_vol.update_layout(
                        paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f",
                        font=dict(family="JetBrains Mono", color="#475569", size=11),
                        margin=dict(l=10, r=10, t=30, b=10), height=200,
                        xaxis=dict(showgrid=False, showline=False),
                        yaxis=dict(showgrid=True, gridcolor="#1e2535", title="Notional ($)"),
                        showlegend=False,
                        title=dict(text="Daily Sell Volume", font=dict(color="#facc15", size=11), x=0.01),
                    )
                    st.plotly_chart(fig_vol, use_container_width=True)

            # ── Open Positions ────────────────────────────
            st.markdown('<div class="section-title-alpaca">📌 Open Positions</div>', unsafe_allow_html=True)
            if not positions:
                st.markdown('<div style="color:#475569;font-size:0.85rem;padding:1rem 0;">No open positions.</div>', unsafe_allow_html=True)
            else:
                df_pos = pd.DataFrame(positions)

                # Color-code P&L column
                def _style_pnl(val):
                    if isinstance(val, (int, float)):
                        color = "#00ff88" if val >= 0 else "#ff4757"
                        return f"color: {color}; font-weight: 700"
                    return ""

                styled = df_pos.style\
                    .applymap(_style_pnl, subset=["Unrealized P&L", "P&L %"])\
                    .format({
                        "Avg Entry":     "${:.2f}",
                        "Current Price": "${:.2f}",
                        "Market Value":  "${:,.2f}",
                        "Unrealized P&L":"${:+,.2f}",
                        "P&L %":         "{:+.2f}%",
                        "Qty":           "{:.4g}",
                    })
                st.dataframe(styled, use_container_width=True, hide_index=True)

            # ── Filled Orders ─────────────────────────────
            st.markdown(f'<div class="section-title-alpaca">📋 Filled Orders (last {alpaca_days} days)</div>', unsafe_allow_html=True)
            if not orders:
                st.markdown('<div style="color:#475569;font-size:0.85rem;padding:1rem 0;">No filled orders found.</div>', unsafe_allow_html=True)
            else:
                df_ord = pd.DataFrame(orders)

                # Filters row
                fc1, fc2, fc3 = st.columns([2, 2, 3])
                with fc1:
                    side_filter = st.selectbox("Side", ["ALL", "BUY", "SELL"], key="alpaca_side_filter")
                with fc2:
                    syms = ["ALL"] + sorted(df_ord["Symbol"].unique().tolist())
                    sym_filter = st.selectbox("Symbol", syms, key="alpaca_sym_filter")
                with fc3:
                    search_sym = st.text_input("Search symbol", placeholder="e.g. NVDA", key="alpaca_search").upper().strip()

                df_filtered = df_ord.copy()
                if side_filter != "ALL":
                    df_filtered = df_filtered[df_filtered["Side"] == side_filter]
                if sym_filter != "ALL":
                    df_filtered = df_filtered[df_filtered["Symbol"] == sym_filter]
                if search_sym:
                    df_filtered = df_filtered[df_filtered["Symbol"].str.contains(search_sym, na=False)]

                def _style_side(val):
                    if val == "BUY":  return "color: #00ff88; font-weight: 700"
                    if val == "SELL": return "color: #ff4757; font-weight: 700"
                    return ""

                styled_ord = df_filtered.style\
                    .applymap(_style_side, subset=["Side"])\
                    .format({
                        "Filled Price": "${:.4f}",
                        "Notional":     "${:,.2f}",
                        "Qty":          "{:.4g}",
                    })
                st.dataframe(styled_ord, use_container_width=True, hide_index=True)

                # Export
                csv_data = df_filtered.drop(columns=["Order ID"], errors="ignore").to_csv(index=False)
                st.download_button(
                    label="⬇ Export Orders CSV",
                    data=csv_data,
                    file_name=f"alpaca_orders_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="export_alpaca_csv",
                )

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;color:#1e2535;font-size:0.7rem;margin-top:2rem;padding-top:1rem;border-top:1px solid #1a1f2e;">
    AI Options Trading Assistant · {datetime.now().strftime('%Y-%m-%d %H:%M')} · Not financial advice · Always do your own research
</div>""", unsafe_allow_html=True)

