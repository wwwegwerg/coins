from __future__ import annotations

import asyncio
from datetime import datetime
from html import escape
from io import BytesIO
from typing import Any

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app.keyboards import (
    auth_keyboard,
    balance_keyboard,
    back_to_menu_keyboard,
    history_keyboard,
    history_object_keyboard,
    main_menu_keyboard,
    topup_amount_keyboard,
)
from app.services.auth_store import AuthStore, UserSession
from app.services.backend_client import BackendClient
from app.services.ui_state import UIStateStore
from app.states import CountStates, WalletStates

router = Router(name="menu")

POLL_INTERVAL_SECONDS = 1.5
ANALYSIS_DISCLAIMER = (
    "⚠️ Важно: если на фото видно меньше 80% монеты или купюры, "
    "сервис не гарантирует корректный подсчет."
)


def _status_human(status: str) -> str:
    mapping = {
        "PENDING": "🕒 В очереди",
        "STARTED": "⚙️ В работе",
        "SUCCESS": "✅ Готово",
        "FAILURE": "❌ Ошибка",
    }
    return mapping.get(status, status)


def _human_process_error(error: str | None) -> str:
    if not error:
        return "Попробуйте еще раз чуть позже."

    normalized = error.strip().lower()
    if "not enough tokens" in normalized or "insufficient_tokens" in normalized:
        return "Недостаточно средств на балансе."
    if "timeout" in normalized:
        return "Слишком долго ждали ответ."
    if "unauthorized" in normalized:
        return "Нужно авторизоваться заново."
    return "Что-то пошло не так. Попробуйте еще раз."


def _format_dt(value: str | None) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return value


def _format_amount(value: Any) -> str:
    if value is None:
        return "—"
    return escape(str(value))


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            return None
        return int(value)
    if isinstance(value, str):
        raw = value.strip()
        if raw.isdigit():
            return int(raw)
    return None


def _normalize_objects(raw_objects: Any) -> list[str]:
    if not isinstance(raw_objects, list):
        return []
    objects: list[str] = []
    for item in raw_objects:
        if not isinstance(item, str):
            continue
        label = item.strip()
        if not label:
            continue
        objects.append(label)
    return objects


def _normalize_instances(raw_instances: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_instances, list):
        return []
    instances: list[dict[str, Any]] = []
    for item in raw_instances:
        if not isinstance(item, dict):
            continue
        image_url = item.get("image_url")
        if not isinstance(image_url, str) or not image_url:
            continue
        instances.append(item)
    return instances


