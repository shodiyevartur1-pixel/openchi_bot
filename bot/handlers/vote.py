from aiogram import Router, F, types
from sqlalchemy import select
from database import async_session
from models import User, Vote
from keyboards import get_vote_keyboard
from utils import check_vote_limit, register_vote
from config import settings
import datetime

router = Router()

# Mock Projects
PROJECTS = [
    {"id": 1, "name": "🚆 Transport loyihasi"},
    {"id": 2, "name": "🏫 Ta'lim markazi"},
    {"id": 3, "name": "🏥 Shifoxona qurilishi"},
]

@router.message(F.text == "📦 Ovoz berish")
async def vote_menu(message: types.Message):
    can_vote = await check_vote_limit(message.from_user.id)
    if not can_vote:
        await message.answer("⚠️ Siz bugun allaqachon ovoz bergansiz. Iltimos ertaga qaytib keling.")
        return

    await message.answer("Quyidagi loyihalardan birini tanlang:", reply_markup=get_vote_keyboard(PROJECTS))

@router.callback_query(F.data.startswith("vote_"))
async def process_vote(callback: types.CallbackQuery):
    project_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    # Double check limit
    if not await check_vote_limit(user_id):
        await callback.answer("Siz bugun ovoz berib bo'ldingiz!", show_alert=True)
        return

    async with async_session() as session:
        # Save Vote
        vote = Vote(user_id=user_id, project_id=project_id)
        session.add(vote)

        # Update User
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one()
        user.votes += 1
        user.balance += settings.VOTE_REWARD
        
        await session.commit()

        # Set Redis Limit
        await register_vote(user_id)

    await callback.answer(f"Ovoz qabul qilindi! +{settings.VOTE_REWARD} so'm", show_alert=True)
    await callback.message.edit_text("✅ Ovozingiz muvaffaqiyatli qabul qilindi.")