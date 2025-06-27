# main.py (Fully Integrated Inline UI + Pattern Detection + Screenshot Bot)

import os
import time
import json
import datetime
import threading
import requests
import pytz
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from playwright.async_api import async_playwright

# =======================
# CONFIGURATION
# =======================
BOT_TOKEN = "8011344779:AAHIw8vYSNBz0GiDKAfehRiIhQk"
CHAT_ID = "1654334233"
STATE_FILE = "state.json"
ALERTS_FILE = "last_alerts.json"
TIMEZ = pytz.timezone("Asia/Kolkata")
BINANCE_API = "https://fapi.binance.com"
TV_BASE = "https://www.tradingview.com/chart/"

DEFAULT_STATE = {
    "timeframe": "30m",
    "pairs": ["btcusdt", "ethusdt"]
}

# =======================
# UTILITIES
# =======================
def load_state():
    if not os.path.exists(STATE_FILE): save_state(DEFAULT_STATE)
    with open(STATE_FILE, 'r') as f: return json.load(f)

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=2)

def get_time():
    return datetime.datetime.now(TIMEZ).strftime("%I:%M %p")

def send_msg(text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": text})

def save_alert(sym, msg):
    data = {}
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE) as f: data = json.load(f)
    data.setdefault(sym, []).append(msg)
    with open(ALERTS_FILE, 'w') as f: json.dump(data, f, indent=2)

def fetch_candles(sym, tf):
    url = f"{BINANCE_API}/fapi/v1/klines?symbol={sym.upper()}&interval={tf}&limit=3"
    res = requests.get(url).json()
    return [{"open":float(c[1]),"high":float(c[2]),"low":float(c[3]),"close":float(c[4])} for c in res]

def is_bullish(p,c): return p['close']<p['open'] and c['close']>c['open'] and c['open']<p['close'] and c['close']>p['open']
def is_bearish(p,c): return p['close']>p['open'] and c['close']<c['open'] and c['open']>p['close'] and c['close']<p['open']
def is_doji(c): return abs(c['close']-c['open']) <= 0.1*(c['high']-c['low'])
def is_hammer(c):
    body=abs(c['close']-c['open'])
    lw=min(c['open'],c['close'])-c['low']
    uw=c['high']-max(c['open'],c['close'])
    return lw>=2*body and uw<body

async def screenshot(symbol, caption):
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width":1280,"height":720})
        url = f"{TV_BASE}?symbol=BINANCE:{symbol.upper()}&interval=30"
        await pg.goto(url)
        await pg.wait_for_selector("canvas", timeout=15000)
        img = await pg.screenshot(type="png")
        await b.close()
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": (f"{symbol}.png", img, "image/png")})

def check_patterns():
    state = load_state()
    for sym in state['pairs']:
        tf = state['timeframe']
        data = fetch_candles(sym, tf)
        if len(data)<3: continue
        p,c = data[-2], data[-1]
        now, price = get_time(), c['close']
        if is_bullish(p,c):
            cap = f"🟢 Bullish Engulfing\n{sym.upper()} {tf}\n🕒 {now}\n📈 {price}"
            send_msg(cap); save_alert(sym, cap)
            asyncio.run(screenshot(sym, cap))
        elif is_bearish(p,c):
            cap = f"🔴 Bearish Engulfing\n{sym.upper()} {tf}\n🕒 {now}\n📉 {price}"
            send_msg(cap); save_alert(sym, cap)
            asyncio.run(screenshot(sym, cap))
        elif is_doji(c):
            cap = f"⚪ Doji\n{sym.upper()} {tf}\n🕒 {now}\n💹 {price}"
            send_msg(cap); save_alert(sym, cap)
            asyncio.run(screenshot(sym, cap))
        elif is_hammer(c):
            cap = f"🔨 Hammer\n{sym.upper()} {tf}\n🕒 {now}\n💥 {price}"
            send_msg(cap); save_alert(sym, cap)
            asyncio.run(screenshot(sym, cap))

# =======================
# TELEGRAM MENU + COMMANDS
# =======================
from telegram import BotCommand
from telegram.constants import ParseMode

# (same inline menu functions from before — unchanged)
# append below:

def run_loop():
    last = None
    while True:
        now = datetime.datetime.utcnow()
        m, s = now.minute, now.second
        if m in (25,55) and s == 0:
            k = now.strftime("%Y-%m-%d %H:%M")
            if k != last:
                send_msg(f"⚠️ 30m candle closing soon\n🕒 {get_time()}\n📌 Check trade")
                last = k
                time.sleep(60)
        if m in (0,30) and s == 5:
            check_patterns()
            time.sleep(10)
        time.sleep(1)

def main():
    threading.Thread(target=run_loop, daemon=True).start()
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("addpair", add_pair_command))
    dp.add_handler(CallbackQueryHandler(menu_handler))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
