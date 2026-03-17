from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from sqlalchemy import select, func, update
from database import async_session
from models import User, WithdrawRequest
from keyboards import (get_admin_keyboard, get_main_keyboard, get_withdraw_action_keyboard, 
                       get_back_keyboard, get_user_manage_keyboard, 
                       get_confirm_keyboard)
from states import BroadcastState, AdminUserSearch, AdminEditBalance, AdminSendMessage
from config import settings
import logging
import asyncio

router = Router()
logger = logging.getLogger(__name__)

def is_admin(user_id):
    return int(user_id) in settings.ADMIN_IDS

# --- Panelga Kirish ---
@router.message(F.text == "/admin")
async def admin_panel(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    await message.answer("👋 Admin Panelga Xush Kelibsiz!", reply_markup=get_admin_keyboard())

@router.message(F.text == "🔙 Ortga")
async def back_to_admin(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.clear()
    await message.answer("Admin Panel:", reply_markup=get_admin_keyboard())

# --- Statistika ---
@router.message(F.text == "📊 Statistika")
async def admin_stats(message: types.Message):
    if not is_admin(message.from_user.id): return
    async with async_session() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        total_votes = (await session.execute(select(func.sum(User.votes)))).scalar() or 0
        try:
            pending_reqs = (await session.execute(select(func.count(WithdrawRequest.id)).where(WithdrawRequest.status == "pending"))).scalar() or 0
        except:
            pending_reqs = 0
        
        total_balance = (await session.execute(select(func.sum(User.balance)))).scalar() or 0
        banned_count = (await session.execute(select(func.count(User.id)).where(User.is_banned == True))).scalar() or 0

    stats = (
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Umumiy Foydalanuvchilar: <b>{total_users}</b>\n"
        f"🔨 Banlanganlar: <b>{banned_count}</b>\n\n"
        f"📦 Umumiy Ovozlar: <b>{total_votes}</b>\n"
        f"💰 Tizimdagi Balans: <b>{total_balance:,} so'm</b>\n"
        f"⏳ Kutilayotgan To'lovlar: <b>{pending_reqs}</b>"
    )
    await message.answer(stats, parse_mode="HTML")

# --- To'lovlar (Tuzatilgan - Telegram ID bo'yicha qidirish) ---
@router.message(F.text == "💳 To'lovlar")
async def admin_withdraws(message: types.Message):
    if not is_admin(message.from_user.id): return
    
    try:
        async with async_session() as session:
            # 1. Kutilayotgan so'rovlarni olamiz
            result = await session.execute(
                select(WithdrawRequest).where(WithdrawRequest.status == "pending").limit(10)
            )
            reqs = result.scalars().all()
        
        if not reqs:
            await message.answer("✅ Hozircha kutilayotgan so'rovlar yo'q.")
            return

        for r in reqs:
            # 2. Userni TELEGRAM ID bo'yicha qidiramiz (User.id emas)
            async with async_session() as session:
                user = await session.scalar(select(User).where(User.telegram_id == r.user_id))
            
            if user:
                username = f"@{user.username}" if user.username else "yo'q"
                text = (
                    f"🆔 So'rov ID: <b>{r.id}</b>\n"
                    f"👤 User: {user.full_name} ({username})\n"
                    f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n"
                    f"💰 Summa: <b>{int(r.amount):,} so'm</b>\n"
                    f"💳 Karta: <code>{r.card_number}</code>"
                )
                await message.answer(text, parse_mode="HTML", reply_markup=get_withdraw_action_keyboard(r.id))
            else:
                logger.warning(f"User topilmadi (Telegram ID: {r.user_id})")
                
    except Exception as e:
        logger.error(f"To'lovlar bo'limida xato: {e}")
        await message.answer("⚠️ To'lovlar bo'limini ochishda xatolik yuz berdi.")

# --- TASDIQLASH ---
@router.callback_query(F.data.startswith("approve_"))
async def approve_withdraw(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id): return
    
    try:
        req_id = int(callback.data.split("_")[1])
        
        async with async_session() as session:
            req = await session.scalar(select(WithdrawRequest).where(WithdrawRequest.id == req_id))
            
            if req:
                req.status = "approved"
                # Userni TELEGRAM ID bo'yicha qidiramiz
                user = await session.scalar(select(User).where(User.telegram_id == req.user_id))
                await session.commit()
                
                if user:
                    try:
                        await bot.send_message(
                            user.telegram_id,
                            f"✅ <b>So'rovingiz tasdiqlandi!</b>\n\n"
                            f"💰 <b>{int(req.amount):,} so'm</b> pul kartangizga tushirildi.",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.warning(f"Foydalanuvchiga xabar bormadi: {e}")

                await callback.message.edit_text(f"✅ To'lov tasdiqlandi (ID: {req_id})")
                await callback.answer("Tasdiqlandi")
            else:
                await callback.answer("So'rov topilmadi!", show_alert=True)

    except Exception as e:
        logger.error(f"Tasdiqlashda xato: {e}")
        await callback.answer("Xatolik yuz berdi!", show_alert=True)

# --- RAD ETISH ---
@router.callback_query(F.data.startswith("reject_"))
async def reject_withdraw(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id): return
    
    try:
        req_id = int(callback.data.split("_")[1])
        
        async with async_session() as session:
            req = await session.scalar(select(WithdrawRequest).where(WithdrawRequest.id == req_id))
            
            if req:
                req.status = "rejected"
                # Userni TELEGRAM ID bo'yicha qidiramiz
                user = await session.scalar(select(User).where(User.telegram_id == req.user_id))
                
                if user:
                    user.balance += req.amount
                    try:
                        await bot.send_message(
                            user.telegram_id,
                            f"❌ <b>So'rovingiz rad etildi.</b>\n\n"
                            f"💰 <b>{int(req.amount):,} so'm</b> hisobingizga qaytarildi.",
                            parse_mode="HTML"
                        )
                    except: pass
                
                await session.commit()
                await callback.message.edit_text(f"❌ Rad etildi (ID: {req_id}). Pul qaytarildi.")
                await callback.answer("Rad etildi")
            else:
                await callback.answer("So'rov topilmadi!", show_alert=True)

    except Exception as e:
        logger.error(f"Rad etishda xato: {e}")
        await callback.answer("Xatolik yuz berdi!", show_alert=True)

# --- User Qidirish ---
@router.message(F.text == "🔍 User Qidirish")
async def start_user_search(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.answer("🔍 User ID yoki Username kiriting:", reply_markup=get_back_keyboard())
    await state.set_state(AdminUserSearch.waiting_for_input)

@router.message(AdminUserSearch.waiting_for_input)
async def process_user_search(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    search_input = message.text.strip()
    async with async_session() as session:
        query = select(User)
        if search_input.isdigit():
            user_res = await session.execute(query.where(User.telegram_id == int(search_input)))
        else:
            user_res = await session.execute(query.where(User.username == search_input.replace("@", "")))
        user = user_res.scalar_one_or_none()

    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi.")
        return

    ban_status = "🔨 Banlangan" if user.is_banned else "✅ Faol"
    text = (
        f"👤 <b>Foydalanuvchi Topildi</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"👤 Ism: {user.full_name}\n"
        f"💰 Balans: {user.balance:,} so'm\n"
        f"📊 Status: {ban_status}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_user_manage_keyboard(user.telegram_id))
    await state.clear()

# --- User Boshqaruv (Ban/Unban) ---
@router.callback_query(F.data.startswith("ban_user_"))
async def ban_user(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[2])
    
    async with async_session() as session:
        await session.execute(update(User).where(User.telegram_id == user_id).values(is_banned=True))
        await session.commit()
    
    try:
        await bot.send_message(
            user_id, 
            "⛔️ <b>Siz admin tomonidan bloklandingiz!</b>\nBotdan foydalanish imkoni cheklandi.", 
            parse_mode="HTML", 
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.warning(f"Userga ban xabari bormadi: {e}")

    await callback.answer("User ban qilindi!")
    await callback.message.edit_reply_markup(reply_markup=get_user_manage_keyboard(user_id))

@router.callback_query(F.data.startswith("unban_user_"))
async def unban_user(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id): return
    user_id = int(callback.data.split("_")[2])
    
    async with async_session() as session:
        await session.execute(update(User).where(User.telegram_id == user_id).values(is_banned=False))
        await session.commit()
    
    try:
        await bot.send_message(
            user_id, 
            "✅ <b>Siz bandan olindingiz!</b>\nBotdan foydalanishingiz mumkin.", 
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Userga unban xabari bormadi: {e}")

    await callback.answer("User bandan olindi!")
    await callback.message.edit_reply_markup(reply_markup=get_user_manage_keyboard(user_id))

@router.callback_query(F.data == "admin_back")
async def admin_back_handler(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer("Admin Panel:", reply_markup=get_admin_keyboard())

# --- Balans Qo'shish ---
@router.callback_query(F.data.startswith("add_bal_"))
async def ask_add_balance(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    user_id = callback.data.split("_")[2]
    await state.update_data(target_user_id=user_id, action="add")
    await callback.message.answer(f"➕ User (ID: {user_id}) balansiga qancha qo'shmoqchisiz?")
    await state.set_state(AdminEditBalance.waiting_for_amount)
    await callback.answer()

# --- Balansdan Ayirish ---
@router.callback_query(F.data.startswith("sub_bal_"))
async def ask_sub_balance(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    user_id = callback.data.split("_")[2]
    await state.update_data(target_user_id=user_id, action="sub")
    await callback.message.answer(f"➖ User (ID: {user_id}) balansidan qancha ayirmoqchisiz?")
    await state.set_state(AdminEditBalance.waiting_for_amount)
    await callback.answer()

# --- Balans Tahrirlash (User Xabari bilan) ---
@router.message(AdminEditBalance.waiting_for_amount)
async def process_balance_edit(message: types.Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id): return
    
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    
    amount = int(message.text)
    data = await state.get_data()
    user_id = data.get("target_user_id")
    action = data.get("action")
    
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == int(user_id)))
        
        if user:
            if action == "add":
                user.balance += amount
                notify_text = f"💰 Admin tomonidan hisobingizga <b>{amount:,} so'm</b> to'ldirildi."
                success_text = f"✅ Balansga {amount:,} so'm qo'shildi."
            elif action == "sub":
                if user.balance >= amount:
                    user.balance -= amount
                    notify_text = f"➖ Admin tomonidan hisobingizdan <b>{amount:,} so'm</b> yechildi."
                    success_text = f"✅ Balansdan {amount:,} so'm ayirildi."
                else:
                    await message.answer(f"❌ Foydalanuvchida buncha pul yo'q! Balans: {user.balance:,}")
                    await state.clear()
                    return
            else:
                await state.clear()
                return

            await session.commit()
            
            try:
                await bot.send_message(user.telegram_id, notify_text, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Userga xabar bormadi: {e}")

            await message.answer(success_text, reply_markup=get_admin_keyboard())
        else:
            await message.answer("❌ Foydalanuvchi topilmadi.")
            
    await state.clear()

# --- Userga Shaxsiy Xabar Yuborish ---
@router.callback_query(F.data.startswith("msg_user_"))
async def ask_user_message(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    user_id = callback.data.split("_")[2]
    await state.update_data(target_user_id=user_id)
    await callback.message.answer(f"✉️ User (ID: {user_id}) ga yubormoqchi bo'lgan xabaringizni yozing:")
    await state.set_state(AdminSendMessage.waiting_for_text)
    await callback.answer()

@router.message(AdminSendMessage.waiting_for_text)
async def send_user_message(message: types.Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    user_id = data.get("target_user_id")
    
    try:
        await bot.send_message(user_id, f"📩 <b>Admin:</b>\n\n{message.text}", parse_mode="HTML")
        await message.answer("✅ Xabar muvaffaqiyatli yuborildi!", reply_markup=get_admin_keyboard())
    except Exception as e:
        await message.answer(f"❌ Xabar yuborib bo'lmadi. (Ehtimol user botni blocklagan).\nXato: {e}")
    
    await state.clear()

# --- Broadcast ---
@router.message(F.text == "📢 Xabar Tarqatish")
async def start_broadcast(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.answer("📝 Xabaringizni yuboring:", reply_markup=get_back_keyboard())
    await state.set_state(BroadcastState.waiting_for_content)

@router.message(BroadcastState.waiting_for_content)
async def get_broadcast_content(message: types.Message, state: FSMContext):
    await state.update_data(content_id=message.message_id, chat_id=message.chat.id)
    await message.answer("📢 Tasdiqlaysizmi?", reply_markup=get_confirm_keyboard())
    await state.set_state(BroadcastState.waiting_for_confirmation)

@router.callback_query(F.data == "confirm_broadcast")
async def send_broadcast(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await callback.message.edit_text("⏳ Tarqatilmoqda...")
    count, errors = 0, 0
    async with async_session() as session:
        users = (await session.execute(select(User.telegram_id))).scalars().all()
        for user_id in users:
            try:
                await bot.copy_message(user_id, data['chat_id'], data['content_id'])
                count += 1
                await asyncio.sleep(0.05)
            except: errors += 1
    await callback.message.answer(f"✅ Yakunlandi!\nYuborildi: {count}\nXatolik: {errors}")
    await state.clear()

@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")

# --- ADMIN PANELDAN CHIQISH ---
@router.message(F.text == "🚪 Chiqish")
async def admin_exit(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): 
        return
    await state.clear()
    await message.answer(
        "👋 Siz admin paneldan chiqdingiz.\n"
        "Asosiy menyu faollashtirildi.", 
        reply_markup=get_main_keyboard()
    )