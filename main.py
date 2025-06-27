# main.py — Real Binance Pattern Detection + Multi-User Bot

import json, time, requests, logging
from datetime import datetime
from pytz import timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler

# =====================
# CONFIG
# =====================
TOKEN = "8011344779:AAHIw8vYSNB-wYmbRNBz0GiDKAfehRiIhQk"
TIMEZONE = timezone("Asia/Kolkata")
STATE_FILE = "state.json"
USERS_FILE = "users.json"
BINANCE_URL = "https://fapi.binance.com/fapi/v1/klines"

# =====================
# GLOBAL STATE
# =====================
state = {"timeframe": "30m", "pairs": ["btcusdt", "ethusdt"]}
try:
    with open(STATE_FILE) as f:
        state = json.load(f)
except: pass

users = []
try:
    with open(USERS_FILE) as f:
        users = json.load(f)
except: pass

logging.basicConfig(level=logging.INFO)

# =====================
# HELPERS
# =====================
def save_state():
    with open(STATE_FILE, "w") as f: json.dump(state, f)

def save_users():
    with open(USERS_FILE, "w") as f: json.dump(users, f)

def get_time():
    return datetime.now(TIMEZONE).strftime("%I:%M %p")

def send_all(text):
    for uid in users:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={
            "chat_id": uid,
            "text": text,
            "parse_mode": "HTML"
        })

def send_chart(uid, caption, pair):
    chart_url = f"https://in.tradingview.com/symbols/{pair.upper()}P/"
    requests.get(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", params={
        "chat_id": uid,
        "photo": chart_url,
        "caption": caption,
        "parse_mode": "HTML"
    })

# =====================
# PATTERN DETECTION
# =====================
def fetch_candles(pair, tf="30m"):
    url = f"{BINANCE_URL}?symbol={pair.upper()}&interval={tf}&limit=3"
    data = requests.get(url).json()
    return [{"open": float(c[1]), "high": float(c[2]), "low": float(c[3]), "close": float(c[4])} for c in data]

def is_bullish(p,c): return p['close'] < p['open'] and c['close'] > c['open'] and c['open'] < p['close'] and c['close'] > p['open']
def is_bearish(p,c): return p['close'] > p['open'] and c['close'] < c['open'] and c['open'] > p['close'] and c['close'] < p['open']
def is_doji(c): return abs(c['close']-c['open']) <= 0.1*(c['high']-c['low'])
def is_hammer(c):
    body = abs(c['close'] - c['open'])
    lw = min(c['open'], c['close']) - c['low']
    uw = c['high'] - max(c['open'], c['close'])
    return lw >= 2 * body and uw < body

def check_patterns():
    for pair in state["pairs"]:
        try:
            data = fetch_candles(pair)
            p, c = data[-2], data[-1]
            now = get_time()
            price = c['close']
            caption = None
            if is_bullish(p, c):
                caption = f"🟢 Bullish Engulfing\n<b>{pair.upper()}</b> 30m\n🕒 {now} | 📈 {price}"
            elif is_bearish(p, c):
                caption = f"🔴 Bearish Engulfing\n<b>{pair.upper()}</b> 30m\n🕒 {now} | 📉 {price}"
            elif is_doji(c):
                caption = f"⚪ Doji\n<b>{pair.upper()}</b> 30m\n🕒 {now} | 💹 {price}"
            elif is_hammer(c):
                caption = f"🔨 Hammer\n<b>{pair.upper()}</b> 30m\n🕒 {now} | 💥 {price}"

            if caption:
                for uid in users:
                    send_chart(uid, caption, pair)
        except Exception as e:
            logging.error(f"Error checking {pair}: {e}")

# =====================
# TELEGRAM COMMANDS
# =====================
def start(update: Update, context: CallbackContext):
    uid = update.effective_chat.id
    if uid not in users:
        users.append(uid)
        save_users()
    kb = [[
        InlineKeyboardButton("📸 Screenshot BTC", callback_data='screenshot_btcusdt'),
        InlineKeyboardButton("➕ Add Pair", callback_data='add_pair')
    ],[
        InlineKeyboardButton("⏱ Set Timeframe", callback_data='set_time'),
        InlineKeyboardButton("📊 Summary", callback_data='summary')
    ]]
    update.message.reply_text("🤖 Bot active. Choose an option:", reply_markup=InlineKeyboardMarkup(kb))

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    cmd = query.data
    query.answer()
    if cmd == 'screenshot_btcusdt':
        send_chart(query.message.chat_id, "🖼 BTCUSDT Chart", "btcusdt")
    elif cmd == 'summary':
        send_msg("📊 Summary feature coming soon.")
    elif cmd == 'add_pair':
        send_msg("Use /addpair <symbol> to add pair.")
    elif cmd == 'set_time':
        send_msg("Use /settime <interval> e.g. 30m")

def addpair(update: Update, context: CallbackContext):
    if context.args:
        pair = context.args[0].lower()
        if pair not in state['pairs']:
            state['pairs'].append(pair)
            save_state()
            update.message.reply_text(f"✅ Tracking {pair.upper()}")
        else:
            update.message.reply_text(f"⚠️ {pair.upper()} already tracked")

def settime(update: Update, context: CallbackContext):
    if context.args:
        tf = context.args[0]
        state['timeframe'] = tf
        save_state()
        update.message.reply_text(f"⏱ Timeframe set to {tf}")

def list_users(update: Update, context: CallbackContext):
    update.message.reply_text(f"👥 Total Users: {len(users)}\n{chr(10).join(map(str, users))}")

# =====================
# MAIN LOOP
# =====================
def run_bot():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("addpair", addpair))
    dp.add_handler(CommandHandler("settime", settime))
    dp.add_handler(CommandHandler("users", list_users))
    dp.add_handler(CallbackQueryHandler(button))
    updater.start_polling()
    send_all(f"🔁 Bot restarted at {get_time()}")
    while True:
        now = datetime.now(TIMEZONE)
        if now.minute in [0,30]: check_patterns()
        if now.minute in [25,55]: send_all(f"⚠️ 30m candle closing soon\n🕒 {get_time()}\n📌 Check chart & prepare trade")
        time.sleep(60)

if __name__ == '__main__':
    run_bot()
