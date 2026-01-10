from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from app.keyboards.common import onboarding_kb, main_menu, contact_kb
from app.utils.states import RegisterFlow
from app.db.database import get_user, upsert_user

router = Router()

TUTORIAL_VIDEO_FILE_ID = "BAACAgIAAxkBAAIBGGlc8yiYUdGDlo0Ur3xXcrodb7WfAAJdiQACsWLoSthlwsIzTugsOAQ"

TUTORIAL_TEXT = (
    "Хурматли хайдовчи экспедиторлар корхонамиз қоидалари билан албатта танишиб чиқинг\n\n"
    "1) Боғча номерини аниқ киритинг. Накладнойга получил деган жойга қабул қилиб олган боғча масъул фамилияси, исми ва имзосини албатта қўйдиринг\n"
    "2) Камерага сифатли олинг. Думалоқ видео мумкин эмас\n"
    "3) Акт қоғозини тиниқ ва тўлиқ кўрсатинг. Видеога олишдаги аввал телефон камерасини тозалаб олинг\n"
    "4) Камерага шошилмай ва силкитиб ташламай барча маҳсулотларни олинг. Маҳсулотларни камерага овоз чиқариб сони ва хажмини ўқинг\n"
    "5) Агар махсулотимиз сифатига богча томондан эьтироз бўлса шу маҳсулотни камерага олинг ва логистика рахбарига юборинг\n"
    "6) Камерага олиш инструкциясини кўринг\n"
)


@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if user:
        await state.clear()
        await message.answer("Bosh menyu:", reply_markup=main_menu())
        return

    # 1) Video
    await message.answer_video(TUTORIAL_VIDEO_FILE_ID)

    # 2) Matn (qoidalar/qo'llanma)
    await message.answer(TUTORIAL_TEXT)

    # 3) Matndan keyin tugma
    await message.answer("Davom etish uchun tugmani bosing:", reply_markup=onboarding_kb())


@router.callback_query(F.data == "onboard_ok")
async def onboard_ok(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Исмингизни ёзинг:")
    await state.set_state(RegisterFlow.waiting_first_name)
    await call.answer()


@router.message(RegisterFlow.waiting_first_name)
async def reg_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text.strip())
    await message.answer("Фамилиянгизни ёзинг:")
    await state.set_state(RegisterFlow.waiting_last_name)


@router.message(RegisterFlow.waiting_last_name)
async def reg_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text.strip())

    # Telefonni contact orqali so'raymiz
    await message.answer(
        "📞 Телефон рақамингизни юборинг (пастдаги тугмани босинг):",
        reply_markup=contact_kb()
    )
    await state.set_state(RegisterFlow.waiting_phone)


@router.message(RegisterFlow.waiting_phone, F.contact)
async def reg_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)

    await message.answer(
        "🚗 Автомашина номерини киритинг (масалан: 01A123BC):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RegisterFlow.waiting_car_plate)


@router.message(RegisterFlow.waiting_phone)
async def reg_phone_wrong(message: Message):
    await message.answer("Илтимос, телефон рақамни айнан тугма орқали юборинг (Contact).")


@router.message(RegisterFlow.waiting_car_plate)
async def reg_car_plate(message: Message, state: FSMContext):
    car_plate = message.text.strip().upper()

    if len(car_plate) < 5:
        await message.answer("Автомашина номерини тўғри киритинг (масалан: 01A123BC).")
        return

    data = await state.get_data()
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    phone = data.get("phone", "").strip()

    # upsert_user endi phone va car_plate ham qabul qiladi (database.py ni keyin yangilaymiz)
    await upsert_user(message.from_user.id, first_name, last_name, phone, car_plate)

    await state.clear()
    await message.answer(
        "✅ Рўйхатдан ўтдингиз:\n"
        f"👤 {first_name} {last_name}\n"
        f"📞 {phone}\n"
        f"🚗 {car_plate}",
        reply_markup=main_menu()
    )
