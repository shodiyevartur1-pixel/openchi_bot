from aiogram.fsm.state import State, StatesGroup

# --- Foydalanuvchi Holatlari ---

class WithdrawState(StatesGroup):
    """Pul yechish jarayoni"""
    amount = State()        # Summa kiritish
    card_number = State()   # Karta raqamini kiritish

class VoteState(StatesGroup):
    """Ovoz berish jarayoni (Yangi)"""
    waiting_for_phone = State()      # Telefon raqam kutish
    waiting_for_screenshot = State() # Skrinshot kutish

# --- Admin Holatlari ---

class BroadcastState(StatesGroup):
    """Xabar tarqatish jarayoni"""
    waiting_for_content = State()       # Xabar matni/rasmi kutish
    waiting_for_confirmation = State()  # Tasdiqlash kutish

class AdminUserSearch(StatesGroup):
    """Foydalanuvchi qidirish"""
    waiting_for_input = State() # ID yoki username kutish
    
class AdminEditBalance(StatesGroup):
    """Balansni o'zgartirish"""
    waiting_for_amount = State() # Summa kiritish kutish

# states.py fayliga qo'shing
class AdminSendMessage(StatesGroup):
    waiting_for_text = State()

# ... boshqa state lar ...

class AdminSendMessage(StatesGroup):
    waiting_for_text = State()