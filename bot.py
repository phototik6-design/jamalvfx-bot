# -*- coding: utf-8 -*-
"""
ربات تلگرام jamalvfx
نمایش تعرفه‌های طراحی کاور و اکولایزر + ثبت سفارش مشتری و ارسال آن به ادمین
+ قابلیت سفارش مجدد و پیگیری سفارش

نحوه اجرا:
    1) pip install -r requirements.txt
    2) مقادیر BOT_TOKEN و ADMIN_CHAT_ID را در پایین همین فایل (یا در فایل .env) تنظیم کنید
    3) python bot.py
"""

import logging
import os
import json
from datetime import datetime
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

# فایل ذخیره سفارش‌ها
ORDERS_FILE = "orders.json"

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
ASK_MODIFY_DETAILS, CONFIRM_REORDER, ASK_REORDER_RECEIPT = range(5, 8)


# ---------------------------------------------------------------------------
# توابع کمکی برای مدیریت سفارش‌ها
# ---------------------------------------------------------------------------
def load_orders():
    """بارگیری سفارش‌ها از فایل JSON"""
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_orders(orders):
    """ذخیره‌سازی سفارش‌ها در فایل JSON"""
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


def get_user_orders(user_id):
    """دریافت تمام سفارش‌های یک کاربر"""
    orders = load_orders()
    user_orders = []
    for order_id, order_data in orders.items():
        if order_data.get("user_id") == user_id:
            user_orders.append((order_id, order_data))
    return sorted(user_orders, key=lambda x: x[1].get("date", ""), reverse=True)


def create_order_id():
    """ایجاد شناسه‌ی منحصربه‌فرد برای سفارش"""
    import time
    return f"ORD_{int(time.time())}"


