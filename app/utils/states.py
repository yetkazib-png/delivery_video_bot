from aiogram.fsm.state import State, StatesGroup


class RegisterFlow(StatesGroup):
    waiting_first_name = State()
    waiting_last_name = State()
    waiting_phone = State()
    waiting_car_plate = State()


class ReasonFlow(StatesGroup):
    waiting_reason = State()


class VideoFlow(StatesGroup):
    waiting_video = State()
