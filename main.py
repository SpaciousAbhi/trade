import time
import datetime
import requests
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_msg(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send message: {e}")

def get_formatted_time():
    now = datetime.datetime.now()
    return now.strftime('%I:%M %p')

def loop():
    sent_at = None
    while True:
        now = datetime.datetime.now()
        current_minute = now.minute
        current_second = now.second

        if current_minute % 15 in [13, 28, 43, 58] and current_second == 0:
            timestamp = now.strftime('%Y-%m-%d %H:%M')
            if sent_at != timestamp:
                msg = f"""⚠️ 15-minute candle closing soon
🕒 Time: {get_formatted_time()}
📌 Check chart & prepare trade"""
                send_msg(msg)
                sent_at = timestamp
                time.sleep(60)
        time.sleep(1)

if __name__ == "__main__":
    loop()