def save_order(order_data):
    """ذخیره‌سازی یک سفارش جدید"""
    orders = load_orders()
    order_id = create_order_id()
    order_data["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    order_data["status"] = "pending"  # pending, confirmed, in_progress, completed
    orders[order_id] = order_data
    save_orders(orders)
    return order_id


def get_order(order_id):
    """دریافت اطلاعات یک سفارش"""
    orders = load_orders()
    return orders.get(order_id)


def update_order_status(order_id, status, message=""):
    """به‌روزرسانی وضعیت سفارش"""
    orders = load_orders()
    if order_id in orders:
        orders[order_id]["status"] = status
        if message:
            orders[order_id]["status_message"] = message
        orders[order_id]["status_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_orders(orders)
        return True
    return False


# ---------------------------------------------------------------------------
# منوها
# ---------------------------------------------------------------------------
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(SERVICES["cover"]["title"], callback_data="cat_cover")],
        [InlineKeyboardButton(SERVICES["eq"]["title"], callback_data="cat_eq")],
        [
            InlineKeyboardButton("🔄 سفارش مجدد", callback_data="reorder"),
            InlineKeyboardButton("📦 پیگیری", callback_data="track"),
        ],
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


def reorder_keyboard(user_orders):
    """منوی سفارش‌های قبلی"""
    if not user_orders:
        return None
    
    buttons = []
    for order_id, order_data in user_orders[:5]:  # فقط آخرین 5 سفارش
        package = order_data.get("package", "نامشخص")
        date = order_data.get("date", "").split()[0]
        status = order_data.get("status", "pending")
        status_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "in_progress": "🔄",
            "completed": "✔️"
        }.get(status, "❓")
        
        buttons.append(
            [InlineKeyboardButton(
                f"{status_emoji} {package[:20]}... ({date})",
                callback_data=f"reorder_{order_id}"
            )]
        )
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def track_keyboard(user_orders):
    """منوی پیگیری سفارش‌ها"""
    if not user_orders:
        return None
    
    buttons = []
    for order_id, order_data in user_orders[:5]:  # فقط آخرین 5 سفارش
        package = order_data.get("package", "نامشخص")
        date = order_data.get("date", "").split()[0]
        status = order_data.get("status", "pending")
        status_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "in_progress": "🔄",
            "completed": "✔️"
        }.get(status, "❓")
        
        buttons.append(
            [InlineKeyboardButton(
                f"{status_emoji} {package[:20]}... ({date})",
                callback_data=f"track_{order_id}"
            )]
        )
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


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
        "یکی از گزینه‌های زیر رو انتخاب کن:"
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_main":
        await query.edit_message_text(
            "یکی از گزینه‌های زیر رو انتخاب کن:",
            reply_markup=main_menu_keyboard(),
        )
        return

    if data == "reorder":
        user_id = query.from_user.id
        user_orders = get_user_orders(user_id)
        
        if not user_orders:
            await query.edit_message_text(
                "تاکنون سفارشی ثبت نکرده‌ای. یک سفارش جدید انتخاب کن 😊",
                reply_markup=main_menu_keyboard(),
            )
            return
        
        reorder_kb = reorder_keyboard(user_orders)
        await query.edit_message_text(
            "🔄 *سفارش‌های قبلی*\n\nیکی رو برای سفارش مجدد انتخاب کن:",
            reply_markup=reorder_kb,
            parse_mode="Markdown"
        )
        return

    if data == "track":
        user_id = query.from_user.id
        user_orders = get_user_orders(user_id)
        
        if not user_orders:
            await query.edit_message_text(
                "تاکنون سفارشی ثبت نکرده‌ای.",
                reply_markup=main_menu_keyboard(),
            )
            return
        
        track_kb = track_keyboard(user_orders)
        await query.edit_message_text(
            "📦 *وضعیت سفارش‌های من*\n\nیکی رو انتخاب کن تا وضعیت رو ببینی:",
            reply_markup=track_kb,
            parse_mode="Markdown"
        )
        return

    if data.startswith("track_"):
        order_id = data.split("_", 1)[1]
        order = get_order(order_id)
        
        if not order:
            await query.answer("سفارش پیدا نشد!", show_alert=True)
            return
        
        status_text = {
            "pending": "⏳ در انتظار تأیید",
            "confirmed": "✅ تأیید شده",
            "in_progress": "🔄 در حال انجام",
            "completed": "✔️ تکمیل شده"
        }.get(order.get("status", "pending"), "نامشخص")
        
        track_text = (
            f"📋 *پیگیری سفارش*\n\n"
            f"🆔 شناسه: `{order_id}`\n"
            f"📦 پکیج: {order.get('package')}\n"
            f"📞 شماره: {order.get('phone')}\n"
            f"📅 تاریخ: {order.get('date')}\n"
            f"💰 مبلغ: {order.get('price')}\n\n"
            f"*وضعیت:* {status_text}\n"
        )
        
        if order.get("status_message"):
            track_text += f"📝 پیام: {order.get('status_message')}\n"
        
        track_text += f"🔄 آپدیت شده: {order.get('status_updated', '-')}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"refresh_track_{order_id}")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="track")]
        ])
        
        await query.edit_message_text(track_text, reply_markup=keyboard, parse_mode="Markdown")
        return

    if data.startswith("refresh_track_"):
        order_id = data.split("_", 2)[2]
        order = get_order(order_id)
        
        if not order:
            await query.answer("سفارش پیدا نشد!", show_alert=True)
            return
        
        status_text = {
            "pending": "⏳ در انتظار تأیید",
            "confirmed": "✅ تأیید شده",
            "in_progress": "🔄 در حال انجام",
            "completed": "✔️ تکمیل شده"
        }.get(order.get("status", "pending"), "نامشخص")
        
        track_text = (
            f"📋 *پیگیری سفارش*\n\n"
            f"🆔 شناسه: `{order_id}`\n"
            f"📦 پکیج: {order.get('package')}\n"
            f"📞 شماره: {order.get('phone')}\n"
            f"📅 تاریخ: {order.get('date')}\n"
            f"💰 مبلغ: {order.get('price')}\n\n"
            f"*وضعیت:* {status_text}\n"
        )
        
        if order.get("status_message"):
            track_text += f"📝 پیام: {order.get('status_message')}\n"
        
        track_text += f"🔄 آپدیت شده: {order.get('status_updated', '-')}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"refresh_track_{order_id}")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="track")]
        ])
        
        await query.edit_message_text(track_text, reply_markup=keyboard, parse_mode="Markdown")
        await query.answer("✅ بروزرسانی شد")
        return

    if data.startswith("reorder_"):
        order_id = data.split("_", 1)[1]
        old_order = get_order(order_id)
        
        if not old_order:
            await query.answer("سفارش پیدا نشد!", show_alert=True)
            return
        
        context.user_data["reorder"] = {
            "old_order_id": order_id,
            "package": old_order.get("package"),
            "price": old_order.get("price"),
            "old_details": old_order.get("details"),
            "name": old_order.get("name"),
            "phone": old_order.get("phone"),
        }
        
        summary = (
            f"🔄 *سفارش مجدد*\n\n"
            f"📦 پکیج: {old_order.get('package')} ({old_order.get('price')})\n"
            f"📝 توضیحات قبلی: {old_order.get('details')}\n\n"
            "می‌خوای توضیحات رو تغییر بدی یا همینطور ثبت کنم؟"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ ویرایش توضیحات", callback_data="modify_details")],
            [InlineKeyboardButton("✅ همینطور ثبت کن", callback_data="confirm_reorder_same")],
            [InlineKeyboardButton("❌ انصراف", callback_data="back_main")],
        ])
        
        await query.edit_message_text(summary, reply_markup=keyboard, parse_mode="Markdown")
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
        "user_id": query.from_user.id,
        "username": query.from_user.username or query.from_user.id,
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

    # ذخیره‌سازی سفارش
    order_id = save_order(order)

    # ارسال سفارش برای ادمین
    admin_text = (
        "🆕 *سفارش جدید*\n\n"
        f"🆔 شناسه: `{order_id}`\n"
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
        f"🆔 شناسه سفارش: `{order_id}`\n\n"
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

    final_message = (
        "🎉 رسید دریافت شد و برای بررسی ارسال شد.\n"
        "به‌زودی از طریق تلگرام یا اینستاگرام باهات هماهنگ می‌کنیم. ممنون 🙏\n\n"
        "برای سفارش‌های دیگر یا پیگیری، گزینه‌های پایین رو استفاده کن:"
    )
    await update.message.reply_text(
        final_message,
        reply_markup=main_menu_keyboard()
    )
    context.user_data.pop("order", None)
    return ConversationHandler.END


async def receipt_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لطفاً فقط *عکس رسید* پرداخت رو بفرست 📸", parse_mode="Markdown")
    return ASK_RECEIPT


async def receive_reorder_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت رسید برای سفارش مجدد"""
    reorder = context.user_data.get("reorder", {})
    user = update.effective_user

    caption = (
        "🧾 *رسید پرداخت (سفارش مجدد)*\n\n"
        f"👤 نام: {reorder.get('name')}\n"
        f"📞 شماره: {reorder.get('phone')}\n"
        f"📦 پکیج: {reorder.get('package')} ({reorder.get('price')})\n"
        f"🔗 آیدی تلگرام مشتری: @{user.username if user.username else user.id}"
    )

    try:
        photo_file_id = update.message.photo[-1].file_id
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=photo_file_id, caption=caption, parse_mode="Markdown")
    except Exception as e:
        logger.error("ارسال رسید سفارش مجدد به ادمین با خطا: %s", e)

    final_message = (
        "🎉 رسید دریافت شد و برای بررسی ارسال شد.\n"
        "به‌زودی از طریق تلگرام یا اینستاگرام باهات هماهنگ می‌کنیم. ممنون 🙏\n\n"
        "برای سفارش‌های دیگر یا پیگیری، گزینه‌های پایین رو استفاده کن:"
    )
    await update.message.reply_text(
        final_message,
        reply_markup=main_menu_keyboard()
    )
    context.user_data.pop("reorder", None)
    return ConversationHandler.END


async def reorder_receipt_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """یادآوری برای دریافت رسید سفارش مجدد"""
    await update.message.reply_text("لطفاً فقط *عکس رسید* پرداخت رو بفرست 📸", parse_mode="Markdown")
    return CONFIRM_REORDER


# --------------------- مکالمه‌ی سفارش مجدد ---------------------
async def modify_reorder_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "توضیحات جدید رو بنویس:\n\n💡 نکته: اگر کاری نمی‌خوای تغییر بدی، همان توضیحات قبلی رو بنویس"
    )
    return ASK_MODIFY_DETAILS


async def get_new_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reorder"]["details"] = update.message.text
    reorder = context.user_data["reorder"]
    
    summary = (
        "📋 *خلاصه سفارش مجدد*\n\n"
        f"📦 پکیج: {reorder['package']} ({reorder['price']})\n"
        f"👤 نام: {reorder['name']}\n"
        f"📞 شماره: {reorder['phone']}\n"
        f"📝 توضیحات جدید: {reorder['details']}\n\n"
        "آیا سفارش مجدد رو ثبت کنم؟"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ بله، ثبت کن", callback_data="confirm_reorder_yes")],
            [InlineKeyboardButton("❌ انصراف", callback_data="back_main")],
        ]
    )
    await update.message.reply_text(summary, reply_markup=keyboard, parse_mode="Markdown")
    return CONFIRM_REORDER


async def finalize_reorder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_reorder_same":
        reorder = context.user_data.get("reorder", {})
        reorder["details"] = reorder.get("old_details", "")
    else:
        reorder = context.user_data.get("reorder", {})
    
    user = query.from_user
    
    # ایجاد سفارش جدید
    new_order_data = {
        "package": reorder.get("package"),
        "price": reorder.get("price"),
        "name": reorder.get("name"),
        "phone": reorder.get("phone"),
        "details": reorder.get("details"),
        "user_id": user.id,
        "username": user.username or user.id,
        "reorder_from": reorder.get("old_order_id"),
    }
    
    order_id = save_order(new_order_data)
    
    # ارسال برای ادمین
    admin_text = (
        "🔄 *سفارش مجدد*\n\n"
        f"🆔 شناسه جدید: `{order_id}`\n"
        f"🔗 سفارش قبلی: `{reorder.get('old_order_id')}`\n"
        f"👤 نام: {reorder.get('name')}\n"
        f"📞 شماره: {reorder.get('phone')}\n"
        f"📦 پکیج: {reorder.get('package')} ({reorder.get('price')})\n"
        f"📝 توضیحات: {reorder.get('details')}\n\n"
        f"👥 تلگرام: @{user.username if user.username else user.id}\n\n"
        "⏳ در انتظار رسید پرداخت..."
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text, parse_mode="Markdown")
    except Exception as e:
        logger.error("ارسال سفارش مجدد به ادمین با خطا: %s", e)
    
    payment_text = (
        "✅ سفارش مجدد ثبت شد!\n\n"
        f"🆔 شناسه: `{order_id}`\n\n"
        "💳 *اطلاعات پرداخت*\n"
        f"شماره کارت: `{CARD_NUMBER}`\n"
        f"به نام: {CARD_HOLDER}\n"
        f"مبلغ: {reorder.get('price')}\n\n"
        "بعد از واریز، لطفاً *عکس رسید* رو برام بفرست 🙏"
    )
    await query.edit_message_text(payment_text, parse_mode="Markdown")
    return ASK_REORDER_RECEIPT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سفارش لغو شد. یکی از گزینه‌های زیر رو انتخاب کن 🙂",
        reply_markup=ReplyKeyboardRemove(),
    )
    # نمایش منوی اصلی
    await update.message.reply_text(
        "بازگشت به منوی اصلی:",
        reply_markup=main_menu_keyboard(),
    )
    context.user_data.pop("order", None)
    context.user_data.pop("reorder", None)
    return ConversationHandler.END


# --------------------- دستورات مدیریت (تنها ادمین) ---------------------
async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش سفارش‌های در انتظار برای ادمین"""
    user_id = update.effective_user.id
    if user_id != int(ADMIN_CHAT_ID):
        await update.message.reply_text("شما اجازه دسترسی ندارید.")
        return
    
    orders = load_orders()
    pending_orders = [(oid, od) for oid, od in orders.items() if od.get("status") == "pending"]
    
    if not pending_orders:
        await update.message.reply_text("هیچ سفارش در انتظار وجود ندارد.")
        return
    
    text = "📋 *سفارش‌های در انتظار*\n\n"
    for order_id, order_data in pending_orders[-10:]:  # آخرین 10 سفارش
        text += (
            f"🆔 {order_id}\n"
            f"👤 {order_data.get('name')} - {order_data.get('phone')}\n"
            f"📦 {order_data.get('package')}\n"
            f"📅 {order_data.get('date')}\n\n"
        )
    
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# اجرای برنامه
# ---------------------------------------------------------------------------
def main():
    if BOT_TOKEN.startswith("PUT_"):
        raise SystemExit(
            "لطفاً BOT_TOKEN را در بالای فایل bot.py یا در متغیر محیطی BOT_TOKEN قرار دهید."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    # مکالمه‌ی سفارش
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
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
    )

    # مکالمه‌ی سفارش مجدد
    reorder_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(modify_reorder_details, pattern=r"^modify_details"),
            CallbackQueryHandler(finalize_reorder, pattern=r"^confirm_reorder_same"),
        ],
        states={
            ASK_MODIFY_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_new_details)],
            CONFIRM_REORDER: [CallbackQueryHandler(finalize_reorder, pattern=r"^confirm_reorder_")],
            ASK_REORDER_RECEIPT: [
                MessageHandler(filters.PHOTO, receive_reorder_receipt),
                MessageHandler(filters.TEXT & ~filters.COMMAND, reorder_receipt_reminder),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pending", admin_pending))
    app.add_handler(order_conv)
    app.add_handler(reorder_conv)
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^(cat_|back_main|tier_|reorder|track|refresh_track_|reorder_|track_)"))

    logger.info("ربات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()
