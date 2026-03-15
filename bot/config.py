import os
import sys
import json  # JSON kutubxonasini qo'shdik
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

class Settings(BaseSettings):
    # --- Bot Sozlamalari ---
    BOT_TOKEN: str
    
    # Admin ID lar (string yoki list kelishini avtomatik to'g'rilaydi)
    ADMIN_IDS: List[int] = []

    # --- Database Sozlamalari (Asosiy) ---
    DB_USER: str = "postgres"
    DB_PASS: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "open_budget"

    # --- Redis Sozlamalari ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # --- Mantiqiy Sozlamalar (Logic) ---
    REFERRAL_BONUS: int = 1000
    VOTE_REWARD: int = 500
    MIN_WITHDRAW: int = 10000

    # --- Yangi Qo'shilgan Sozlamalar (Kuchaytirilgan) ---
    # Majburiy obuna kanali (masalan: @mychannel yoki -1001234567890)
    CHANNEL_ID: str = "@openchi_uz" 
    
    # Ovoz berish havolasi (User shu linkka o'tadi)
    VOTE_LINK: str = "https://openbudget.uz/boards/initiatives/initiative/53/b1083f65-8463-43d0-9ce8-7d96fe5e40f4" 

    # --- Pydantic V2 Sozlamalari ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore' # Keraksiz o'zgaruvchilarga e'tibor bermaslik
    )

    # --- VALIDATOR: Admin ID larni to'g'rilash ---
    @field_validator('ADMIN_IDS', mode='before')
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            # Agar [ ] qavslar ichida bo'lsa (JSON format)
            if v.startswith('[') and v.endswith(']'):
                try:
                    # JSON formatni listga aylantiramiz
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            
            # Agar vergul bilan ajratilgan bo'lsa (1,2,3)
            if ',' in v:
                return [int(x.strip()) for x in v.split(',') if x.strip().isdigit()]
            
            # Agar bitta raqam bo'lsa
            if v.isdigit():
                return [int(v)]
                
        if isinstance(v, list):
            return v
        return []

    # --- VALIDATOR: Kanal ID ni to'g'rilash ---
    @field_validator('CHANNEL_ID', mode='before')
    @classmethod
    def parse_channel_id(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("@") or v.startswith("-100"):
                return v
            if not v.startswith("@") and not v.startswith("http"):
                return f"@{v}"
        return v

    # --- URL Generatsiyasi (RENDER VA POSTGRES UCHUN TO'G'RILANDI) ---
    @property
    def DATABASE_URL(self) -> str:
        # Render'dagi Environment Variable'ni tekshirish
        url = os.getenv("DATABASE_URL")
        if url:
            # SQLAlchemy asinxron ishlashi uchun postgres:// ni postgresql+asyncpg:// ga almashtiramiz
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
        
        # Agar DATABASE_URL topilmasa (lokal uchun)
        if self.DB_HOST == "db":
            return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        
        # Oxirgi chora sifatida SQLite
        return "sqlite+aiosqlite:///./open_budget.db"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

# Global o'zgaruvchi
settings = Settings()

# Konsolga chiqarish (Tekshiruv)
print(f"⚙️ Config loaded. Admins: {settings.ADMIN_IDS}")
# Bazani aniqlash logikasi log uchun
current_url = settings.DATABASE_URL
db_log_type = "PostgreSQL (Remote/Docker)" if "postgresql" in current_url else "SQLite (Local)"
print(f"💾 Database Type: {db_log_type}")
print(f"📢 Channel ID: {settings.CHANNEL_ID}")