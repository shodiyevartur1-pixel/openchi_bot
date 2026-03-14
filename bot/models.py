from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    full_name = Column(String)
    username = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    balance = Column(Float, default=0.0)
    votes = Column(Integer, default=0)
    referrals = Column(Integer, default=0)
    referred_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    is_active = Column(Boolean, default=True) # For blocking
    created_at = Column(DateTime, default=datetime.utcnow)

class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    # BU YERNI O'ZGARTIRING: Integer -> BigInteger
    user_id = Column(BigInteger, ForeignKey('users.id')) 
    project_id = Column(Integer) 
    created_at = Column(DateTime, default=datetime.utcnow)

class WithdrawRequest(Base):
    __tablename__ = "withdraw_requests"

    id = Column(Integer, primary_key=True)
    # BU YERNI HAM O'ZGARTIRING: Integer -> BigInteger
    user_id = Column(BigInteger, ForeignKey('users.id'))
    amount = Column(Float)
    card_number = Column(String)
    status = Column(String, default="pending") 
    created_at = Column(DateTime, default=datetime.utcnow)