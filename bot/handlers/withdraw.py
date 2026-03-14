from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, desc
from database import async_session
from models import User, WithdrawRequest
from keyboards import get_main_keyboard
from states import WithdrawState
from config import settings

router = Router()

@router.message(F.text == "💳 Pul yechish")
async def withdraw_start(message: types.Message, state: FSMContext):
    async with async_session() as session:
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one()
        
        if user.balance < settings.MIN_WITHDRAW:
            await message.answer(f"Minimal yechish summasi: {settings.MIN_WITHDRAW} so'm.\nSizning balans: {int(user.balance)} so'm")
            return

    await message.answer(f"Yechmoqchi bo'lgan summani kiriting (Minimal: {settings.MIN_WITHDRAW}):")
    await state.set_state(WithdrawState.amount)

@router.message(WithdrawState.amount)
async def withdraw_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam kiriting.")
        return
    
    amount = int(message.text)
    await state.update_data(amount=amount)
    await message.answer("Karta raqamingizni kiriting (16 xonali):")
    await state.set_state(WithdrawState.card_number)

@router.message(WithdrawState.card_number)
async def withdraw_card(message: types.Message, state: FSMContext):
    if not (message.text.isdigit() and len(message.text) == 16):
        await message.answer("Karta raqami noto'g'ri. Iltimos, qaytadan kiriting.")
        return

    data = await state.get_data()
    amount = data['amount']
    card = message.text

    async with async_session() as session:
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one()

        if user.balance < amount:
            await message.answer("Balansda yetarli mablag' yo'q.")
            await state.clear()
            return

        # Deduct balance immediately (or hold it)
        user.balance -= amount
        
        req = WithdrawRequest(
            user_id=user.id,
            amount=amount,
            card_number=card,
            status="pending"
        )
        session.add(req)
        await session.commit()

    await state.clear()
    await message.answer("✅ So'rov muvaffaqiyatli yuborildi! Admin tasdiqlashini kuting.", reply_markup=get_main_keyboard())

@router.message(F.text == "📄 To'lovlar")
async def withdraw_history(message: types.Message):
    async with async_session() as session:
        # Join User and WithdrawRequest or just get by telegram_id logic
        res_user = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res_user.scalar_one()
        
        res = await session.execute(
            select(WithdrawRequest)
            .where(WithdrawRequest.user_id == user.id)
            .order_by(desc(WithdrawRequest.created_at))
            .limit(10)
        )
        requests = res.scalars().all()

    if not requests:
        await message.answer("Sizda to'lovlar tarixi yo'q.")
        return

    text = "📄 <b>So'nggi to'lovlar:</b>\n\n"
    for r in requests:
        status_emoji = "⏳" if r.status == "pending" else ("✅" if r.status == "approved" else "❌")
        text += (
            f"{status_emoji} <b>{int(r.amount)} so'm</b>\n"
            f"Karta: {r.card_number}\n"
            f"Sana: {r.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"Holat: {r.status}\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")