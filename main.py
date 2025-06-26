import time
import datetime
import requests
import pytz
import sys
import threading

# ─── YOUR TELEGRAM CREDENTIALS ─────────────────────────────────────
BOT_TOKEN = "8011344779:AAHIw8vYSNB-wYmbRNBz0GiDKAfehRiIhQk"
CHAT_ID   = "1654334233"
# ──────────────────────────────────────────────────────────────────

FUTURES_PAIRS = ["btcusdt", "etcusdt"]
TIMEFRAME = "30m"
BINANCE_API = "https://fapi.binance.com"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_msg(msg):
    url = f"{TELEGRAM_API}/sendMessage"
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
    url = f"{BINANCE_API}/fapi/v1/klines?symbol={symbol.upper()}&interval={TIMEFRAME}&limit=3"
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
TF: {TIMEFRAME}
🕒 Time: {time_str}
📈 Price: {price} USDT"""
            send_msg(msg)
        elif is_bearish_engulfing(prev, curr):
            msg = f"""🔴 Bearish Engulfing Detected
Pair: {symbol.upper()}-PERP
TF: {TIMEFRAME}
🕒 Time: {time_str}
📉 Price: {price} USDT"""
            send_msg(msg)

def handle_start_command():
    url = f"{TELEGRAM_API}/getUpdates"
    last_update_id = None
    while True:
        try:
            res = requests.get(url).json()
            if "result" in res:
                for update in res["result"]:
                    update_id = update["update_id"]
                    if update_id == last_update_id:
                        continue
                    last_update_id = update_id
                    if "message" in update and "text" in update["message"]:
                        msg = update["message"]["text"]
                        chat_id = str(update["message"]["chat"]["id"])
                        if msg == "/start" and chat_id == CHAT_ID:
                            reply = (
                                "✅ Bot is active.\n"
                                f"🔍 Monitoring Binance Futures pairs: {', '.join(FUTURES_PAIRS).upper()}\n"
                                f"🕒 Timeframe: {TIMEFRAME}\n"
                                "📡 Alerts: Engulfing + Pre-candle-close alerts"
                            )
                            send_msg(reply)
        except Exception as e:
            print(f"Command handler error: {e}")
        time.sleep(3)

def loop():
    last_msg_time = None
    while True:
        now = datetime.datetime.utcnow()
        minute = now.minute
        second = now.second

        # Pre-close alert at :25 and :55
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

        # Engulfing check on :00 and :30
        if minute in (0, 30) and second == 5:
            check_engulfing_patterns()
            time.sleep(5)

        time.sleep(1)

if __name__ == "__main__":
    send_msg(f"🔄 Bot has started.\n🕒 Time: {get_formatted_time()}\n✅ Engulfing detection + alerts active.")
    threading.Thread(target=handle_start_command, daemon=True).start()
    loop()
