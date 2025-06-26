import time
import datetime
import requests
import sys

# ─── YOUR CREDENTIALS ─────────────────────────────────────────────────────────
BOT_TOKEN = "7798265687:AAG1HqZBNYx4GBZZ5jC5cP3MTt8wsvtjQGE"
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
    now = datetime.datetime.now()
    return now.strftime('%I:%M %p')  # e.g. 02:43 PM

def loop():
    last_sent = None
    while True:
        now = datetime.datetime.now()
        minute = now.minute
        second = now.second
        # Trigger at :13, :28, :43, :58 exactly at second 0
        if minute % 15 in (13, 28, 43, 58) and second == 0:
            stamp = now.strftime('%Y-%m-%d %H:%M')
            if stamp != last_sent:
                msg = (
                    "⚠️ 15-minute candle closing soon\n"
                    f"🕒 Time: {get_formatted_time()}\n"
                    "📌 Check chart & prepare trade"
                )
                send_msg(msg)
                last_sent = stamp
                time.sleep(60)  # avoid duplicates
        time.sleep(1)

if __name__ == "__main__":
    loop()
