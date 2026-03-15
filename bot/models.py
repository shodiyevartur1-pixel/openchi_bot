from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, BigInteger # BigInteger qo'shildi
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timedelta

# Toshkent vaqti uchun yordamchi funksiya (UTC+5)
def get_uzbekistan_time():
    return datetime.utcnow() + timedelta(hours=5)

# --- FOYDALANUVCHI JADVALI ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # INTEGER dan BIGINTEGER ga o'zgartirdik:
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False) 
    full_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    balance = Column(Float, default=0.0)
    votes = Column(Integer, default=0)
    referrals = Column(Integer, default=0)
    # Bu ham foydalanuvchi ID si bo'lgani uchun BigInteger bo'lgani ma'qul
    referred_by = Column(BigInteger, nullable=True) 
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=get_uzbekistan_time)

# --- PUL YECHISH SO'ROVLARI JADVALI ---
class WithdrawRequest(Base):
    __tablename__ = "withdraw_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    card_number = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=get_uzbekistan_time)
    
    user = relationship("User", backref="withdraw_requests")