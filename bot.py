import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_BOT_TOKEN = "9175824403:AAGrK7wERNWN0DcdkAvc0u0MdCjE_TLet-c"
ADMIN_ID = 7606113367

def fetch_pinterest_images(query: str, bookmark: str = None):
    url = "https://www.pinterest.com/resource/BaseSearchResource/get/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    options = {
        "query": query,
        "scope": "pins",
        "page_size": 15
    }
    
    if bookmark:
        options["bookmarks"] = [bookmark]

    params = {
        "source_url": f"/search/pins/?q={query}",
        "data": f'{{"options":{requests.compat.dumps(options)}}}'
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        
        results = data.get('resource_response', {}).get('data', {}).get('results', [])
        next_bookmark = data.get('resource_response', {}).get('bookmark')

        image_urls = []
        for item in results:
            images = item.get('images', {})
            orig = images.get('orig') or images.get('736x') or images.get('474x')
            if orig and 'url' in orig:
                image_urls.append(orig['url'])
                
        return image_urls, next_bookmark
    except Exception as e:
        logging.error(f"Pinterest Search Error: {e}")
        return [], None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! 🌸\n\n"
        "هر کلمه یا موضوعی که می‌خواهی را بفرست تا مستقیم از پینترست برایت جستجو کنم و عکس‌ها را به صورت ورق‌زدنی نمایش دهم."
    )

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    status_msg = await update.message.reply_text(f"🔍 در حال جستجوی «{query}» در پینترست...")
    
    images, bookmark = fetch_pinterest_images(query)
    
    if not images:
        await context.bot.edit_message_text(
            chat_id=update.message.chat_id,
            message_id=status_msg.message_id,
            text="نتیجه‌ای برای این جستجو پیدا نشد یا پینترست محدودیت ایجاد کرد. لطفاً کلیدواژه دیگری امتحان کنید."
        )
        return

    try:
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=status_msg.message_id)
    except Exception:
        pass

    context.user_data['query'] = query
    context.user_data['images'] = images
    context.user_data['index'] = 0
    context.user_data['bookmark'] = bookmark

    await send_pin_response(update.message.chat_id, context)

async def send_pin_response(chat_id: int, context: ContextTypes.DEFAULT_TYPE, message_id: int = None):
    images = context.user_data.get('images', [])
    index = context.user_data.get('index', 0)
    query = context.user_data.get('query', '')
    
    if index >= len(images):
        return

    current_image = images[index]
    keyboard = [
        [InlineKeyboardButton("صفحه بعدی ➡️", callback_data="next_pin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    caption = f"🖼 تصویر {index + 1} | کلیدواژه: `{query}`"

    if message_id:
        try:
            await context.bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=InputMediaPhoto(media=current_image, caption=caption, parse_mode="Markdown"),
                reply_markup=reply_markup
            )
            return
        except Exception:
            pass

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=current_image,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "next_pin":
        context.user_data['index'] += 1
        index = context.user_data['index']
        images = context.user_data.get('images', [])

        if index >= len(images):
            search_query = context.user_data.get('query')
            bookmark = context.user_data.get('bookmark')
            
            if bookmark:
                new_images, next_bookmark = fetch_pinterest_images(search_query, bookmark)
                if new_images:
                    context.user_data['images'].extend(new_images)
                    context.user_data['bookmark'] = next_bookmark
                else:
                    await query.message.reply_text("تصویر دیگری در این دسته یافت نشد.")
                    return
            else:
                await query.message.reply_text("به انتهای نتایج این جستجو رسیدید.")
                return

        await send_pin_response(query.message.chat_id, context, message_id=query.message.message_id)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("ربات جستجوی پینترست روشن شد و آماده دریافت پیام است...")
    app.run_polling()

if __name__ == '__main__':
    main()
