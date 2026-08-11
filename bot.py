# -*- coding: utf-8 -*-
"""
ربات تلگرام jamalvfx
نمایش تعرفه‌های طراحی کاور و اکولایزر + ثبت سفارش مشتری و ارسال آن به ادمین

نحوه اجرا:
    1) pip install -r requirements.txt
    2) مقادیر BOT_TOKEN و ADMIN_CHAT_ID را در پایین همین فایل (یا در فایل .env) تنظیم کنید
    3) python bot.py
"""

import logging
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------------------------
# تنظیمات — این دو مقدار را حتماً پر کنید
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "PUT_YOUR_CHAT_ID_HERE")  # آیدی عددی چت خودتان

# اطلاعات پرداخت و لینک‌ها
CARD_NUMBER = "6219-8619-1625-5325"
CARD_HOLDER = "جمال محمدی"
CHANNEL_USERNAME = "Jamalvfxx"      # بدون @
INSTAGRAM_USERNAME = "jamalvfx_"    # بدون @

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# داده‌ی تعرفه‌ها
# ---------------------------------------------------------------------------
SERVICES = {
    "cover": {
        "title": "🎨 طراحی کاور",
        "tiers": {
            "cover_1": {
                "name": "طراحی کاور حرفه‌ای",
                "desc": "فضاسازی، پالت رنگی، فونت‌آرایی، افکت‌گذاری",
                "price": "۷۰۰ هزار تومان",
                "gift": "🎁 هدیه: کامینگ‌سون رایگان",
            },
            "cover_2": {
                "name": "طراحی کاور حرفه‌ای",
                "desc": "پالت رنگی، افکت‌گذاری، فونت‌آرایی",
                "price": "۵۵۰ هزار تومان",
                "gift": None,
            },
            "cover_3": {
                "name": "طراحی کاور حرفه‌ای مناسب کار",
                "desc": "پالت رنگی، فونت‌آرایی",
                "price": "۴۵۰ هزار تومان",
                "gift": None,
            },
        },
    },
    "eq": {
        "title": "🎵 طراحی اکولایزر",
        "tiers": {
            "eq_1": {
                "name": "اکولایزر حرفه‌ای و منحصربه‌فرد",
                "desc": "موشن‌گرافی حرفه‌ای و افکت‌گذاری",
                "price": "۷۰۰ هزار تومان",
                "gift": "🎁 هدیه: نسخه‌ی کامینگ‌سون استوری رایگان",
            },
            "eq_2": {
                "name": "اکولایزر حرفه‌ای",
                "desc": "افکت‌گذاری",
                "price": "۵۵۰ هزار تومان",
                "gift": None,
            },
            "eq_3": {
                "name": "اکولایزر حرفه‌ای مناسب کار",
                "desc": "-",
                "price": "۴۵۰ هزار تومان",
                "gift": "🎁 شعرنویسی اکولایزر یک دقیقه، رایگان",
            },
        },
    },
}

# مراحل مکالمه برای ثبت سفارش
ASK_NAME, ASK_PHONE, ASK_DETAILS, CONFIRM, ASK_RECEIPT = range(5)


