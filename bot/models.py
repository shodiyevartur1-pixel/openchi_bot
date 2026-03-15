from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True) # BigInteger bu yerda to'g'ri
    full_name = Column(String)
    username = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    
    # Pulga doir maydonlar uchun Float o'rniga Numeric ishlatish tavsiya etiladi, 
    # lekin sizning kodingiz bilan ishlashi uchun Float qoldirdik.
    balance = Column(Float, default=0.0) 
    votes = Column(Integer, default=0)
    
    referrals = Column(Integer, default=0)
    referred_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Admin panel uchun MUHIM o'zgartirish:
    # is_active o'rniga is_banned ishlatdik. 
    # Sababi: Yangi userlar default=False (ban emas) bo'ladi, bu mantiqiyroq.
    is_banned = Column(Boolean, default=False) 
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # --- YANGI QO'SHILDI: Bog'lanishlar (Relationships) ---
    # Endi user.withdraw_requests yoki user.votes_list deb murojat qilish mumkin
    withdraw_requests = relationship("WithdrawRequest", back_populates="user")
    votes_list = relationship("Vote", back_populates="user")

class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    
    # ✅ TUZATISH: Integer -> BigInteger (Telegram IDlar katta bo'lishi mumkin)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), index=True) 
    
    project_id = Column(Integer) 
    created_at = Column(DateTime, default=datetime.utcnow)

    # Bog'lanish
    user = relationship("User", back_populates="votes_list")

class WithdrawRequest(Base):
    __tablename__ = "withdraw_requests"

    id = Column(Integer, primary_key=True)
    
    # ✅ TUZATISH: Integer -> BigInteger
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), index=True)
    
    amount = Column(Float) # Yoki Numeric(10, 2)
    card_number = Column(String)
    status = Column(String, default="pending") 
    created_at = Column(DateTime, default=datetime.utcnow)

    # Bog'lanish
    user = relationship("User", back_populates="withdraw_requests")