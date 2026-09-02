import asyncio
import threading

import uvicorn
from aiogram import Bot

from . import db
from .api import app
from .bot import run_bot
from .config import BOT_TOKEN, HOST, PORT


def run_api():
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


async def main():
    db.init_db()

    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    bot = Bot(BOT_TOKEN)
    try:
        await run_bot(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