def _labels_from_instances(instances: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for item in instances:
        raw_label = item.get("label")
        if not isinstance(raw_label, str):
            continue
        label = raw_label.strip()
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
    return labels


def _extract_object_data(payload: dict[str, Any]) -> tuple[int, list[str], list[dict[str, Any]]]:
    instances = _normalize_instances(payload.get("instances"))
    instance_labels = _labels_from_instances(instances)
    if instance_labels:
        objects = instance_labels
    else:
        objects = _normalize_objects(payload.get("objects"))

    objects_count = _to_int(payload.get("objects_count"))
    if objects_count is None:
        objects_count = _to_int(payload.get("objectsCount"))
    if instances:
        objects_count = len(instances)
    elif objects_count is None:
        objects_count = len(instances) if instances else len(objects)
    return max(0, objects_count), objects, instances


def _format_objects_text(objects_count: int, objects: list[str]) -> str:
    if objects_count <= 0:
        return "🧩 Объекты: <b>0</b>"

    lines = [f"🧩 Объекты: <b>{objects_count}</b>"]
    if objects:
        labels = ", ".join(escape(obj) for obj in objects[:8])
        if len(objects) > 8:
            labels += ", …"
        lines.append(f"Метки: <code>{labels}</code>")
    return "\n".join(lines)


def _analysis_number_for_index(total_items: int, index: int) -> int:
    return max(1, total_items - index)


async def _resolve_analysis_number_for_task(
    auth_store: AuthStore,
    backend_client: BackendClient,
    user_id: int,
    task_id: str,
) -> int | None:
    history_result = await _load_history(auth_store, backend_client, user_id)
    if not history_result.get("ok"):
        return None

    items = history_result.get("items", [])
    for index, item in enumerate(items):
        if str(item.get("id") or "") == task_id:
            return _analysis_number_for_index(len(items), index)
    return None


async def _safe_delete_user_message(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        return


async def _safe_delete_message(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
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
            text=text,
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


def _get_callback_message(callback: CallbackQuery) -> Message | None:
    if callback.message is None:
        return None
    if not isinstance(callback.message, Message):
        return None
    return callback.message


async def _send_or_replace_result_photo(
    bot: Bot,
    chat_id: int,
    user_id: int,
    image_bytes: bytes,
    caption: str,
    ui_state: UIStateStore,
) -> None:
    previous_message_id = ui_state.get_result_message_id(user_id)
    if previous_message_id:
        await _safe_delete_message(bot, chat_id, previous_message_id)

    sent = await bot.send_photo(
        chat_id=chat_id,
        photo=BufferedInputFile(image_bytes, filename="result.jpg"),
        caption=caption,
        parse_mode=ParseMode.HTML,
    )
    ui_state.set_result_message_id(user_id, sent.message_id)


async def _show_auth_required(
    bot: Bot,
    chat_id: int,
    user_id: int,
    text: str,
    state: FSMContext,
    ui_state: UIStateStore,
) -> None:
    await state.clear()
    await _render_existing_or_new(
        bot=bot,
        chat_id=chat_id,
        user_id=user_id,
        text=text,
        reply_markup=auth_keyboard(),
        ui_state=ui_state,
    )


async def _get_session(auth_store: AuthStore, user_id: int) -> UserSession | None:
    return await auth_store.get_session(user_id)


async def _show_main_menu(
    bot: Bot,
    chat_id: int,
    user_id: int,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
    state: FSMContext,
) -> None:
    await state.clear()
    session = await _get_session(auth_store, user_id)
    if not session:
        await _show_auth_required(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="Нужна авторизация.\nНажмите <b>🔐 Авторизоваться</b>.",
            state=state,
            ui_state=ui_state,
        )
        return

    is_authorized, backend_login = await backend_client.check_auth(session.token)
    if not is_authorized:
        await auth_store.delete_session(user_id)
        await _show_auth_required(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="Сессия завершилась.\nНажмите <b>🔐 Авторизоваться</b>.",
            state=state,
            ui_state=ui_state,
        )
        return

    text = (
        "🏠 Главное меню\n\n"
        f"Профиль: <code>{escape(backend_login or session.backend_login)}</code>\n"
        "Выберите действие ниже 👇"
    )
    await _render_existing_or_new(
        bot=bot,
        chat_id=chat_id,
        user_id=user_id,
        text=text,
        reply_markup=main_menu_keyboard(),
        ui_state=ui_state,
    )


async def _load_history(
    auth_store: AuthStore,
    backend_client: BackendClient,
    user_id: int,
) -> dict[str, Any]:
    session = await _get_session(auth_store, user_id)
    if not session:
        return {"ok": False, "unauthorized": True, "error": "Session not found"}

    history = await backend_client.get_history(session.token)
    if history.get("unauthorized"):
        await auth_store.delete_session(user_id)
        return {"ok": False, "unauthorized": True, "error": "Unauthorized"}

    if not history.get("ok"):
        return {"ok": False, "unauthorized": False, "error": history.get("error")}

    return {"ok": True, "items": history.get("items", [])}


async def _show_balance_menu(
    bot: Bot,
    chat_id: int,
    user_id: int,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
    state: FSMContext,
) -> None:
    await state.clear()
    session = await _get_session(auth_store, user_id)
    if not session:
        await _show_auth_required(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="Нужна авторизация.\nНажмите <b>🔐 Авторизоваться</b>.",
            state=state,
            ui_state=ui_state,
        )
        return

    balance = await backend_client.get_balance(session.token)
    if balance.get("unauthorized"):
        await auth_store.delete_session(user_id)
        await _show_auth_required(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="Сессия завершилась.\nНажмите <b>🔐 Авторизоваться</b>.",
            state=state,
            ui_state=ui_state,
        )
        return

    if not balance.get("ok"):
        await _render_existing_or_new(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="⚠️ Не удалось получить баланс.\nПопробуйте еще раз чуть позже.",
            reply_markup=main_menu_keyboard(),
            ui_state=ui_state,
        )
        return

    balance_text = _format_amount(balance.get("balance"))
    cost_text = _format_amount(balance.get("cost"))
    text = (
        "💰 Баланс кошелька\n\n"
        f"Доступно: <b>{balance_text}</b>\n"
        f"Стоимость одной проверки: <b>{cost_text}</b>\n\n"
        "Нажмите <b>💳 Пополнить</b>, чтобы ввести сумму."
    )
    await _render_existing_or_new(
        bot=bot,
        chat_id=chat_id,
        user_id=user_id,
        text=text,
        reply_markup=balance_keyboard(),
        ui_state=ui_state,
    )


async def _show_history_page(
    bot: Bot,
    chat_id: int,
    user_id: int,
    page: int,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
    state: FSMContext,
) -> None:
    await state.clear()

    history_result = await _load_history(auth_store, backend_client, user_id)
    if not history_result.get("ok"):
        if history_result.get("unauthorized"):
            await _show_auth_required(
                bot=bot,
                chat_id=chat_id,
                user_id=user_id,
                text="Нужна повторная авторизация.\nНажмите <b>🔐 Авторизоваться</b>.",
                state=state,
                ui_state=ui_state,
            )
            return

        await _render_existing_or_new(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="⚠️ Историю пока не удалось открыть.\nПопробуйте еще раз чуть позже.",
            reply_markup=main_menu_keyboard(),
            ui_state=ui_state,
        )
        return

    items = history_result.get("items", [])
    if not items:
        await _render_existing_or_new(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="🧾 История пока пустая.",
            reply_markup=main_menu_keyboard(),
            ui_state=ui_state,
        )
        return

    safe_page = max(0, min(page, len(items) - 1))
    item = items[safe_page]
    analysis_number = _analysis_number_for_index(len(items), safe_page)

    status = _status_human(str(item.get("status") or "UNKNOWN"))
    total = item.get("total")
    total_text = str(total) if total is not None else "—"
    objects_count, objects, instances = _extract_object_data(item)

    text = (
        f"🧾 Анализ #{analysis_number}\n\n"
        f"Статус: <b>{escape(status)}</b>\n"
        f"Сумма: <b>{escape(total_text)}</b>\n"
        f"{_format_objects_text(objects_count, objects)}\n"
        f"Создано: <code>{_format_dt(item.get('createdAt'))}</code>\n"
        f"Завершено: <code>{_format_dt(item.get('completedAt'))}</code>"
    )

    await _render_existing_or_new(
        bot=bot,
        chat_id=chat_id,
        user_id=user_id,
        text=text,
        reply_markup=history_keyboard(
            page=safe_page,
            total=len(items),
            has_image=bool(item.get("imageUrl")),
            has_objects=bool(instances),
        ),
        ui_state=ui_state,
    )


async def _show_history_object_instance(
    bot: Bot,
    chat_id: int,
    user_id: int,
    page: int,
    index: int,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
    state: FSMContext,
) -> None:
    await state.clear()
    history_result = await _load_history(auth_store, backend_client, user_id)
    if not history_result.get("ok"):
        if history_result.get("unauthorized"):
            await _show_auth_required(
                bot=bot,
                chat_id=chat_id,
                user_id=user_id,
                text="Нужна повторная авторизация.\nНажмите <b>🔐 Авторизоваться</b>.",
                state=state,
                ui_state=ui_state,
            )
            return
        await _render_existing_or_new(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="⚠️ Не удалось открыть вырезки объектов.",
            reply_markup=main_menu_keyboard(),
            ui_state=ui_state,
        )
        return

    items = history_result.get("items", [])
    if not items:
        await _render_existing_or_new(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="🧾 История пока пустая.",
            reply_markup=main_menu_keyboard(),
            ui_state=ui_state,
        )
        return

    safe_page = max(0, min(page, len(items) - 1))
    item = items[safe_page]
    analysis_number = _analysis_number_for_index(len(items), safe_page)
    objects_count, objects, instances = _extract_object_data(item)
    if not instances:
        await _show_history_page(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            page=safe_page,
            auth_store=auth_store,
            backend_client=backend_client,
            ui_state=ui_state,
            state=state,
        )
        return

    safe_index = max(0, min(index, len(instances) - 1))
    instance = instances[safe_index]
    image_url = instance.get("image_url")
    if not isinstance(image_url, str) or not image_url:
        await _render_existing_or_new(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="⚠️ Для этого объекта нет изображения.",
            reply_markup=history_object_keyboard(
                page=safe_page,
                index=safe_index,
                total=len(instances),
            ),
            ui_state=ui_state,
        )
        return

    image_response = await backend_client.get_result_image(image_url)
    if not image_response.get("ok"):
        await _render_existing_or_new(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="⚠️ Не удалось загрузить вырезку объекта.",
            reply_markup=history_object_keyboard(
                page=safe_page,
                index=safe_index,
                total=len(instances),
            ),
            ui_state=ui_state,
        )
        return

    label = escape(str(instance.get("label") or "Объект"))
    objects_text = _format_objects_text(objects_count, objects)
    await _send_or_replace_result_photo(
        bot=bot,
        chat_id=chat_id,
        user_id=user_id,
        image_bytes=image_response["content"],
        caption=(
            f"🧩 Анализ #{analysis_number}\n"
            f"Объект: <b>{label}</b>\n"
            f"Кадр: <b>{safe_index + 1}/{len(instances)}</b>\n"
            f"{objects_text}"
        ),
        ui_state=ui_state,
    )

    await _render_existing_or_new(
        bot=bot,
        chat_id=chat_id,
        user_id=user_id,
        text=(
            f"🧩 Вырезки объектов для анализа #{analysis_number}\n\n"
            "Используйте кнопки ниже для переключения."
        ),
        reply_markup=history_object_keyboard(
            page=safe_page,
            index=safe_index,
            total=len(instances),
        ),
        ui_state=ui_state,
    )


@router.callback_query(F.data == "menu:back")
async def menu_back(
    callback: CallbackQuery,
    state: FSMContext,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
) -> None:
    await callback.answer()
    await _show_main_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        user_id=callback.from_user.id,
        auth_store=auth_store,
        backend_client=backend_client,
        ui_state=ui_state,
        state=state,
    )


@router.callback_query(F.data == "menu:count")
async def menu_count(
    callback: CallbackQuery,
    state: FSMContext,
    auth_store: AuthStore,
    ui_state: UIStateStore,
) -> None:
    await callback.answer()

    session = await _get_session(auth_store, callback.from_user.id)
    if not session:
        await _show_auth_required(
            bot=callback.bot,
            chat_id=callback.from_user.id,
            user_id=callback.from_user.id,
            text="Нужна авторизация.\nНажмите <b>🔐 Авторизоваться</b>.",
            state=state,
            ui_state=ui_state,
        )
        return

    await state.set_state(CountStates.waiting_photo)
    await _edit_from_callback(
        callback=callback,
        text=(
            "Отправьте фото с монетами или купюрами.\n\n"
            f"{escape(ANALYSIS_DISCLAIMER)}\n\n"
            "После обработки фото из чата удалится."
        ),
        reply_markup=back_to_menu_keyboard(),
        ui_state=ui_state,
    )


@router.callback_query(F.data == "menu:history")
async def menu_history(
    callback: CallbackQuery,
    state: FSMContext,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
) -> None:
    await callback.answer()
    await _show_history_page(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        user_id=callback.from_user.id,
        page=0,
        auth_store=auth_store,
        backend_client=backend_client,
        ui_state=ui_state,
        state=state,
    )


@router.callback_query(F.data == "menu:balance")
async def menu_balance(
    callback: CallbackQuery,
    state: FSMContext,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
) -> None:
    await callback.answer()
    await _show_balance_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        user_id=callback.from_user.id,
        auth_store=auth_store,
        backend_client=backend_client,
        ui_state=ui_state,
        state=state,
    )


@router.callback_query(F.data == "wallet:topup")
async def wallet_topup_start(
    callback: CallbackQuery,
    state: FSMContext,
    ui_state: UIStateStore,
) -> None:
    await callback.answer()
    await state.set_state(WalletStates.waiting_topup_amount)
    await _edit_from_callback(
        callback=callback,
        text=(
            "💳 Пополнение\n\n"
            "Введите сумму цифрами.\n"
            "Например: <b>500</b>"
        ),
        reply_markup=topup_amount_keyboard(),
        ui_state=ui_state,
    )


@router.callback_query(F.data == "wallet:cancel")
async def wallet_topup_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
) -> None:
    await callback.answer("Отменено")
    await _show_balance_menu(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        user_id=callback.from_user.id,
        auth_store=auth_store,
        backend_client=backend_client,
        ui_state=ui_state,
        state=state,
    )


