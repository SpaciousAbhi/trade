import time
import datetime
import requests
import pytz
import sys

# ─── YOUR CREDENTIALS ─────────────────────────────────────────────────────────
BOT_TOKEN = "8011344779:AAHIw8vYSNB-wYmbRNBz0GiDKAfehRiIhQk"
CHAT_ID   = "1654334233"
# ──────────────────────────────────────────────────────────────────────────────

if not BOT_TOKEN or not CHAT_ID:
    print("ERROR: BOT_TOKEN and/or CHAT_ID not set.")
    sys.exit(1)

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
    return now_ist.strftime('%I:%M %p')  # e.g. 01:13 PM

def loop():
    last_sent = None
    while True:
        utc_now = datetime.datetime.utcnow()
        minute = utc_now.minute
        second = utc_now.second
        # Use UTC clock to determine trigger time, since Heroku runs on UTC
        if minute % 15 in (13, 28, 43, 58) and second == 0:
            timestamp = utc_now.strftime('%Y-%m-%d %H:%M')
            if timestamp != last_sent:
                msg = (
                    "⚠️ 15-minute candle closing soon\n"
                    f"🕒 Time: {get_formatted_time()}\n"
                    "📌 Check chart & prepare trade"
                )
                send_msg(msg)
                last_sent = timestamp
                time.sleep(60)  # avoid duplicates
        time.sleep(1)

if __name__ == "__main__":
    loop()
