from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timedelta  # timedelta qo'shildi

# Toshkent vaqti uchun yordamchi funksiya (UTC+5)
def get_uzbekistan_time():
    return datetime.utcnow() + timedelta(hours=5)

# --- FOYDALANUVCHI JADVALI ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    balance = Column(Float, default=0.0)
    votes = Column(Integer, default=0)
    referrals = Column(Integer, default=0)
    referred_by = Column(Integer, nullable=True)
    is_banned = Column(Boolean, default=False)
    # BU YERGA QARANG: default=get_uzbekistan_time
    created_at = Column(DateTime, default=get_uzbekistan_time)

# --- PUL YECHISH SO'ROVLARI JADVALI ---
class WithdrawRequest(Base):
    __tablename__ = "withdraw_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    card_number = Column(String, nullable=False)
    status = Column(String, default="pending")
    # BU YERGA QARANG: default=get_uzbekistan_time
    created_at = Column(DateTime, default=get_uzbekistan_time)
    
    user = relationship("User", backref="withdraw_requests")