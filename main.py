from telegram.ext import Updater, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import CallbackContext
import os
import subprocess
import logging
from flask import Flask, request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def start(update: Update, context: CallbackContext):
    update.message.reply_text("שלום! שלח לי קובץ epub ואמיר אותו ל-PDF!")

def conversion(update: Update, context: CallbackContext):
    try:
        if update.message.document:
            file = context.bot.getFile(update.message.document.file_id)
            file_name = update.message.document.file_name

            file_epub = "files/" + file_name
            file_pdf = file_epub.replace(".epub", ".pdf")

            file.download(file_epub)

            update.message.reply_text("מעבד... " + file_name)
            subprocess.run(
                ["ebook-convert", file_epub, file_pdf],
                env={"QTWEBENGINE_CHROMIUM_FLAGS": "--no-sandbox"},
            )

            context.bot.send_document(
                chat_id=update.message.chat_id,
                document=open(file_pdf, "rb"),
                caption="הנה ה-PDF שלך!",
            )

            os.remove(file_epub)
            os.remove(file_pdf)
            subprocess.run(["find", "files/", "-name", "*", "!", "-iname", ".gitkeep", "-type", "f", "-delete"])
        else:
            update.message.reply_text("שלח לי קובץ .epub ואמיר אותו ל-PDF")
    except:
        update.message.reply_text("שגיאה! אנא ספק קובץ epub תקין")

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.json, bot)
    dp.process_update(update)
    return 'OK'

if __name__ == "__main__":
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    bot = updater.bot

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(MessageHandler(filters.document, conversion))

    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
    bot.set_webhook(url=WEBHOOK_URL)

    app.run(host='0.0.0.0', port=8080)