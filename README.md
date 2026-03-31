# FinanceFlow API

Fast, reliable stock market data API built with FastAPI + yfinance.
Built to compete with YH Finance on RapidAPI — faster latency, better pricing, cleaner responses.

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stock/price` | Real-time price + key stats |
| GET | `/stock/news` | Latest news articles |
| GET | `/stock/indicators` | SMA, EMA, RSI, MACD |
| GET | `/stock/options` | Options chain (calls + puts) |

---

## Run Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open: http://localhost:8000/docs

---

## Deploy to Render (Free)

1. Push this folder to a GitHub repo
2. Go to render.com → New Web Service
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Deploy → get your live URL

---

## List on RapidAPI

1. Go to rapidapi.com/provider
2. Add New API
3. Paste your Render URL as the base URL
4. Add each endpoint manually
5. Set pricing tiers:
   - Free: 500 req/month
   - Basic: $5.99 → 15,000 req/month
   - Pro: $19.99 → 75,000 req/month

---

## Caching

All endpoints cache responses for 60 seconds in memory.
This drops latency from ~2000ms to ~50ms for repeat requests.
Response includes `"cached": true/false` so you can verify.

---

## Example Responses

### /stock/price?ticker=AAPL
```json
{
  "ticker": "AAPL",
  "price": 189.30,
  "open": 188.50,
  "high": 190.10,
  "low": 187.80,
  "volume": 52341200,
  "market_cap": 2950000000000,
  "52w_high": 199.62,
  "52w_low": 164.08,
  "currency": "USD",
  "exchange": "NMS",
  "cached": false
}
```

### /stock/indicators?ticker=AAPL&period=3mo
```json
{
  "ticker": "AAPL",
  "period": "3mo",
  "current_price": 189.30,
  "sma_20": 186.50,
  "sma_50": 182.10,
  "ema_12": 188.20,
  "ema_26": 185.60,
  "macd": 2.60,
  "macd_signal": 2.60,
  "rsi": 58.4,
  "rsi_signal": "Neutral",
  "cached": false
}
```
