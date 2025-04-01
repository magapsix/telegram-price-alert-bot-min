import asyncio
import requests
import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import os
import re

TOKEN = os.getenv("BOT_TOKEN")
alerts = {}

coin_ids = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'CRO': 'crypto-com-chain'
}

def get_crypto_prices(ids):
    url = 'https://api.coingecko.com/api/v3/simple/price'
    params = {
        'ids': ','.join(ids),
        'vs_currencies': 'usd',
        'include_24hr_change': 'true'
    }
    return requests.get(url, params=params).json()

def get_sp500_index_price():
    sp500 = yf.Ticker("^GSPC")
    data = sp500.history(period="1d")
    last_price = data["Close"].iloc[-1]
    change = data["Close"].iloc[-1] - data["Open"].iloc[-1]
    percent_change = (change / data["Open"].iloc[-1]) * 100
    return last_price, percent_change

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await get_prices_message()
    await update.message.reply_text(message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text.strip()

    if text.lower().startswith("alert"):
        match = re.match(r'alert\s+([A-Z]{2,6})\s*([<>])\s*(\d+\.?\d*)', text, re.IGNORECASE)
        if match:
            sym, op, val = match.groups()
            alerts.setdefault(user_id, []).append((sym.upper(), op, float(val)))
            await update.message.reply_text(f"✅ Alert збережено: {sym.upper()} {op} {val}")
        else:
            await update.message.reply_text("⚠️ Формат: alert BTC < 65000")

async def get_prices_message():
    crypto = get_crypto_prices([v for v in coin_ids.values()])
    sp_price, sp_change = get_sp500_index_price()

    lines = []
    for sym, id in coin_ids.items():
        if id in crypto:
            p = crypto[id]["usd"]
            ch = crypto[id]["usd_24h_change"]
            lines.append(f"{sym}: ${p:,.2f} ({ch:+.2f}%)")

    lines.append(f"S&P500: ${sp_price:,.2f} ({sp_change:+.2f}%)")
    return "\n".join(lines)

async def alert_checker(app):
    while True:
        crypto = get_crypto_prices([v for v in coin_ids.values()])
        for user_id, user_alerts in alerts.items():
            for sym, op, val in user_alerts:
                if sym in coin_ids:
                    price = crypto[coin_ids[sym]]["usd"]
                    if (op == "<" and price < val) or (op == ">" and price > val):
                        msg = f"🔔 {sym} {op} {val} | Поточна ціна: ${price:,.2f}"
                        await app.bot.send_message(chat_id=user_id, text=msg)
        await asyncio.sleep(21600)  # 6 год

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def main():
    asyncio.create_task(alert_checker(app))
    await app.run_polling()

asyncio.run(main())
