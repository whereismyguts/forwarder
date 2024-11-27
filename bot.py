
import logging
import redis.asyncio as redis
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.dispatcher.router import Router
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.filters import Command

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

bot = Bot(token=BOT_TOKEN)
router = Router()

redis_client = None


async def init_redis():
    global redis_client
    # redis_client = redis.from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
    redis_client = redis.from_url("redis://redis:6379/0", encoding="utf-8", decode_responses=True)


@router.message(lambda msg: msg.chat.id != int(ADMIN_ID) and not msg.text.startswith("/start"))
async def forward_to_admin(message: types.Message):
    try:
        logging.info(f"Forwarding message from {message.chat.id} to admin {ADMIN_ID}")
        forwarded_message = await bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        await redis_client.set(f"message:{forwarded_message.message_id}", message.chat.id)
    except Exception as e:
        logging.error(f"Error forwarding message: {e}")


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


@router.message(Command("start"))
async def start_command(message: Message):
    await message.answer("Добро пожаловать в бот-канал MTL Village! Здесь мы с удовольствием ответим на все ваши вопросы")


async def main():
    await init_redis()
    storage = RedisStorage(redis_client)
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import asyncio

    asyncio.run(main())
