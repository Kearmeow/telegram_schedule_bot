from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)

from .config import WEBAPP_URL, ADMIN_IDS, ADMIN_USERNAMES
from . import db
from .api import parse_text_schedule

router = Router()


class AdminScheduleStates(StatesGroup):
    waiting_group = State()
    waiting_schedule = State()
    waiting_confirmation = State()
    waiting_replace_group = State()
    waiting_replace_schedule = State()
    waiting_delete_schedule_group = State()
    waiting_delete_schedule_confirmation = State()
    waiting_delete_group = State()
    waiting_delete_group_confirmation = State()


def is_admin(user_id: int, username: str | None = None) -> bool:
    if user_id in ADMIN_IDS:
        return True
    return bool(username) and username.lower() in ADMIN_USERNAMES


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить расписание", callback_data="admin:add_schedule")],
            [InlineKeyboardButton(text="✏️ Заменить расписание", callback_data="admin:replace_schedule")],
            [InlineKeyboardButton(text="🗑️ Удалить расписание", callback_data="admin:delete_schedule")],
            [InlineKeyboardButton(text="📋 Список групп", callback_data="admin:groups")],
            [InlineKeyboardButton(text="🗑️ Удалить группу", callback_data="admin:delete_group")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin:close")],
        ]
    )


def confirm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Сохранить", callback_data="admin:confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel"),
            ]
        ]
    )


def group_keyboard(groups, action: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"📚 {group['name']}",
            callback_data=f"admin:{action}:{group['id']}"
        )]
        for group in groups
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def delete_confirm_keyboard(action: str, group_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="✅ Да, удалить",
                callback_data=f"admin:{action}_confirm:{group_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="admin:back"
            ),
        ]]
    )


@router.message(CommandStart())
async def start(message: Message):
    if not WEBAPP_URL or "your-domain" in WEBAPP_URL:
        await message.answer(
            "👋 Привет!\n\n"
            "Mini App пока не настроен.\n"
            "Укажи WEBAPP_URL в переменных окружения и перезапусти проект."
        )
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text="📚 Открыть расписание",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]],
        resize_keyboard=True,
    )

    await message.answer(
        "👋 Привет!\n\n"
        "Здесь можно посмотреть расписание своей группы.\n\n"
        "Нажми кнопку ниже:",
        reply_markup=keyboard,
    )


@router.message(Command("id"))
async def my_id_command(message: Message):
    username = f"@{message.from_user.username}" if message.from_user.username else "не установлен"
    await message.answer(
        "🆔 Твои данные в Telegram:\n\n"
        f"ID: <code>{message.from_user.id}</code>\n"
        f"Username: <code>{escape_html(username)}</code>\n\n"
        "Для админки можно указать ID в ADMIN_IDS или username в ADMIN_USERNAMES.",
        parse_mode="HTML",
    )