@router.callback_query(F.data.startswith("history:page:"))
async def history_page(
    callback: CallbackQuery,
    state: FSMContext,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
) -> None:
    await callback.answer()

    try:
        page = int(callback.data.split(":")[-1])
    except Exception:
        return

    await _show_history_page(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        user_id=callback.from_user.id,
        page=page,
        auth_store=auth_store,
        backend_client=backend_client,
        ui_state=ui_state,
        state=state,
    )


@router.callback_query(F.data == "history:noop")
async def history_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("history:image:"))
async def history_image(
    callback: CallbackQuery,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
) -> None:
    await callback.answer()

    try:
        page = int(callback.data.split(":")[-1])
    except Exception:
        return

    history_result = await _load_history(auth_store, backend_client, callback.from_user.id)
    if not history_result.get("ok"):
        return

    items = history_result.get("items", [])
    if not items:
        return

    safe_page = max(0, min(page, len(items) - 1))
    item = items[safe_page]
    analysis_number = _analysis_number_for_index(len(items), safe_page)
    image_url = item.get("imageUrl")
    if not isinstance(image_url, str) or not image_url:
        return

    image_response = await backend_client.get_result_image(image_url)
    if not image_response.get("ok"):
        return

    filename = escape(str(item.get("filename") or "—"))
    status = escape(_status_human(str(item.get("status") or "UNKNOWN")))
    total = item.get("total")
    total_text = escape(str(total) if total is not None else "—")
    objects_count, objects, _ = _extract_object_data(item)
    objects_text = _format_objects_text(objects_count, objects)

    await _send_or_replace_result_photo(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        user_id=callback.from_user.id,
        image_bytes=image_response["content"],
        caption=(
            f"🧾 Анализ #{analysis_number}\n"
            f"Файл: <code>{filename}</code>\n"
            f"Статус: <b>{status}</b>\n"
            f"Сумма: <b>{total_text}</b>\n"
            f"{objects_text}"
        ),
        ui_state=ui_state,
    )


