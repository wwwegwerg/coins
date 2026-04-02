from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def auth_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Авторизоваться", callback_data="auth:start")],
        ]
    )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧮 Подсчет", callback_data="menu:count")],
            [InlineKeyboardButton(text="🧾 История", callback_data="menu:history")],
            [InlineKeyboardButton(text="💰 Баланс", callback_data="menu:balance")],
        ]
    )


def auth_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="auth:cancel")],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:back")],
        ]
    )


def history_keyboard(
    page: int,
    total: int,
    has_image: bool,
    has_objects: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀", callback_data=f"history:page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total}", callback_data="history:noop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton(text="▶", callback_data=f"history:page:{page + 1}"))
    rows.append(nav)

    if has_image:
        rows.append([InlineKeyboardButton(text="🖼 Показать фото", callback_data=f"history:image:{page}")])
    if has_objects:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🧩 Вырезки объектов",
                    callback_data=f"history:objects:{page}",
                )
            ]
        )

    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:back")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def history_object_keyboard(page: int, index: int, total: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    nav: list[InlineKeyboardButton] = []
    if index > 0:
        nav.append(
            InlineKeyboardButton(
                text="◀",
                callback_data=f"history:object:{page}:{index - 1}",
            )
        )
    nav.append(InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data="history:noop"))
    if index < total - 1:
        nav.append(
            InlineKeyboardButton(
                text="▶",
                callback_data=f"history:object:{page}:{index + 1}",
            )
        )
    rows.append(nav)
    rows.append([InlineKeyboardButton(text="🧾 К анализу", callback_data=f"history:page:{page}")])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:back")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def balance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить", callback_data="wallet:topup")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:back")],
        ]
    )


def topup_amount_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="wallet:cancel")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:back")],
        ]
    )
