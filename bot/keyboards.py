from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- Foydalanuvchi Menyusi ---
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📦 Ovoz berish")
    builder.button(text="💰 Hisobim")
    builder.button(text="💳 Pul yechish")
    builder.button(text="👥 Taklif qilish")
    builder.button(text="🏆 TOP 10")
    builder.button(text="📜 To'lovlar tarixi")  # TUZATILDI: Handlerga mos keladigan qilib
    builder.button(text="📚 Qo'llanma")
    builder.button(text="⚙️ Sozlamalar")
    builder.adjust(2) # Har qatorda 2 ta tugma
    return builder.as_markup(resize_keyboard=True)

def get_back_keyboard():        
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Ortga")]], resize_keyboard=True)

# Yangi qo'shildi: Pul yechish bekor qilish tugmasi uchun
def get_cancel_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]], resize_keyboard=True)

def get_contact_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Telefon raqamni yuborish", request_contact=True)
    builder.button(text="🔙 Ortga")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

# --- Ovoz berish uchun ---
def get_vote_link_keyboard(link):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔗 Ovoz berish havolasi", url=link)
    builder.button(text="✅ Ovoz berdim", callback_data="vote_done")
    builder.adjust(1)
    return builder.as_markup()

# --- Admin Panel ---

def get_admin_keyboard():
    buttons = [
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="💳 To'lovlar")],
        [KeyboardButton(text="📢 Xabar Tarqatish"), KeyboardButton(text="🔍 User Qidirish")],
        [KeyboardButton(text="🚪 Chiqish")]  # YANGI TUGMA QO'SHILDI
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ... qolgan kod ...
def get_user_manage_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Balans", callback_data=f"add_bal_{user_id}"),
            InlineKeyboardButton(text="➖ Balans", callback_data=f"sub_bal_{user_id}")
        ],
        [
            InlineKeyboardButton(text="🔨 Ban", callback_data=f"ban_user_{user_id}"),
            InlineKeyboardButton(text="✅ Unban", callback_data=f"unban_user_{user_id}")
        ],
        [InlineKeyboardButton(text="🔙 Admin Panelga Qaytish", callback_data="admin_back")]
    ])

def get_withdraw_action_keyboard(req_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{req_id}"),
            InlineKeyboardButton(text="❌ Rad Etish", callback_data=f"reject_{req_id}")
        ]
    ])

def get_confirm_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Xabar Yuborish", callback_data="confirm_broadcast")],
        [InlineKeyboardButton(text="❌ Bekor Qilish", callback_data="cancel_broadcast")]
    ])

# --- Tasdiqlash uchun (Admin) ---
def get_vote_approve_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash (+500 so'm)", callback_data=f"vote_approve_{user_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"vote_reject_{user_id}")
        ]
    ])

# --- Obuna tekshirish ---
def get_subscription_keyboard(channel_url):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=channel_url)],
        [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]
    ])