@router.callback_query(F.data.startswith("history:objects:"))
async def history_objects(
    callback: CallbackQuery,
    state: FSMContext,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
) -> None:
    await callback.answer()
    try:
        page = int(callback.data.split(":")[-1])
    except Exception:
        return

    await _show_history_object_instance(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        user_id=callback.from_user.id,
        page=page,
        index=0,
        auth_store=auth_store,
        backend_client=backend_client,
        ui_state=ui_state,
        state=state,
    )


@router.callback_query(F.data.startswith("history:object:"))
async def history_object_page(
    callback: CallbackQuery,
    state: FSMContext,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
) -> None:
    await callback.answer()
    try:
        _, _, page_raw, index_raw = callback.data.split(":")
        page = int(page_raw)
        index = int(index_raw)
    except Exception:
        return

    await _show_history_object_instance(
        bot=callback.bot,
        chat_id=callback.from_user.id,
        user_id=callback.from_user.id,
        page=page,
        index=index,
        auth_store=auth_store,
        backend_client=backend_client,
        ui_state=ui_state,
        state=state,
    )


@router.message(CountStates.waiting_photo, F.photo)
@router.message(CountStates.waiting_photo, F.document)
async def receive_photo_for_count(
    message: Message,
    state: FSMContext,
    bot: Bot,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
) -> None:
    user_id = message.from_user.id
    chat_id = message.chat.id
    await _safe_delete_user_message(message)

    session = await _get_session(auth_store, user_id)
    if not session:
        await _show_auth_required(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="Нужна авторизация.\nНажмите <b>🔐 Авторизоваться</b>.",
            state=state,
            ui_state=ui_state,
        )
        return

    await _render_existing_or_new(
        bot=bot,
        chat_id=chat_id,
        user_id=user_id,
        text="✅ Фото получено.\n⏳ Считаю сумму...",
        reply_markup=back_to_menu_keyboard(),
        ui_state=ui_state,
    )

    image = None
    filename = ""

    if message.photo:
        image = message.photo[-1]
        filename = f"{image.file_id}.jpg"
    elif message.document:
        document = message.document
        mime_type = (document.mime_type or "").lower()
        if not mime_type.startswith("image/"):
            await _render_existing_or_new(
                bot=bot,
                chat_id=chat_id,
                user_id=user_id,
                text=(
                    "Нужна именно картинка.\n"
                    "Отправьте фото (или изображение-файл) и попробуйте снова."
                ),
                reply_markup=back_to_menu_keyboard(),
                ui_state=ui_state,
            )
            return
        image = document
        filename = document.file_name or f"{document.file_id}.jpg"

    if image is None:
        await _render_existing_or_new(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="Не удалось распознать изображение.\nОтправьте фото еще раз.",
            reply_markup=back_to_menu_keyboard(),
            ui_state=ui_state,
        )
        return

    image_buffer = BytesIO()
    try:
        await bot.download(image, destination=image_buffer)
    except Exception:
        await _render_existing_or_new(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="⚠️ Не получилось прочитать фото.\nОтправьте его еще раз.",
            reply_markup=back_to_menu_keyboard(),
            ui_state=ui_state,
        )
        return

    detect_result = await backend_client.detect(
        token=session.token,
        filename=filename,
        image_bytes=image_buffer.getvalue(),
    )

    if detect_result.get("unauthorized"):
        await auth_store.delete_session(user_id)
        await _show_auth_required(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text="Сессия завершилась.\nНажмите <b>🔐 Авторизоваться</b>.",
            state=state,
            ui_state=ui_state,
        )
        return

    if not detect_result.get("ok"):
        process_error = _human_process_error(str(detect_result.get("error") or ""))
        await _render_existing_or_new(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id,
            text=f"⚠️ Не получилось запустить подсчет.\n{escape(process_error)}",
            reply_markup=back_to_menu_keyboard(),
            ui_state=ui_state,
        )
        return

    task_id = str(detect_result.get("task_id"))
    last_status = ""

    while True:
        result_state = await backend_client.get_result(token=session.token, task_id=task_id)

        if result_state.get("unauthorized"):
            await auth_store.delete_session(user_id)
            await _show_auth_required(
                bot=bot,
                chat_id=chat_id,
                user_id=user_id,
                text="Сессия завершилась.\nНажмите <b>🔐 Авторизоваться</b>.",
                state=state,
                ui_state=ui_state,
            )
            return

        if not result_state.get("ok"):
            process_error = _human_process_error(str(result_state.get("error") or ""))
            await _render_existing_or_new(
                bot=bot,
                chat_id=chat_id,
                user_id=user_id,
                text=f"⚠️ Не получилось получить результат.\n{escape(process_error)}",
                reply_markup=back_to_menu_keyboard(),
                ui_state=ui_state,
            )
            return

        status = str(result_state.get("status"))

        if status in {"PENDING", "STARTED"}:
            if status != last_status:
                last_status = status
                await _render_existing_or_new(
                    bot=bot,
                    chat_id=chat_id,
                    user_id=user_id,
                    text=f"⏳ Считаю сумму...\nСтатус: <b>{escape(_status_human(status))}</b>",
                    reply_markup=back_to_menu_keyboard(),
                    ui_state=ui_state,
                )
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            continue

        if status == "FAILURE":
            process_error = _human_process_error(str(result_state.get("error") or ""))
            await _render_existing_or_new(
                bot=bot,
                chat_id=chat_id,
                user_id=user_id,
                text=f"❌ Обработка не удалась.\n{escape(process_error)}",
                reply_markup=main_menu_keyboard(),
                ui_state=ui_state,
            )
            await state.clear()
            return

        if status == "SUCCESS":
            result_payload = result_state.get("result") if isinstance(result_state.get("result"), dict) else {}
            total = result_payload.get("total")
            total_text = escape(str(total) if total is not None else "—")
            image_url = result_payload.get("image_url")
            objects_count, objects, _ = _extract_object_data(result_payload)
            objects_text = _format_objects_text(objects_count, objects)
            analysis_number = await _resolve_analysis_number_for_task(
                auth_store=auth_store,
                backend_client=backend_client,
                user_id=user_id,
                task_id=task_id,
            )
            analysis_title = (
                f"🧾 Анализ #{analysis_number}\n"
                if isinstance(analysis_number, int)
                else ""
            )

            if isinstance(image_url, str) and image_url:
                image_response = await backend_client.get_result_image(image_url)
                if image_response.get("ok"):
                    await _send_or_replace_result_photo(
                        bot=bot,
                        chat_id=chat_id,
                        user_id=user_id,
                        image_bytes=image_response["content"],
                        caption=(
                            f"{analysis_title}"
                            "✅ Готово!\n"
                            f"💰 Сумма: <b>{total_text}</b>\n"
                            f"{objects_text}"
                        ),
                        ui_state=ui_state,
                    )

            await state.clear()
            await _render_existing_or_new(
                bot=bot,
                chat_id=chat_id,
                user_id=user_id,
                text=(
                    f"{analysis_title}"
                    "✅ Подсчет завершен.\n\n"
                    f"Итог: <b>{total_text}</b>\n"
                    f"{objects_text}"
                ),
                reply_markup=main_menu_keyboard(),
                ui_state=ui_state,
            )
            return

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@router.message(CountStates.waiting_photo, F.text)
@router.message(CountStates.waiting_photo)
async def block_non_photo_during_count(
    message: Message,
    bot: Bot,
    ui_state: UIStateStore,
) -> None:
    await _safe_delete_user_message(message)
    await _render_existing_or_new(
        bot=bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        text=(
            "Жду фотографию.\n"
            "Отправьте фото или нажмите <b>⬅️ В меню</b>.\n\n"
            f"{escape(ANALYSIS_DISCLAIMER)}"
        ),
        reply_markup=back_to_menu_keyboard(),
        ui_state=ui_state,
    )


