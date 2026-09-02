from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from .config import WEBAPP_URL

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    if not WEBAPP_URL or "your-domain" in WEBAPP_URL:
        await message.answer(
            "👋 Привет!\n\n"
            "Mini App пока не настроен.\n"
            "Укажи WEBAPP_URL в файле .env, затем перезапусти бота."
        )
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text="📚 Открыть расписание",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]],
        resize_keyboard=True
    )

    await message.answer(
        "👋 Привет!\n\n"
        "Здесь можно посмотреть расписание своей группы.\n\n"
        "Нажми кнопку ниже:",
        reply_markup=keyboard
    )


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "📚 Используй кнопку «Открыть расписание», чтобы выбрать группу "
        "и посмотреть расписание."
    )


async def run_bot(bot: Bot):
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)
