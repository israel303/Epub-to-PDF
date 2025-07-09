import logging
import os
from telegram import Update, __version__ as TG_VER
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import io
import asyncio
import ebooklib
from ebooklib import epub
from weasyprint import HTML
import tempfile
import re
import os.path
import logging.handlers

# הגדרת לוגים
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# דיכוי אזהרות של weasyprint
weasyprint_logger = logging.getLogger('weasyprint')
weasyprint_logger.setLevel(logging.ERROR)  # מציג רק שגיאות, לא אזהרות

# תמונת ה-thumbnail הקבועה
THUMBNAIL_PATH = 'thumbnail.jpg'

# כתובת בסיס ל-Webhook
BASE_URL = os.getenv('BASE_URL', 'https://groky.onrender.com')

# רישום גרסת python-telegram-bot
logger.info(f"Using python-telegram-bot version {TG_VER}")

# פונקציה: המרת EPUB ל-PDF עם תמיכה בתמונות
def convert_epub_to_pdf(epub_path: str, pdf_path: str) -> bool:
    try:
        # יצירת ספרייה זמנית לחילוץ תמונות
        with tempfile.TemporaryDirectory() as temp_dir:
            # קריאת קובץ EPUB
            book = epub.read_epub(epub_path)
            html_content = ""
            
            # חילוץ תמונות לספרייה זמנית
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_IMAGE:
                    image_path = os.path.join(temp_dir, item.get_name())
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    with open(image_path, 'wb') as img_file:
                        img_file.write(item.get_content())
            
            # חילוץ תוכן HTML
            for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    html_content += item.get_content().decode('utf-8')
            
            if not html_content:
                logger.error("לא נמצא תוכן HTML בקובץ EPUB")
                return False
            
            # המרת HTML ל-PDF עם base_url לספריית התמונות הזמנית
            HTML(string=html_content, base_url=temp_dir).write_pdf(pdf_path)
            return True
    except Exception as e:
        logger.error(f"שגיאה בהמרת EPUB ל-PDF: {e}")
        return False

# פקודת /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'היי! אני גרוקי. לא מכיר? לא נורא...\n'
        'שלח לי קובץ EPUB, ואני אמיר אותו ל-PDF עם התמונה של אולדטאון.\n'
        'צריך עזרה? הקלד /help.'
    )

# פקודת /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'הנה מה שאני עושה:\n'
        '1. שלח לי קובץ EPUB.\n'
        '2. אני אמיר אותו ל-PDF.\n'
        '3. אני אוסיף את התמונה של אולדטאון ואת הסיומת _OldTown לשם הקובץ.\n'
        '4. תקבל את קובץ ה-PDF בחזרה.\n'
        'שלח רק קבצי EPUB, אחרת תקבל שגיאה!\n'
        'יש שאלות? תתאפק.'
    )

# הכנת thumbnail
async def prepare_thumbnail() -> io.BytesIO:
    try:
        with Image.open(THUMBNAIL_PATH) as img:
            img = img.convert('RGB')
            img.thumbnail((200, 300))
            thumb_io = io.BytesIO()
            img.save(thumb_io, format='JPEG', quality=85)
            thumb_io.seek(0)
            return thumb_io
    except Exception as e:
        logger.error(f"שגיאה בהכנת thumbnail: {e}")
        return None

# טיפול בקבצים
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document
    
    # בדיקה אם הקובץ הוא EPUB
    if document.mime_type != 'application/epub+zip' and not document.file_name.lower().endswith('.epub'):
        await update.message.reply_text('שגיאה: אנא שלח קובץ EPUB בלבד!')
        return

    await update.message.reply_text('קיבלתי את קובץ ה-EPUB, ממיר אותו ל-PDF...')

    try:
        # הורדת הקובץ
        file_obj = await document.get_file()
        input_file = f'temp_{document.file_name}'
        await file_obj.download_to_drive(input_file)

        # הכנת thumbnail
        thumb_io = await prepare_thumbnail()
        error_message = None
        if not thumb_io:
            error_message = 'לא הצלחתי להוסיף תמונה, אבל הנה ה-PDF שלך.'

        # המרת EPUB ל-PDF
        output_file = f'temp_{os.path.splitext(document.file_name)[0]}.pdf'
        if not convert_epub_to_pdf(input_file, output_file):
            await update.message.reply_text('שגיאה בהמרת הקובץ ל-PDF. תנסה שוב?')
            os.remove(input_file)
            return

        # הוספת "_OldTown" לשם הקובץ
        base, _ = os.path.splitext(document.file_name)
        base = re.sub(r'[_|\s]+', ' ', base.strip())  # ניקוי רווחים/קווים תחתונים
        new_filename = f"{base.replace(' ', '_')}_OldTown.pdf"

        # שליחת קובץ ה-PDF
        with open(output_file, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.message.chat_id,
                document=f,
                filename=new_filename,
                thumbnail=thumb_io if thumb_io else None,
                caption=error_message or 'ספריית אולדטאון - https://t.me/OldTownew'
            )

        # ניקוי קבצים זמניים
        os.remove(input_file)
        if os.path.exists(output_file):
            os.remove(output_file)

    except Exception as e:
        logger.error(f"שגיאה בטיפול בקובץ: {e}")
        await update.message.reply_text('משהו השתבש. תנסה שוב?')
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(output_file):
            os.remove(output_file)

# טיפול בשגיאות
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f'עדכון {update} גרם לשגיאה: {context.error}')
    if update and update.message:
        await update.message.reply_text('אוי, משהו השתבש. תנסה שוב.')

# פונקציה ראשית
async def main():
    # בדיקת קובץ thumbnail
    if not os.path.exists(THUMBNAIL_PATH):
        logger.error(f"קובץ thumbnail {THUMBNAIL_PATH} לא נמצא!")
        return

    # קבלת הטוקן
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        logger.error("TELEGRAM_TOKEN לא הוגדר!")
        return

    # בניית כתובת Webhook
    webhook_url = f"{BASE_URL}/{token}"
    if not webhook_url.startswith('https://'):
        logger.error("BASE_URL חייב להתחיל ב-https://!")
        return

    # יצירת האפליקציה
    application = Application.builder().token(token).build()

    # הוספת handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    application.add_error_handler(error_handler)

    # הגדרת Webhook
    port = int(os.getenv('PORT', 8443))

    try:
        await application.initialize()
        await application.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook הוגדר לכתובת {webhook_url}")
        await application.start()
        await application.updater.start_webhook(
            listen='0.0.0.0',
            port=port,
            url_path=token,
            webhook_url=webhook_url
        )
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logger.error(f"שגיאה בלולאה הראשית: {e}")
        await application.stop()
        await application.shutdown()
        raise
    finally:
        await application.stop()
        await application.shutdown()
        logger.info("הבוט נסגר")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("הבוט נעצר על ידי המשתמש")
    except Exception as e:
        logger.error(f"שגיאה קריטית: {e}")