# ---------------------------------------------------------------------------
# منوها
# ---------------------------------------------------------------------------
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(SERVICES["cover"]["title"], callback_data="cat_cover")],
        [InlineKeyboardButton(SERVICES["eq"]["title"], callback_data="cat_eq")],
        [
            InlineKeyboardButton("📢 کانال", url=f"https://t.me/{CHANNEL_USERNAME}"),
            InlineKeyboardButton("📸 اینستاگرام", url=f"https://instagram.com/{INSTAGRAM_USERNAME}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def tiers_keyboard(cat_key):
    buttons = []
    for tier_key, tier in SERVICES[cat_key]["tiers"].items():
        buttons.append(
            [InlineKeyboardButton(f"{tier['name']} — {tier['price']}", callback_data=f"tier_{tier_key}")]
        )
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def tier_detail_keyboard(tier_key):
    keyboard = [
        [InlineKeyboardButton("✅ ثبت سفارش این پکیج", callback_data=f"order_{tier_key}")],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def find_tier(tier_key):
    for cat in SERVICES.values():
        if tier_key in cat["tiers"]:
            return cat["tiers"][tier_key]
    return None


# ---------------------------------------------------------------------------
# دستورات و هندلرها
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "سلام 👋\n"
        "به ربات *jamalvfx* خوش اومدی!\n\n"
        "یکی از خدمات زیر رو انتخاب کن تا تعرفه‌ها رو ببینی:"
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_main":
        await query.edit_message_text(
            "یکی از خدمات زیر رو انتخاب کن تا تعرفه‌ها رو ببینی:",
            reply_markup=main_menu_keyboard(),
        )
        return

    if data.startswith("cat_"):
        cat_key = data.split("_", 1)[1]
        title = SERVICES[cat_key]["title"]
        await query.edit_message_text(
            f"{title}\n\nیکی از پکیج‌ها رو انتخاب کن:",
            reply_markup=tiers_keyboard(cat_key),
        )
        return

    if data.startswith("tier_"):
        tier_key = data.split("_", 1)[1]
        tier = find_tier(tier_key)
        text = f"*{tier['name']}*\n{tier['desc']}\n\n💰 قیمت: {tier['price']}"
        if tier["gift"]:
            text += f"\n{tier['gift']}"
        await query.edit_message_text(text, reply_markup=tier_detail_keyboard(tier_key), parse_mode="Markdown")
        return


# --------------------- مکالمه‌ی ثبت سفارش ---------------------
async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tier_key = query.data.split("_", 1)[1]
    tier = find_tier(tier_key)
    context.user_data["order"] = {
        "package": tier["name"],
        "price": tier["price"],
    }
    await query.edit_message_text(
        f"عالیه! پکیج انتخابی: *{tier['name']}* ({tier['price']})\n\n"
        f"لطفاً *اسمت* رو بنویس:",
        parse_mode="Markdown",
    )
    return ASK_NAME


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["order"]["name"] = update.message.text
    contact_btn = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 ارسال شماره من", request_contact=True)]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )
    await update.message.reply_text(
        "شماره تماست رو بفرست (یا با دکمه پایین ارسال کن):",
        reply_markup=contact_btn,
    )
    return ASK_PHONE


async def ask_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text
    context.user_data["order"]["phone"] = phone

    await update.message.reply_text(
        "چند خط درباره کاری که میخوای بنویس (اسم آهنگ/موضوع، رفرنس، سبک رنگی و ...):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_DETAILS


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["order"]["details"] = update.message.text
    order = context.user_data["order"]

    summary = (
        "📋 *خلاصه سفارش*\n\n"
        f"👤 نام: {order['name']}\n"
        f"📞 شماره: {order['phone']}\n"
        f"📦 پکیج: {order['package']} ({order['price']})\n"
        f"📝 توضیحات: {order['details']}\n\n"
        "آیا سفارش رو ثبت کنم؟"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ بله، ثبت کن", callback_data="confirm_yes")],
            [InlineKeyboardButton("❌ انصراف", callback_data="confirm_no")],
        ]
    )
    await update.message.reply_text(summary, reply_markup=keyboard, parse_mode="Markdown")
    return CONFIRM


async def finalize_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        await query.edit_message_text("سفارش لغو شد. هر وقت خواستی دوباره از /start شروع کن 🙂")
        context.user_data.pop("order", None)
        return ConversationHandler.END

    order = context.user_data.get("order", {})
    user = query.from_user

    # ارسال سفارش برای ادمین
    admin_text = (
        "🆕 *سفارش جدید*\n\n"
        f"👤 نام: {order.get('name')}\n"
        f"📞 شماره: {order.get('phone')}\n"
        f"📦 پکیج: {order.get('package')} ({order.get('price')})\n"
        f"📝 توضیحات: {order.get('details')}\n\n"
        f"🔗 آیدی تلگرام مشتری: @{user.username if user.username else user.id}\n\n"
        "⏳ در انتظار ارسال رسید پرداخت..."
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text, parse_mode="Markdown")
    except Exception as e:
        logger.error("ارسال پیام به ادمین با خطا مواجه شد: %s", e)

    payment_text = (
        "✅ سفارشت ثبت شد!\n\n"
        "💳 *اطلاعات پرداخت*\n"
        f"شماره کارت: `{CARD_NUMBER}`\n"
        f"به نام: {CARD_HOLDER}\n"
        f"مبلغ: {order.get('price')}\n\n"
        "بعد از واریز، لطفاً *عکس رسید* پرداخت رو همینجا برام بفرست تا سفارش تأیید بشه 🙏"
    )
    await query.edit_message_text(payment_text, parse_mode="Markdown")
    return ASK_RECEIPT


async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order = context.user_data.get("order", {})
    user = update.effective_user

    caption = (
        "🧾 *رسید پرداخت*\n\n"
        f"👤 نام: {order.get('name')}\n"
        f"📞 شماره: {order.get('phone')}\n"
        f"📦 پکیج: {order.get('package')} ({order.get('price')})\n"
        f"🔗 آیدی تلگرام مشتری: @{user.username if user.username else user.id}"
    )

    try:
        photo_file_id = update.message.photo[-1].file_id
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=photo_file_id, caption=caption, parse_mode="Markdown")
    except Exception as e:
        logger.error("ارسال رسید به ادمین با خطا مواجه شد: %s", e)

    await update.message.reply_text(
        "🎉 رسید دریافت شد و برای بررسی ارسال شد.\nبه‌زودی از طریق تلگرام یا اینستاگرام باهات هماهنگ می‌کنیم. ممنون 🙏"
    )
    context.user_data.pop("order", None)
    return ConversationHandler.END


async def receipt_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لطفاً فقط *عکس رسید* پرداخت رو بفرست 📸", parse_mode="Markdown")
    return ASK_RECEIPT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سفارش لغو شد. هر وقت خواستی دوباره از /start شروع کن 🙂",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.pop("order", None)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# اجرای برنامه
# ---------------------------------------------------------------------------
def main():
    if BOT_TOKEN.startswith("PUT_"):
        raise SystemExit(
            "لطفاً BOT_TOKEN را در بالای فایل bot.py یا در متغیر محیطی BOT_TOKEN قرار دهید."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(order_start, pattern=r"^order_")],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_PHONE: [MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, ask_details)],
            ASK_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_order)],
            CONFIRM: [CallbackQueryHandler(finalize_order, pattern=r"^confirm_")],
            ASK_RECEIPT: [
                MessageHandler(filters.PHOTO, receive_receipt),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receipt_reminder),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(order_conv)
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^(cat_|back_main|tier_)"))

    logger.info("ربات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()
