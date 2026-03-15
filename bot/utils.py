import redis.asyncio as redis
from config import settings

# Initialize Redis connection
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def check_vote_limit(user_id: int) -> bool:
    """Check if user can vote today (Redis implementation)"""
    key = f"vote_limit:{user_id}"
    votes = await redis_client.get(key)
    if votes and int(votes) >= 1:
        return False
    return True

async def register_vote(user_id: int):
    """Register a vote and set expiry to end of day"""
    key = f"vote_limit:{user_id}"
    await redis_client.set(key, 1)
    # Set expiry to midnight (simplified: 24 hours for demo)
    await redis_client.expire(key, 86400)

async def get_cache(key: str):
    return await redis_client.get(key)

async def set_cache(key: str, value: str, expire: int = 60):
    await redis_client.set(key, value, ex=expire)

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Botni ishga tushirishdan oldin chaqiring
keep_alive()
# ... botni ishga tushirish kodi (bot.polling() yoki executable)