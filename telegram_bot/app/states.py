from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    waiting_login = State()
    waiting_password = State()


class CountStates(StatesGroup):
    waiting_photo = State()


class WalletStates(StatesGroup):
    waiting_topup_amount = State()
