from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# Main Menu
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📦 Ovoz berish")
    builder.button(text="💰 Hisobim")
    builder.button(text="💳 Pul yechish")
    builder.button(text="👥 Taklif qilish")
    builder.button(text="🏆 TOP 10")
    builder.button(text="📄 To'lovlar")
    builder.button(text="📚 Qo'llanma")
    builder.button(text="⚙️ Sozlamalar")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# Contact Request
def get_contact_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Telefon raqamni yuborish", request_contact=True)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

# Vote Menu
def get_vote_keyboard(projects):
    builder = InlineKeyboardBuilder()
    for proj in projects:
        builder.button(text=proj['name'], callback_data=f"vote_{proj['id']}")
    builder.adjust(1)
    return builder.as_markup()

# Admin Panel
def get_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Statistika", callback_data="admin_stats")
    builder.button(text="💳 To'lov so'rovlari", callback_data="admin_withdraws")
    builder.button(text="📨 Xabar yuborish", callback_data="admin_broadcast")
    builder.button(text="👤 Foydalanuvchi qidirish", callback_data="admin_search")
    builder.adjust(2)
    return builder.as_markup()

def get_withdraw_action_keyboard(request_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"approve_{request_id}")
    builder.button(text="❌ Rad etish", callback_data=f"reject_{request_id}")
    builder.adjust(2)
    return builder.as_markup()