import logging
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta
import re

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot API tokeni
TOKEN = "8584516435:AAEIHWB1hHgU39gVkccfvqGBLcRa9gqqtwo"

# Reklama ogohlantirishlari uchun xotira (user_id: ogohlantirish soni)
ad_warnings = {}

# Taqiqlangan so'zlar ro'yxati
banned_words = set()

# Reklama patternlari
AD_PATTERNS = [
    r'https?://\S+',  # URL linklar
    r't\.me/\S+',  # Telegram linklar
    r'@\w+',  # Username mention
    r'\b(arzon|sotiladi|sotib|xarid|chegirma|aksiya|narx|buyurtma|zakaz)\b',  # O'zbek reklama so'zlari
]

def is_advertisement(text: str) -> bool:
    """Xabar reklama ekanligini tekshirish"""
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Reklama patternlarini tekshirish
    for pattern in AD_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    
    return False

def contains_banned_word(text: str) -> bool:
    """Xabarda taqiqlangan so'z borligini tekshirish"""
    if not text or not banned_words:
        return False
    
    text_lower = text.lower()
    for word in banned_words:
        if word.lower() in text_lower:
            return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot boshlanganda xabar"""
    await update.message.reply_text(
        "Assalomu alaykum! Men guruh moderator botiman.\n\n"
        "Buyruqlar:\n"
        "/addword <so'z> - Taqiqlangan so'z qo'shish\n"
        "/removeword <so'z> - Taqiqlangan so'zni o'chirish\n"
        "/listwords - Barcha taqiqlangan so'zlarni ko'rish\n"
        "/warnings - Ogohlantirish statistikasi"
    )

async def add_banned_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Taqiqlangan so'z qo'shish"""
    # Faqat adminlar qo'sha oladi
    user = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if user.status not in ['creator', 'administrator']:
        await update.message.reply_text("Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    if not context.args:
        await update.message.reply_text("So'z kiriting! Masalan: /addword badword")
        return
    
    word = ' '.join(context.args)
    banned_words.add(word)
    await update.message.reply_text(f"✅ '{word}' taqiqlangan so'zlar ro'yxatiga qo'shildi!")

async def remove_banned_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Taqiqlangan so'zni o'chirish"""
    user = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if user.status not in ['creator', 'administrator']:
        await update.message.reply_text("Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    if not context.args:
        await update.message.reply_text("So'z kiriting! Masalan: /removeword badword")
        return
    
    word = ' '.join(context.args)
    if word in banned_words:
        banned_words.remove(word)
        await update.message.reply_text(f"✅ '{word}' taqiqlangan so'zlar ro'yxatidan o'chirildi!")
    else:
        await update.message.reply_text(f"'{word}' ro'yxatda topilmadi!")

async def list_banned_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha taqiqlangan so'zlarni ko'rsatish"""
    if not banned_words:
        await update.message.reply_text("Hozircha taqiqlangan so'zlar yo'q.")
        return
    
    words_list = '\n'.join([f"• {word}" for word in sorted(banned_words)])
    await update.message.reply_text(f"📋 Taqiqlangan so'zlar:\n\n{words_list}")

async def show_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ogohlantirish statistikasi"""
    if not ad_warnings:
        await update.message.reply_text("Hozircha ogohlantirishlar yo'q.")
        return
    
    stats = "⚠️ Ogohlantirish statistikasi:\n\n"
    for user_id, count in ad_warnings.items():
        try:
            user = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            name = user.user.first_name
            stats += f"• {name}: {count} ogohlantirish\n"
        except:
            stats += f"• User {user_id}: {count} ogohlantirish\n"
    
    await update.message.reply_text(stats)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruh xabarlarini tekshirish"""
    if not update.message or not update.message.text:
        return
    
    message = update.message
    user_id = message.from_user.id
    chat_id = message.chat_id
    text = message.text
    
    # Admin xabarlarini tekshirmaslik
    try:
        user = await context.bot.get_chat_member(chat_id, user_id)
        if user.status in ['creator', 'administrator']:
            return
    except:
        pass
    
    # Taqiqlangan so'zlarni tekshirish
    if contains_banned_word(text):
        try:
            await message.delete()
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ {message.from_user.first_name}, xabaringiz taqiqlangan so'z uchun o'chirildi!"
            )
        except Exception as e:
            logger.error(f"Xabarni o'chirishda xatolik: {e}")
        return
    
    # Reklama tekshirish
    if is_advertisement(text):
        # Ogohlantirish sonini oshirish
        if user_id not in ad_warnings:
            ad_warnings[user_id] = 0
        ad_warnings[user_id] += 1
        
        warning_count = ad_warnings[user_id]
        
        try:
            # Xabarni o'chirish
            await message.delete()
            
            if warning_count == 1:
                # 1-ogohlantirish
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ {message.from_user.first_name}, reklama taqiqlangan! Bu sizning 1-ogohlantirishingiz."
                )
            
            elif warning_count == 2:
                # 2-ogohlantirish - 1 soatga cheklash
                until_date = datetime.now() + timedelta(hours=1)
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🚫 {message.from_user.first_name}, 2-marta reklama yuborganingiz uchun 1 soatga cheklandingiz!"
                )
            
            elif warning_count >= 3:
                # 3-ogohlantirish - guruhdan chiqarish
                await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ {message.from_user.first_name} 3-marta reklama yuborgan uchun guruhdan chiqarildi!"
                )
                # Statistikadan o'chirish
                del ad_warnings[user_id]
        
        except Exception as e:
            logger.error(f"Foydalanuvchini cheklashda xatolik: {e}")

def main():
    """Botni ishga tushirish"""
    # Application yaratish
    application = Application.builder().token(TOKEN).build()
    
    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addword", add_banned_word))
    application.add_handler(CommandHandler("removeword", remove_banned_word))
    application.add_handler(CommandHandler("listwords", list_banned_words))
    application.add_handler(CommandHandler("warnings", show_warnings))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Botni ishga tushirish
    logger.info("Bot ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()