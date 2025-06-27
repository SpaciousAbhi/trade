import os
import sys
import time
import datetime
import requests
import pytz
import threading
import asyncio
from playwright.async_api import async_playwright

# ─── YOUR CREDENTIALS ────────────────────────────────────────────────────────
BOT_TOKEN = "8011344779:AAHIw8vYSNB-wYmbRNBz0GiDKAfehRiIhQk"
CHAT_ID   = "1654334233"
# ──────────────────────────────────────────────────────────────────────────────

# Bot config
FUTURES_PAIRS = ["btcusdt", "ethusdt"]
TIMEFRAME     = "30m"
BINANCE_API   = "https://fapi.binance.com"
TELEGRAM_API  = f"https://api.telegram.org/bot{BOT_TOKEN}"
TV_URL        = "https://www.tradingview.com/chart/"

def send_msg(text: str):
    requests.post(f"{TELEGRAM_API}/sendMessage", data={
        "chat_id": CHAT_ID,
        "text": text
    })

def send_chart(symbol: str, caption: str):
    """Launch headless browser, take chart screenshot, send via Telegram."""
    async def _screenshot():
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=["--no-sandbox"])
            page = await browser.new_page(viewport={"width":1280,"height":720})
            url = f"{TV_URL}?symbol=BINANCE:{symbol.upper()}&interval={TIMEFRAME}"
            await page.goto(url)
            # wait for chart canvas to load
            await page.wait_for_selector("canvas", timeout=15000)
            img_bytes = await page.screenshot(type="png")
            await browser.close()
            return img_bytes

    img = asyncio.run(_screenshot())
    # send as photo
    files = {"photo": (f"{symbol}.png", img, "image/png")}
    data = {"chat_id": CHAT_ID, "caption": caption}
    requests.post(f"{TELEGRAM_API}/sendPhoto", data=data, files=files)

def get_formatted_time():
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.datetime.now(ist).strftime("%I:%M %p")

def fetch_candles(sym):
    url = f"{BINANCE_API}/fapi/v1/klines?symbol={sym.upper()}&interval={TIMEFRAME}&limit=3"
    res = requests.get(url).json()
    return [{"open":float(c[1]),"high":float(c[2]),"low":float(c[3]),"close":float(c[4])} for c in res]

def is_bullish_engulfing(p,c): return p["close"]<p["open"] and c["close"]>c["open"] and c["open"]<p["close"] and c["close"]>p["open"]
def is_bearish_engulfing(p,c): return p["close"]>p["open"] and c["close"]<c["open"] and c["open"]>p["close"] and c["close"]<p["open"]
def is_doji(c):
    body=abs(c["close"]-c["open"]); rng=c["high"]-c["low"]
    return body<=0.1*rng
def is_hammer(c):
    body=abs(c["close"]-c["open"])
    low_wick=min(c["open"],c["close"])-c["low"]
    up_wick=c["high"]-max(c["open"],c["close"])
    return low_wick>=2*body and up_wick<body

def check_patterns():
    for sym in FUTURES_PAIRS:
        candles = fetch_candles(sym)
        if len(candles)<3: continue
        prev, curr = candles[-2], candles[-1]
        now = get_formatted_time()
        price = curr["close"]
        if is_bullish_engulfing(prev,curr):
            cap = f"🟢 Bullish Engulfing\nPair: {sym.upper()}-PERP\nTF: {TIMEFRAME}\n🕒 {now}\n📈 {price} USDT"
            send_msg(cap)
            send_chart(sym, cap)
        elif is_bearish_engulfing(prev,curr):
            cap = f"🔴 Bearish Engulfing\nPair: {sym.upper()}-PERP\nTF: {TIMEFRAME}\n🕒 {now}\n📉 {price} USDT"
            send_msg(cap)
            send_chart(sym, cap)
        if is_doji(curr):
            cap = f"⚪ Doji Candle\nPair: {sym.upper()}-PERP\nTF: {TIMEFRAME}\n🕒 {now}\n💹 {price} USDT"
            send_msg(cap)
            send_chart(sym, cap)
        if is_hammer(curr):
            cap = f"🔨 Hammer Candle\nPair: {sym.upper()}-PERP\nTF: {TIMEFRAME}\n🕒 {now}\n💥 {price} USDT"
            send_msg(cap)
            send_chart(sym, cap)

def handle_start():
    url = f"{TELEGRAM_API}/getUpdates"
    last_id=None
    while True:
        res = requests.get(url).json().get("result",[])
        for upd in res:
            uid = upd["update_id"]
            if uid==last_id: continue
            last_id=uid
            msg=upd.get("message",{}).get("text","")
            cid=str(upd.get("message",{}).get("chat",{}).get("id",""))
            if msg=="/start" and cid==CHAT_ID:
                send_msg(
                    "✅ Bot active.\n"
                    f"🔍 Monitoring: {','.join(FUTURES_PAIRS).upper()} ({TIMEFRAME})\n"
                    "⚡ Alerts: Engulfing/Doji/Hammer + charts"
                )
        time.sleep(3)

def loop():
    last_alert=None
    while True:
        u = datetime.datetime.utcnow()
        m,s = u.minute, u.second

        # pre-close alert
        if m in (25,55) and s==0:
            key=u.strftime("%Y-%m-%d %H:%M")
            if key!=last_alert:
                send_msg(f"⚠️ 30m candle closing soon\n🕒 {get_formatted_time()}\n📌 Check trade")
                last_alert=key
                time.sleep(60)

        # pattern check
        if m in (0,30) and s==5:
            check_patterns()
            time.sleep(5)

        time.sleep(1)

if __name__=="__main__":
    send_msg(f"🔄 Bot started.\n🕒 {get_formatted_time()}\n✅ Monitoring patterns + charts")
    threading.Thread(target=handle_start,daemon=True).start()
    loop()