@router.message(WalletStates.waiting_topup_amount, F.text)
async def receive_topup_amount(
    message: Message,
    state: FSMContext,
    bot: Bot,
    auth_store: AuthStore,
    backend_client: BackendClient,
    ui_state: UIStateStore,
) -> None:
    await _safe_delete_user_message(message)

    raw_amount = message.text.strip().replace(" ", "")
    if not raw_amount.isdigit():
        await _render_existing_or_new(
            bot=bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text="⚠️ Введите сумму цифрами.\nНапример: <b>500</b>",
            reply_markup=topup_amount_keyboard(),
            ui_state=ui_state,
        )
        return

    amount = int(raw_amount)
    if amount <= 0:
        await _render_existing_or_new(
            bot=bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text="⚠️ Сумма должна быть больше нуля.",
            reply_markup=topup_amount_keyboard(),
            ui_state=ui_state,
        )
        return

    session = await _get_session(auth_store, message.from_user.id)
    if not session:
        await _show_auth_required(
            bot=bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text="Нужна авторизация.\nНажмите <b>🔐 Авторизоваться</b>.",
            state=state,
            ui_state=ui_state,
        )
        return

    topup_result = await backend_client.topup_balance(session.token, amount)
    if topup_result.get("unauthorized"):
        await auth_store.delete_session(message.from_user.id)
        await _show_auth_required(
            bot=bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text="Сессия завершилась.\nНажмите <b>🔐 Авторизоваться</b>.",
            state=state,
            ui_state=ui_state,
        )
        return

    if not topup_result.get("ok"):
        await _render_existing_or_new(
            bot=bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text="⚠️ Не удалось пополнить баланс.\nПопробуйте еще раз.",
            reply_markup=topup_amount_keyboard(),
            ui_state=ui_state,
        )
        return

    await state.clear()
    added_text = _format_amount(topup_result.get("added"))
    balance_text = _format_amount(topup_result.get("balance"))
    await _render_existing_or_new(
        bot=bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        text=(
            "✅ Баланс пополнен.\n\n"
            f"Добавлено: <b>{added_text}</b>\n"
            f"Текущий баланс: <b>{balance_text}</b>"
        ),
        reply_markup=balance_keyboard(),
        ui_state=ui_state,
    )