@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id, message.from_user.username):
        await message.answer(
            "⛔ У тебя нет доступа к админке.\n\n"
            f"Твой Telegram ID: <code>{message.from_user.id}</code>\n"
            "Отправь /id, чтобы увидеть данные полностью.",
            parse_mode="HTML",
        )
        return

    await state.clear()
    await message.answer(
        "🔐 <b>Панель администратора</b>\n\n"
        "Здесь можно быстро добавить расписание прямо сообщением.",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:add_schedule")
async def add_schedule_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(AdminScheduleStates.waiting_group)
    await callback.message.edit_text(
        "➕ <b>Добавление расписания</b>\n\n"
        "Напиши название группы одним сообщением.\n\n"
        "Например:\n<code>ИВТ-21</code>\n\n"
        "Для отмены отправь /cancel.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminScheduleStates.waiting_group)
async def receive_group(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id, message.from_user.username):
        await state.clear()
        await message.answer("⛔ У тебя нет доступа к админке.")
        return

    group = message.text.strip() if message.text else ""
    if not group:
        await message.answer("❌ Напиши название группы текстом.")
        return

    await state.update_data(group=group)
    await state.set_state(AdminScheduleStates.waiting_schedule)

    await message.answer(
        "✅ Группа: <b>" + escape_html(group) + "</b>\n\n"
        "Теперь отправь всё расписание одним сообщением.\n\n"
        "Пример:\n"
        "<pre>Понедельник\n"
        "08:30-10:05 Математика | Иванов И.И. | 301\n"
        "10:15-11:50 Информатика | Петров П.П. | 205\n\n"
        "Вторник\n"
        "08:30-10:05 Программирование | Сидоров | 205</pre>\n"
        "Можно использовать Пн/Вт/Ср...\n\n"
        "Для отмены отправь /cancel.",
        parse_mode="HTML",
    )


@router.message(AdminScheduleStates.waiting_schedule)
async def receive_schedule(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id, message.from_user.username):
        await state.clear()
        await message.answer("⛔ У тебя нет доступа к админке.")
        return

    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("❌ Отправь расписание текстом одним сообщением.")
        return

    try:
        parsed = parse_text_schedule(text)
    except ValueError as exc:
        await message.answer(
            "❌ Не получилось разобрать расписание.\n\n"
            f"{escape_html(str(exc))}\n\n"
            "Пример правильной строки:\n"
            "<code>08:30-10:05 Математика | Иванов | 301</code>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    group = data["group"]
    await state.update_data(schedule_text=text, parsed=parsed)
    await state.set_state(AdminScheduleStates.waiting_confirmation)

    preview_lines = []
    for item in parsed[:12]:
        preview_lines.append(
            f"{day_name(item['weekday'])}: {item['start_time']}-{item['end_time']} — "
            f"{escape_html(item['subject'])}"
            + (f" | {escape_html(item['teacher'])}" if item["teacher"] else "")
            + (f" | {escape_html(item['room'])}" if item["room"] else "")
        )

    more = len(parsed) - len(preview_lines)
    if more > 0:
        preview_lines.append(f"… и ещё {more}")

    await message.answer(
        "🔎 <b>Проверь перед сохранением</b>\n\n"
        f"Группа: <b>{escape_html(group)}</b>\n"
        f"Занятий найдено: <b>{len(parsed)}</b>\n\n"
        + "\n".join(preview_lines)
        + "\n\n<b>Сохранить с заменой расписания этой группы?</b>",
        reply_markup=confirm_menu(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:confirm")
async def confirm_import(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    group = data.get("group")
    parsed = data.get("parsed")

    if not group or not parsed:
        await state.clear()
        await callback.message.edit_text("❌ Данные для сохранения потеряны. Начни заново через /admin.")
        await callback.answer()
        return

    rows = [{**lesson, "group": group} for lesson in parsed]
    try:
        result = db.import_lessons(rows, replace=True)
    except Exception as exc:
        await callback.message.edit_text(
            "❌ Ошибка сохранения: " + escape_html(str(exc)),
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
        return

    await state.clear()
    await callback.message.edit_text(
        "✅ <b>Расписание сохранено!</b>\n\n"
        f"Группа: <b>{escape_html(group)}</b>\n"
        f"Занятий: <b>{result['lessons']}</b>\n\n"
        "Теперь его можно открыть через Mini App.",
        parse_mode="HTML",
    )
    await callback.answer("Сохранено")


@router.callback_query(F.data == "admin:cancel")
async def cancel_import(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Добавление расписания отменено.")
    await callback.answer()


@router.callback_query(F.data == "admin:replace_schedule")
async def replace_schedule_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("Нет доступа", show_alert=True)
        return
    groups = db.list_groups()
    if not groups:
        await callback.message.edit_text(
            "📚 Групп пока нет.\n\nСначала добавь расписание.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")]
            ]),
        )
        await callback.answer()
        return
    await state.set_state(AdminScheduleStates.waiting_replace_group)
    await callback.message.edit_text(
        "✏️ <b>Заменить расписание</b>\n\nВыбери группу:",
        reply_markup=group_keyboard(groups, "replace"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:replace:"))
async def replace_group_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("Нет доступа", show_alert=True)
        return
    group_id = int(callback.data.rsplit(":", 1)[1])
    group = db.get_group(group_id)
    if not group:
        await callback.answer("Группа не найдена", show_alert=True)
        return
    await state.update_data(replace_group_id=group_id, replace_group_name=group["name"])
    await state.set_state(AdminScheduleStates.waiting_replace_schedule)
    await callback.message.edit_text(
        "✏️ <b>Замена расписания</b>\n\n"
        f"Группа: <b>{escape_html(group['name'])}</b>\n\n"
        "Отправь новое расписание одним сообщением.\n"
        "Старое расписание этой группы будет заменено полностью.\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminScheduleStates.waiting_replace_schedule)
async def receive_replace_schedule(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id, message.from_user.username):
        await state.clear()
        await message.answer("⛔ У тебя нет доступа к админке.")
        return
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("❌ Отправь расписание текстом одним сообщением.")
        return
    try:
        parsed = parse_text_schedule(text)
    except ValueError as exc:
        await message.answer(
            "❌ Не получилось разобрать расписание.\n\n" + escape_html(str(exc)),
            parse_mode="HTML",
        )
        return
    data = await state.get_data()
    group = data["replace_group_name"]
    rows = [{**lesson, "group": group} for lesson in parsed]
    try:
        result = db.import_lessons(rows, replace=True)
    except Exception as exc:
        await state.clear()
        await message.answer("❌ Ошибка сохранения: " + escape_html(str(exc)), parse_mode="HTML")
        return
    await state.clear()
    await message.answer(
        "✅ <b>Расписание заменено!</b>\n\n"
        f"Группа: <b>{escape_html(group)}</b>\n"
        f"Новых занятий: <b>{result['lessons']}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )


@router.callback_query(F.data == "admin:delete_schedule")
async def delete_schedule_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("Нет доступа", show_alert=True)
        return
    groups = db.list_groups()
    if not groups:
        await callback.message.edit_text(
            "🗑️ Расписаний пока нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")]
            ]),
        )
        await callback.answer()
        return
    await state.set_state(AdminScheduleStates.waiting_delete_schedule_group)
    await callback.message.edit_text(
        "🗑️ <b>Удалить расписание</b>\n\nВыбери группу:",
        reply_markup=group_keyboard(groups, "delete_schedule"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete_schedule:"))
async def delete_schedule_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("Нет доступа", show_alert=True)
        return
    group_id = int(callback.data.rsplit(":", 1)[1])
    group = db.get_group(group_id)
    if not group:
        await callback.answer("Группа не найдена", show_alert=True)
        return
    count = len(db.get_lessons(group_id))
    await callback.message.edit_text(
        "⚠️ <b>Удалить расписание?</b>\n\n"
        f"Группа: <b>{escape_html(group['name'])}</b>\n"
        f"Будет удалено занятий: <b>{count}</b>\n\n"
        "Сама группа останется.",
        reply_markup=delete_confirm_keyboard("delete_schedule", group_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete_schedule_confirm:"))
async def delete_schedule_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("Нет доступа", show_alert=True)
        return
    group_id = int(callback.data.rsplit(":", 1)[1])
    group = db.get_group(group_id)
    if not group:
        await callback.answer("Группа не найдена", show_alert=True)
        return
    try:
        for lesson in db.get_lessons(group_id):
            db.delete_lesson(lesson["id"])
    except Exception as exc:
        await callback.message.edit_text("❌ Ошибка удаления: " + escape_html(str(exc)), parse_mode="HTML")
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_text(
        "✅ <b>Расписание удалено!</b>\n\n"
        f"Группа <b>{escape_html(group['name'])}</b> сохранена.",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )
    await callback.answer("Удалено")


@router.callback_query(F.data == "admin:delete_group")
async def delete_group_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("Нет доступа", show_alert=True)
        return
    groups = db.list_groups()
    if not groups:
        await callback.message.edit_text(
            "📋 Групп пока нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")]
            ]),
        )
        await callback.answer()
        return
    await state.set_state(AdminScheduleStates.waiting_delete_group)
    await callback.message.edit_text(
        "🗑️ <b>Удалить группу</b>\n\n"
        "⚠️ Вместе с группой будет удалено всё её расписание.\n\n"
        "Выбери группу:",
        reply_markup=group_keyboard(groups, "delete_group"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete_group:"))
async def delete_group_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("Нет доступа", show_alert=True)
        return
    group_id = int(callback.data.rsplit(":", 1)[1])
    group = db.get_group(group_id)
    if not group:
        await callback.answer("Группа не найдена", show_alert=True)
        return
    count = len(db.get_lessons(group_id))
    await callback.message.edit_text(
        "⚠️ <b>Удалить группу полностью?</b>\n\n"
        f"Группа: <b>{escape_html(group['name'])}</b>\n"
        f"Занятий: <b>{count}</b>\n\n"
        "Будет удалена сама группа и всё её расписание.",
        reply_markup=delete_confirm_keyboard("delete_group", group_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete_group_confirm:"))
async def delete_group_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("Нет доступа", show_alert=True)
        return
    group_id = int(callback.data.rsplit(":", 1)[1])
    group = db.get_group(group_id)
    if not group:
        await callback.answer("Группа не найдена", show_alert=True)
        return
    try:
        db.delete_group(group_id)
    except Exception as exc:
        await callback.message.edit_text("❌ Ошибка удаления: " + escape_html(str(exc)), parse_mode="HTML")
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_text(
        "✅ <b>Группа удалена!</b>\n\n"
        f"Группа <b>{escape_html(group['name'])}</b> и её расписание удалены.",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )
    await callback.answer("Удалено")


@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "🔐 <b>Панель администратора</b>\n\nУправление расписанием и группами.",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )
    await callback.answer()



@router.callback_query(F.data == "admin:groups")
async def show_groups(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("Нет доступа", show_alert=True)
        return

    groups = db.list_groups()
    if not groups:
        text = "📋 <b>Группы</b>\n\nПока нет ни одной группы."
    else:
        text = "📋 <b>Группы</b>\n\n" + "\n".join(
            f"• {escape_html(group['name'])}" for group in groups
        )

    await callback.message.edit_text(text + "\n\nДля добавления используй /admin.", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:close")
async def close_admin(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Админка закрыта.")
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Текущая операция отменена.")
    else:
        await message.answer("Сейчас нет активной операции.")


@router.message(Command("help"))
async def help_command(message: Message):
    text = (
        "📚 Используй кнопку «Открыть расписание», чтобы выбрать группу "
        "и посмотреть расписание."
    )
    if is_admin(message.from_user.id, message.from_user.username):
        text += "\n\n🔐 Для управления расписанием: /admin"
    await message.answer(text)


def day_name(day: int) -> str:
    return ["", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][day]


def escape_html(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


async def run_bot(bot: Bot):
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)
