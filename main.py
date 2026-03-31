from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import time
from typing import Optional
import pandas as pd

app = FastAPI(
    title="FinanceFlow API",
    description="Fast, reliable stock market data API. Cheaper and faster than the competition.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-Memory Cache ---
cache = {}
CACHE_TTL = 60  # seconds

def get_cached(key):
    if key in cache:
        data, timestamp = cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
    return None

def set_cache(key, data):
    cache[key] = (data, time.time())


# --- API Key Auth ---
VALID_API_KEYS = {"test-key-123", "rapidapi-proxy"}  # RapidAPI injects its own auth on top

def verify_key(x_api_key: Optional[str] = Header(None)):
    # When deployed on RapidAPI, they handle auth — this is for direct access
    if x_api_key and x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")


# --- Endpoints ---

@app.get("/", tags=["Info"])
def root():
    return {
        "name": "FinanceFlow API",
        "version": "1.0.0",
        "endpoints": ["/stock/price", "/stock/news", "/stock/indicators", "/stock/options"]
    }


@app.get("/stock/price", tags=["Stock"])
def get_stock_price(ticker: str):
    """
    Get real-time stock price and key stats for any ticker.
    Example: /stock/price?ticker=AAPL
    """
    ticker = ticker.upper()
    cache_key = f"price_{ticker}"
    cached = get_cached(cache_key)
    if cached:
        return {**cached, "cached": True}

    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info

        result = {
            "ticker": ticker,
            "price": round(info.last_price, 4) if info.last_price else None,
            "open": round(info.open, 4) if info.open else None,
            "high": round(info.day_high, 4) if info.day_high else None,
            "low": round(info.day_low, 4) if info.day_low else None,
            "volume": info.last_volume,
            "market_cap": info.market_cap,
            "52w_high": round(info.year_high, 4) if info.year_high else None,
            "52w_low": round(info.year_low, 4) if info.year_low else None,
            "currency": info.currency,
            "exchange": info.exchange,
            "cached": False
        }

        set_cache(cache_key, result)
        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch data for {ticker}: {str(e)}")


@app.get("/stock/news", tags=["News"])
def get_market_news(ticker: str, limit: int = 10):
    """
    Get latest news articles for a stock ticker.
    Example: /stock/news?ticker=TSLA&limit=5
    """
    ticker = ticker.upper()
    cache_key = f"news_{ticker}_{limit}"
    cached = get_cached(cache_key)
    if cached:
        return {**cached, "cached": True}

    try:
        stock = yf.Ticker(ticker)
        news = stock.news or []

        articles = []
        for item in news[:limit]:
            content = item.get("content", {})
            articles.append({
                "title": content.get("title"),
                "summary": content.get("summary"),
                "url": content.get("canonicalUrl", {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else None,
                "publisher": content.get("provider", {}).get("displayName") if isinstance(content.get("provider"), dict) else None,
                "published_at": content.get("pubDate"),
            })

        result = {
            "ticker": ticker,
            "count": len(articles),
            "articles": articles,
            "cached": False
        }

        set_cache(cache_key, result)
        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch news for {ticker}: {str(e)}")


@app.get("/stock/indicators", tags=["Technical"])
def get_technical_indicators(ticker: str, period: str = "3mo"):
    """
    Get technical indicators: SMA, EMA, RSI, MACD.
    Period options: 1mo, 3mo, 6mo, 1y
    Example: /stock/indicators?ticker=AAPL&period=3mo
    """
    ticker = ticker.upper()
    cache_key = f"indicators_{ticker}_{period}"
    cached = get_cached(cache_key)
    if cached:
        return {**cached, "cached": True}

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)

        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No historical data found for {ticker}")

        close = hist["Close"]

        # SMA
        sma_20 = round(float(close.rolling(window=20).mean().iloc[-1]), 4)
        sma_50 = round(float(close.rolling(window=50).mean().iloc[-1]), 4) if len(close) >= 50 else None

        # EMA
        ema_12 = round(float(close.ewm(span=12).mean().iloc[-1]), 4)
        ema_26 = round(float(close.ewm(span=26).mean().iloc[-1]), 4)

        # MACD
        macd_line = round(ema_12 - ema_26, 4)
        signal_line = round(float(pd.Series([macd_line]).ewm(span=9).mean().iloc[-1]), 4)

        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = round(float(100 - (100 / (1 + rs.iloc[-1]))), 2)

        result = {
            "ticker": ticker,
            "period": period,
            "current_price": round(float(close.iloc[-1]), 4),
            "sma_20": sma_20,
            "sma_50": sma_50,
            "ema_12": ema_12,
            "ema_26": ema_26,
            "macd": macd_line,
            "macd_signal": signal_line,
            "rsi": rsi,
            "rsi_signal": "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral",
            "cached": False
        }

        set_cache(cache_key, result)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not compute indicators for {ticker}: {str(e)}")


@app.get("/stock/options", tags=["Options"])
def get_options_data(ticker: str):
    """
    Get options chain data (calls and puts) for nearest expiry.
    Example: /stock/options?ticker=AAPL
    """
    ticker = ticker.upper()
    cache_key = f"options_{ticker}"
    cached = get_cached(cache_key)
    if cached:
        return {**cached, "cached": True}

    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options

        if not expirations:
            raise HTTPException(status_code=404, detail=f"No options data found for {ticker}")

        nearest_expiry = expirations[0]
        chain = stock.option_chain(nearest_expiry)

        def parse_options(df, limit=10):
            df = df.sort_values("volume", ascending=False).head(limit)
            return [
                {
                    "strike": row["strike"],
                    "last_price": row["lastPrice"],
                    "bid": row["bid"],
                    "ask": row["ask"],
                    "volume": int(row["volume"]) if not pd.isna(row["volume"]) else 0,
                    "open_interest": int(row["openInterest"]) if not pd.isna(row["openInterest"]) else 0,
                    "implied_volatility": round(float(row["impliedVolatility"]), 4) if not pd.isna(row["impliedVolatility"]) else None,
                    "in_the_money": bool(row["inTheMoney"]),
                }
                for _, row in df.iterrows()
            ]

        result = {
            "ticker": ticker,
            "expiry": nearest_expiry,
            "calls": parse_options(chain.calls),
            "puts": parse_options(chain.puts),
            "cached": False
        }

        set_cache(cache_key, result)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch options for {ticker}: {str(e)}")
