import requests
from telegram import Bot, Update, ForceReply
from telegram.ext import CommandHandler, ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
import asyncio
import pytz
import os

# Telegram bot tokeninizi burada tanımlayın
TELEGRAM_BOT_TOKEN = '7473494626:AAHItSYwmY7ty5wfCl1_iCJiQ6snHpdZVKs'

# Chat ID'leri dosya adı
CHAT_ID_FILE = 'chat_ids.txt'

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Chat ID'leri dosyadan yükleme fonksiyonu
def load_chat_ids():
    if os.path.exists(CHAT_ID_FILE):
        with open(CHAT_ID_FILE, 'r') as file:
            return [line.strip() for line in file]
    return []

# Chat ID'leri dosyaya kaydetme fonksiyonu
def save_chat_id(chat_id):
    with open(CHAT_ID_FILE, 'a') as file:
        file.write(f"{chat_id}\n")

# Chat ID'leri dosyadan silme fonksiyonu
def remove_chat_id(chat_id):
    chat_ids = load_chat_ids()
    if chat_id in chat_ids:
        chat_ids.remove(chat_id)
        with open(CHAT_ID_FILE, 'w') as file:
            for id in chat_ids:
                file.write(f"{id}\n")
        return True
    return False

# /start komutu için handler fonksiyonu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    chat_ids = load_chat_ids()
    logging.info(f"Received /start command from chat_id: {chat_id}")
    if chat_id not in chat_ids:
        save_chat_id(chat_id)
        await update.message.reply_text(f"Chat ID: {chat_id} olarak eklendin. Keyfini çıkar :).")
        logging.info(f"Chat ID {chat_id} added to the list.")
    else:
        await update.message.reply_text("Zaten listedesin :).")
        logging.info(f"Chat ID {chat_id} is already in the list.")

# /unlist komutu için handler fonksiyonu
async def unlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    if remove_chat_id(chat_id):
        await update.message.reply_text("Listeden çıkarıldın.")
        logging.info(f"Chat ID {chat_id} removed from the list.")
    else:
        await update.message.reply_text("Listede değilsin.")
        logging.info(f"Chat ID {chat_id} is not in the list.")

# Binance API'den veri çekme fonksiyonu
def get_top_volumes():
    logging.info("Fetching top volumes from Binance")
    url = 'https://api.binance.com/api/v3/ticker/24hr'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        sorted_data = sorted(data, key=lambda x: float(x['quoteVolume']), reverse=True)
        top_volumes = sorted_data[:10]  # En yüksek hacimli ilk 10 kripto para
        logging.info("Top volumes fetched successfully")
        return top_volumes
    else:
        logging.error("Failed to fetch data from Binance")
        return []

# Telegram'a mesaj gönderme fonksiyonu
async def send_telegram_message(message):
    logging.info("Sending message to Telegram")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    chat_ids = load_chat_ids()
    for chat_id in chat_ids:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)
    logging.info("Message sent successfully")

# Ana fonksiyon
async def main():
    logging.info("Starting main function")
    top_volumes = get_top_volumes()
    if top_volumes:
        message = "<b>Top 10 Cryptocurrencies by Volume:</b>\n"
        for coin in top_volumes:
            message += f"<b>{coin['symbol']}:</b> {coin['quoteVolume']} USDT\n"
        await send_telegram_message(message)
    else:
        logging.error("No data to send")

# Zamanlayıcı
async def scheduler_start():
    logging.info("Starting scheduler")
    scheduler = AsyncIOScheduler(timezone=pytz.utc)
    scheduler.add_job(main, 'interval', minutes=1)
    scheduler.start()

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)

# Telegram botunu başlatma fonksiyonu
async def start_bot():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Komut handler'ı ekleyin
    application.add_handler(CommandHandler("ciguli", start))
    application.add_handler(CommandHandler("unlist", unlist))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Botu başlatın
    logging.info("Starting the bot")

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.create_task(start_bot())
    loop.create_task(scheduler_start())

    loop.run_forever()
