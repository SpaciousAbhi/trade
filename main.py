import time
import datetime
import requests
import pytz
import sys

# ─── YOUR TELEGRAM CREDENTIALS ─────────────────────────────────────
BOT_TOKEN = "8011344779:AAHIw8vYSNB-wYmbRNBz0GiDKAfehRiIhQk"
CHAT_ID   = "1654334233"
# ──────────────────────────────────────────────────────────────────

FUTURES_PAIRS = ["btcusdt", "etcusdt"]
TIMEFRAME = "30m"
BINANCE_API = "https://fapi.binance.com"

def send_msg(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        r = requests.post(url, data=data)
        r.raise_for_status()
    except Exception as e:
        print(f"Failed to send message: {e}")

def get_formatted_time():
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    return now_ist.strftime('%I:%M %p')

def get_candles(symbol):
    url = f"{BINANCE_API}/fapi/v1/klines?symbol={symbol.upper()}&interval=30m&limit=3"
    try:
        res = requests.get(url)
        data = res.json()
        return [{
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4])
        } for c in data]
    except Exception as e:
        print(f"Error fetching candles for {symbol}: {e}")
        return []

def is_bullish_engulfing(prev, curr):
    return (
        prev["close"] < prev["open"] and
        curr["close"] > curr["open"] and
        curr["open"] < prev["close"] and
        curr["close"] > prev["open"]
    )

def is_bearish_engulfing(prev, curr):
    return (
        prev["close"] > prev["open"] and
        curr["close"] < curr["open"] and
        curr["open"] > prev["close"] and
        curr["close"] < prev["open"]
    )

def check_engulfing_patterns():
    for symbol in FUTURES_PAIRS:
        candles = get_candles(symbol)
        if len(candles) < 3:
            continue
        prev = candles[-2]
        curr = candles[-1]
        time_str = get_formatted_time()
        price = curr["close"]
        if is_bullish_engulfing(prev, curr):
            msg = f"""🟢 Bullish Engulfing Detected
Pair: {symbol.upper()}-PERP
TF: 30m
🕒 Time: {time_str}
📈 Price: {price} USDT"""
            send_msg(msg)
        elif is_bearish_engulfing(prev, curr):
            msg = f"""🔴 Bearish Engulfing Detected
Pair: {symbol.upper()}-PERP
TF: 30m
🕒 Time: {time_str}
📉 Price: {price} USDT"""
            send_msg(msg)

def loop():
    last_msg_time = None
    while True:
        now = datetime.datetime.utcnow()
        minute = now.minute
        second = now.second

        # ⏰ Pre-close alert at :25 and :55
        if minute in (25, 55) and second == 0:
            timestamp = now.strftime('%Y-%m-%d %H:%M')
            if timestamp != last_msg_time:
                msg = (
                    "⚠️ 30-minute candle closing soon\n"
                    f"🕒 Time: {get_formatted_time()}\n"
                    "📌 Check chart & prepare trade"
                )
                send_msg(msg)
                last_msg_time = timestamp
                time.sleep(60)

        # 🧠 Pattern check at every :00 and :30
        if minute in (0, 30) and second == 5:
            check_engulfing_patterns()
            time.sleep(5)

        time.sleep(1)

if __name__ == "__main__":
    loop()
