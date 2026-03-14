from aiogram.fsm.state import State, StatesGroup

class WithdrawState(StatesGroup):
    amount = State()
    card_number = State()

class BroadcastState(StatesGroup):
    message = State()

class AdminUserSearch(StatesGroup):
    user_id = State()