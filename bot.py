
import logging
import redis.asyncio as redis
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.dispatcher.router import Router
from aiogram.types.error_event import ErrorEvent
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage, Redis

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# Initialize the bot, dispatcher, and router
bot = Bot(token=BOT_TOKEN)
router = Router()

# Redis configuration
redis_client = None


async def init_redis():
    global redis_client
    # redis = aioredis.from_url("redis://redis:6379/0", encoding="utf-8", decode_responses=True)
    # redis_client = redis.from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
    redis_client = redis.from_url("redis://redis:6379/0", encoding="utf-8", decode_responses=True)


# Forward all user messages to the admin
@router.message(lambda msg: msg.chat.id != int(ADMIN_ID))
async def forward_to_admin(message: types.Message):
    try:
        logging.info(f"Forwarding message from {message.chat.id} to admin {ADMIN_ID}")
        forwarded_message = await bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        # Store message mapping in Redis
        await redis_client.set(f"message:{forwarded_message.message_id}", message.chat.id)
    except Exception as e:
        logging.error(f"Error forwarding message: {e}")


# Handle admin replies and send them to the original user
@router.message(lambda msg: msg.chat.id == int(ADMIN_ID) and msg.reply_to_message)
async def reply_to_user(message: types.Message):
    try:
        if message.reply_to_message is None:
            logging.info("Ignoring message from chat (no reply)")
            return

        if message.reply_to_message.from_user.username != "MTLVillageSupportBot":
            logging.info("Ignoring message from chat (not a bot)")
            return

        logging.info(f"Replying to user from admin {ADMIN_ID}")
        original_message_id = message.reply_to_message.message_id
        user_id = await redis_client.get(f"message:{original_message_id}")
        if user_id:
            await bot.send_message(chat_id=int(user_id), text=message.text)
        else:
            await message.reply("Unable to find the original user for this message.")
    except Exception as e:
        logging.error(f"Error replying to user: {e}")


async def main():
    # Initialize Redis
    await init_redis()

    # Create Dispatcher with Redis-based storage
    storage = RedisStorage(redis_client)

    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import asyncio

    asyncio.run(main())
