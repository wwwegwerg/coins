from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards import auth_cancel_keyboard, auth_keyboard, main_menu_keyboard
from app.services.auth_store import AuthStore
from app.services.backend_client import BackendClient
from app.services.ui_state import UIStateStore
from app.states import AuthStates

router = Router(name="auth")


async def _safe_delete_user_message(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        return


async def _render_existing_or_new(
    bot: Bot,
    chat_id: int,
    user_id: int,
    text: str,
    reply_markup,
    ui_state: UIStateStore,
) -> None:
    current_message_id = ui_state.get_message_id(user_id)

    if current_message_id:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=current_message_id,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
            return
        except (TelegramBadRequest, TelegramForbiddenError):
            pass

    sent = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    ui_state.set_message_id(user_id, sent.message_id)


async def _edit_from_callback(
    callback: CallbackQuery,
    text: str,
    reply_markup,
    ui_state: UIStateStore,
) -> None:
    message = _get_callback_message(callback)
    if not message:
        return

    user_id = callback.from_user.id
    ui_state.set_message_id(user_id, message.message_id)
    try:
        await message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    except (TelegramBadRequest, TelegramForbiddenError):
        await _render_existing_or_new(
            bot=callback.bot,
            chat_id=message.chat.id,
            user_id=user_id,
            text=text,
            reply_markup=reply_markup,
            ui_state=ui_state,
        )


def _get_callback_message(callback: CallbackQuery):
    if callback.message is None:
        return None
    if not isinstance(callback.message, Message):
        return None
    return callback.message


def _human_login_error(error: str | None) -> str:
    if not error:
        return "Попробуйте еще раз."

    normalized = error.strip().lower()
    if normalized == "invalid_credentials":
        return "Логин или пароль не подошли."
    if normalized == "db_error":
        return "Сервис временно недоступен."
    if "unreachable" in normalized or "connection" in normalized:
        return "Нет связи с сервисом."
    return "Что-то пошло не так. Попробуйте еще раз."


@router.callback_query(F.data == "auth:start")
async def begin_auth(
    callback: CallbackQuery,
    state: FSMContext,
    ui_state: UIStateStore,
) -> None:
    await state.set_state(AuthStates.waiting_login)
    await callback.answer()
    await _edit_from_callback(
        callback=callback,
        text="👤 Введите ваш логин:",
        reply_markup=auth_cancel_keyboard(),
        ui_state=ui_state,
    )


@router.callback_query(F.data == "auth:cancel")
async def cancel_auth(
    callback: CallbackQuery,
    state: FSMContext,
    ui_state: UIStateStore,
) -> None:
    await state.clear()
    await callback.answer("❌ Отменено")
    await _edit_from_callback(
        callback=callback,
        text="❌ Вход отменен.\nНажмите <b>🔐 Авторизоваться</b>, чтобы начать заново.",
        reply_markup=auth_keyboard(),
        ui_state=ui_state,
    )


@router.message(AuthStates.waiting_login, F.text)
async def receive_login(
    message: Message,
    state: FSMContext,
    bot: Bot,
    ui_state: UIStateStore,
) -> None:
    login = message.text.strip()
    await _safe_delete_user_message(message)

    if not login:
        return

    await state.update_data(login=login)
    await state.set_state(AuthStates.waiting_password)

    await _render_existing_or_new(
        bot=bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        text="🔑 Введите пароль:",
        reply_markup=auth_cancel_keyboard(),
        ui_state=ui_state,
    )


@router.message(AuthStates.waiting_password, F.text)
async def receive_password(
    message: Message,
    state: FSMContext,
    bot: Bot,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
) -> None:
    password = message.text.strip()
    await _safe_delete_user_message(message)

    data = await state.get_data()
    login = data.get("login", "")

    if not login or not password:
        await state.set_state(AuthStates.waiting_login)
        await _render_existing_or_new(
            bot=bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text="⚠️ Данные не распознаны.\nВведите логин еще раз 👇",
            reply_markup=auth_cancel_keyboard(),
            ui_state=ui_state,
        )
        return

    await _render_existing_or_new(
        bot=bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        text="⏳ Проверяю данные...",
        reply_markup=auth_cancel_keyboard(),
        ui_state=ui_state,
    )

    ok, token, error = await backend_client.login(login=login, password=password)
    if not ok or not token:
        friendly_error = _human_login_error(error)
        await state.set_state(AuthStates.waiting_login)
        await _render_existing_or_new(
            bot=bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text=(
                "❌ Авторизоваться не получилось.\n"
                f"{escape(friendly_error)}\n\n"
                "Введите логин еще раз 👇"
            ),
            reply_markup=auth_cancel_keyboard(),
            ui_state=ui_state,
        )
        return

    await auth_store.save_session(
        telegram_user_id=message.from_user.id,
        backend_login=login,
        token=token,
    )
    await state.clear()

    await _render_existing_or_new(
        bot=bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        text=(
            "✅ Готово, вы вошли!\n\n"
            f"Профиль: <code>{escape(login)}</code>\n"
            "Выберите действие ниже 👇"
        ),
        reply_markup=main_menu_keyboard(),
        ui_state=ui_state,
    )


@router.message(AuthStates.waiting_login)
@router.message(AuthStates.waiting_password)
async def block_non_text_during_auth(message: Message) -> None:
    await _safe_delete_user_message(message)