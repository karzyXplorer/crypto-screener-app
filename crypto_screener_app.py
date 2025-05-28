import streamlit as st
import requests
import pandas as pd
from ta.volatility import AverageTrueRange
import time

# Read secrets from .streamlit/secrets.toml
TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        st.error(f"Failed to send Telegram message: {e}")

def get_top_200_symbols():
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 200,
        'page': 1
    }
    response = requests.get(url, params=params)
    coins = response.json()
    symbols = [coin['symbol'].upper() + 'USDT' for coin in coins]
    return symbols

def fetch_binance_ohlcv(symbol, interval='15m', limit=100):
    url = f'https://api.binance.com/api/v3/klines'
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close',
            'volume', 'close_time', 'quote_asset_volume',
            'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore'
        ])
        df = df[['open', 'high', 'low', 'close']].astype(float)
        return df
    except Exception:
        return None

def check_candle_condition(df):
    if df is None or len(df) < 10:
        return False
    atr = AverageTrueRange(df['high'], df['low'], df['close'], window=8).average_true_range()
    last_atr = atr.iloc[-2]
    last_row = df.iloc[-1]
    candle_range = last_row['high'] - last_row['low']
    candle_body = abs(last_row['close'] - last_row['open'])
    return candle_range > 1.5 * last_atr and (candle_body / candle_range) > 0.7

# === STREAMLIT UI ===
st.title("🧠 Crypto Screener (15m + ATR + Telegram)")

if st.button("Run Screener"):
    with st.spinner("Scanning top 200 coins..."):
        symbols = get_top_200_symbols()
        matches = []

        for sym in symbols:
            df = fetch_binance_ohlcv(sym)
            if check_candle_condition(df):
                matches.append(sym)
            time.sleep(0.2)

        if matches:
            st.success(f"✅ Found {len(matches)} matches!")
            st.write(pd.DataFrame(matches, columns=["Matching Symbol"]))
            msg = "🚨 *Crypto Screener Matches (15m)*\n" + "\n".join(matches)
            send_telegram_message(msg)
        else:
            st.info("No matches found.")
            send_telegram_message("✅ Screener run completed — No matches found.")