@router.message(WalletStates.waiting_topup_amount)
async def block_non_text_during_topup(
    message: Message,
    bot: Bot,
    ui_state: UIStateStore,
) -> None:
    await _safe_delete_user_message(message)
    await _render_existing_or_new(
        bot=bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        text="💳 Введите сумму цифрами.\nНапример: <b>500</b>",
        reply_markup=topup_amount_keyboard(),
        ui_state=ui_state,
    )


@router.message(StateFilter(None), F.photo)
@router.message(StateFilter(None), F.text)
@router.message(StateFilter(None))
async def block_free_messages(
    message: Message,
    bot: Bot,
    auth_store: AuthStore,
    ui_state: UIStateStore,
) -> None:
    await _safe_delete_user_message(message)

    session = await auth_store.get_session(message.from_user.id)
    if session:
        text = "👇 Используйте кнопки: <b>🧮 Подсчет</b>, <b>🧾 История</b> или <b>💰 Баланс</b>."
        keyboard = main_menu_keyboard()
    else:
        text = "Нажмите <b>🔐 Авторизоваться</b>, чтобы продолжить."
        keyboard = auth_keyboard()

    await _render_existing_or_new(
        bot=bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        text=text,
        reply_markup=keyboard,
        ui_state=ui_state,
    )
