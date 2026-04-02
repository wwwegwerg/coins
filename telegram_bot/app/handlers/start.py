from __future__ import annotations

from html import escape

from aiogram import Bot, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message

from app.keyboards import auth_keyboard, main_menu_keyboard
from app.services.auth_store import AuthStore
from app.services.backend_client import BackendClient
from app.services.ui_state import UIStateStore

router = Router(name="start")


async def _safe_delete_message(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        return


async def _render_main_card(
    bot: Bot,
    chat_id: int,
    user_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup,
    ui_state: UIStateStore,
) -> None:
    current_message_id = ui_state.get_message_id(user_id)
    if current_message_id:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=current_message_id,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )
            return
        except (TelegramBadRequest, TelegramForbiddenError):
            pass

    sent = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )
    ui_state.set_message_id(user_id, sent.message_id)


@router.message(CommandStart())
async def on_start(
    message: Message,
    state: FSMContext,
    bot: Bot,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
) -> None:
    await _safe_delete_message(message)
    await state.clear()

    user_id = message.from_user.id
    session = await auth_store.get_session(user_id)

    is_authorized = False
    backend_login = None

    if session:
        is_authorized, backend_login = await backend_client.check_auth(session.token)
        if not is_authorized:
            await auth_store.delete_session(user_id)

    if is_authorized and backend_login:
        text = (
            "✅ Вы уже вошли.\n\n"
            f"Профиль: <code>{escape(backend_login)}</code>\n"
            "Выберите действие ниже 👇"
        )
        keyboard = main_menu_keyboard()
    else:
        text = (
            "👋 Добро пожаловать!\n\n"
            "Этот бот может посчитать количество монет, купюр и объектов на фото. Просто пополните кошелек и отправьте изображение\n"
            "Здесь всё работает через кнопки.\n"
            "Нажмите <b>🔐 Авторизоваться</b>."
        )
        keyboard = auth_keyboard()

    await _render_main_card(
        bot=bot,
        chat_id=message.chat.id,
        user_id=user_id,
        text=text,
        keyboard=keyboard,
        ui_state=ui_state,
    )
