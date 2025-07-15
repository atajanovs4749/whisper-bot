import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
from dotenv import load_dotenv
from utils.whisper_worker import transcribe_audio  # AI funksiyasi

import json

# ======================= DATABASE FUNCTIONS =========================
DB_PATH = "users.json"

def load_users():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def set_user_limit(user_id: str, limit: int):
    data = load_users()
    data[user_id] = {"used": 0, "limit": limit}
    save_users(data)

def can_use(user_id: str):
    data = load_users()
    user = data.get(user_id)
    if not user:
        return True  # 1 martalik bepul foydalanish
    return user["used"] < user["limit"]

def increment_usage(user_id: str):
    data = load_users()
    if user_id in data:
        data[user_id]["used"] += 1
        save_users(data)

# .env dan tokenni olish
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 60020965
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
# TEMP papka mavjudligini tekshirib yaratish
if not os.path.exists("temp"):
    os.makedirs("temp")
# Loglar
logging.basicConfig(level=logging.INFO)

# Bot va dispatcher
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# ======================= START HANDLER =========================
@dp.message(F.text == "/start")
async def start_handler(message: types.Message):
    text = (
        "<b>Ovozdan matnga aylantiruvchi botga xush kelibsiz!</b>\n\n"
        "<b>1 martalik bepul foydalanish mavjud.</b>\n"
        "<b>Tariflar:</b>\n"
        "1) 5 ta audio – 15 000 so'm\n"
        "2) 9 ta audio – 25 000 so'm\n\n"
        "<b>Qoidalar:</b>\n"
        "- Audio 2 daqiqadan oshmasin.\n"
        "- Ovozingiz tiniq eshitilsin.\n"
        "- Har bir audio faqat bir martalik xizmatni egallaydi."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="15 000 so'm — 5 audio", callback_data="tarif_5")],
        [InlineKeyboardButton(text="25 000 so'm — 9 audio", callback_data="tarif_9")]
    ])
    await message.answer(text, reply_markup=keyboard)

# ======================= CALLBACK HANDLER (Tarif tanlash) =========================
@dp.callback_query(F.data.startswith("tarif_"))
async def tarif_callback(call: types.CallbackQuery):
    tarif = call.data.split("_")[1]
    tarif_text = "15 000 so'm — 5 audio" if tarif == "5" else "25 000 so'm — 9 audio"

    await bot.send_message(
        ADMIN_ID,
        f"[TO‘LOV KUTILMOQDA]\n\n"
        f"Foydalanuvchi: <code>{call.from_user.id}</code>\n"
        f"Tanlangan tarif: {tarif_text}"
    )

    await call.message.answer(
        f"✅ Tanlangan tarif: <b>{tarif_text}</b>\n\n"
        "Iltimos, to‘lov chek rasmini yuboring. Admin tasdiqlaganidan so‘ng foydalanishingiz mumkin.",
        reply_markup=None
    )
    await call.answer()

# ======================= ADMIN TASDIQLASH =========================
@dp.message(F.text.startswith("/tasdiq"))
async def approve_payment(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.strip().split()
    if len(parts) != 3:
        await message.answer("❌ Foydalanish: /tasdiq user_id limit\nMisol: /tasdiq 123456789 5")
        return

    user_id, limit = parts[1], int(parts[2])
    set_user_limit(user_id, limit)
    await bot.send_message(int(user_id), f"✅ To‘lov tasdiqlandi. Sizga {limit} ta audio imkoniyati berildi.")
    await message.answer("✅ Tasdiq muvaffaqiyatli amalga oshirildi.")
# ======================= VOICE HANDLER =========================
@dp.message(F.voice)
async def voice_handler(message: types.Message):
    user_id = str(message.from_user.id)
    duration = message.voice.duration

    if duration > 120:
        await message.answer("⚠️ Audio maksimal 2 daqiqa bo'lishi kerak. Iltimos, qisqaroq yuboring.")
        return

    if not can_use(user_id):
        await message.answer("‼️ Sizning imkoniyatingiz tugagan. Iltimos, tarif tanlab, to‘lov qiling.")
        return

    await message.answer("⏳ Jarayon boshlandi. Iltimos, 1 daqiqa kuting...")

    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path

    voice_ogg = f"temp/{user_id}.ogg"
    await bot.download_file(file_path, voice_ogg)

    matn = await transcribe_audio(voice_ogg)
    await message.answer(f"📄 Natija:\n{matn}")
    increment_usage(user_id)

# ======================= BOT COMMANDS =========================
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni boshlash"),
        BotCommand(command="help", description="Foydalanish qoidalari"),
    ]
    await bot.set_my_commands(commands)

# ======================= MAIN (WEBHOOK) =========================
async def main():
    await set_bot_commands(bot)
    await bot.set_webhook(url=WEBHOOK_URL)

    app = web.Application()
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path="/webhook")

    return app

if __name__ == '__main__':
    web.run_app(main(), host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

