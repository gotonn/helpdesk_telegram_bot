import asyncio
import os
import csv
import requests
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, 
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    ReplyKeyboardRemove, 
    FSInputFile, 
    URLInputFile, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database

BOT_TOKEN = "8734454151:AAEtZ5qyxEVnkArWDrwgHDKbd0XxS-sBQ2c"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🛠 Створити заявку")],[KeyboardButton(text="📋 Мої заявки"), KeyboardButton(text="📊 Завантажити звіт")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Оберіть дію нижче..."
)

equip_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💻 Ноутбук/ПК"), KeyboardButton(text="🖨 Принтер")],[KeyboardButton(text="🌐 Мережа/Інтернет"), KeyboardButton(text="❌ Скасувати")]
    ],
    resize_keyboard=True
)

class TicketState(StatesGroup):
    equipment = State()
    cabinet = State()
    description = State()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    database.add_user(message.from_user.id, message.from_user.full_name)
    await message.answer(
        f"Вітаю, {message.from_user.full_name}! 👋\n"
        f"Це система технічної підтримки компанії.\nОберіть потрібну дію:",
        reply_markup=main_kb
    )

@dp.message(F.text == "🛠 Створити заявку")
async def start_ticket(message: Message, state: FSMContext):
    await message.answer("Що саме зламалося? Оберіть з варіантів:", reply_markup=equip_kb)
    await state.set_state(TicketState.equipment)

@dp.message(F.text == "❌ Скасувати")
async def cancel_ticket(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Створення заявки скасовано.", reply_markup=main_kb)

@dp.message(TicketState.equipment)
async def process_equipment(message: Message, state: FSMContext):
    await state.update_data(equipment=message.text)
    await message.answer("Напишіть номер вашого кабінету (наприклад: 405):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(TicketState.cabinet)

@dp.message(TicketState.cabinet)
async def process_cabinet(message: Message, state: FSMContext):
    await state.update_data(cabinet=message.text)
    await message.answer("Коротко опишіть проблему:")
    await state.set_state(TicketState.description)

@dp.message(TicketState.description)
async def process_description(message: Message, state: FSMContext):
    data = await state.get_data()
    
    ticket_id = database.add_ticket(message.from_user.id, data['equipment'], data['cabinet'], message.text)
    await state.clear()

    api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=Ticket_ID_{ticket_id}"
    qr_photo = URLInputFile(api_url)

    await message.answer_photo(
        photo=qr_photo,
        caption=f"✅ Заявку №{ticket_id} успішно створено!\nПокажіть цей QR-код майстру.",
        reply_markup=main_kb
    )

@dp.message(F.text == "📋 Мої заявки")
async def view_my_tickets(message: Message):
    tickets = database.get_user_tickets(message.from_user.id)
    if not tickets:
        await message.answer("У вас немає активних заявок 🤷‍♂️")
        return
        
    await message.answer("<b>Ваші останні заявки:</b>", parse_mode="HTML")
    
    for t in tickets:
        ticket_id = t[0]
        status = t[3]
        text = f"🔧 <b>{t[1]}</b> (Каб. {t[2]})\nСтатус: {status}"
        
        inline_kb = None
        if "Відкрита" in status:
            inline_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Позначити як вирішено", callback_data=f"close_{ticket_id}")],[InlineKeyboardButton(text="🗑 Видалити заявку", callback_data=f"delete_{ticket_id}")]
            ])
            
        await message.answer(text, parse_mode="HTML", reply_markup=inline_kb)

@dp.callback_query(F.data.startswith("close_"))
async def close_ticket_callback(callback: CallbackQuery):
    ticket_id = int(callback.data.split("_")[1])
    database.close_ticket(ticket_id) 
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n<i>Оновлено: Вирішено ✅</i>", 
        parse_mode="HTML",
        reply_markup=None
    )
    await callback.answer("Статус заявки оновлено!")

@dp.callback_query(F.data.startswith("delete_"))
async def delete_ticket_callback(callback: CallbackQuery):
    ticket_id = int(callback.data.split("_")[1])
    database.delete_ticket(ticket_id) 
    
    await callback.message.edit_text(
        f"<i>🚫 Заявку №{ticket_id} було назавжди видалено з бази даних.</i>", 
        parse_mode="HTML",
        reply_markup=None
    )
    await callback.answer("Заявку видалено!")

@dp.message(F.text == "📊 Завантажити звіт")
async def export_tickets(message: Message):
    await message.answer("⏳ Генерую звіт, зачекайте...")
    tickets = database.get_all_tickets()
    
    filename = "helpdesk_report.csv"
    
    with open(filename, mode='w', encoding='utf-8-sig', newline='') as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow(['ID Заявки', 'Обладнання', 'Кабінет', 'Опис', 'Статус'])
        for t in tickets:
            writer.writerow([t[0], t[1], t[2], t[3], t[4]])
            
    document = FSInputFile(filename)
    await message.answer_document(document, caption="📊 Ось ваш звіт по всіх заявках!")
    os.remove(filename)

async def healthcheck_handler(request):
    return web.Response(text="Bot is running.")

async def main():
    app = web.Application()
    app.router.add_get('/', healthcheck_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    print("Service started.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
