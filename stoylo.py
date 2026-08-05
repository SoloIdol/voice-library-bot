import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    InlineQueryResultCachedAudio,
    InlineQueryResultCachedDocument,
    InlineQueryResultCachedVoice
)

API_TOKEN = "8712123008:AAHiO9cEOT_Qkghgb7JpsnzReKXVa1oFNGg"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# База данных
AUDIO_DATABASE = [
    {
        "id": "1",
        "title": "Семья",
        "file_id": "CQACAgQAAxkBAAMJanMtE5MeIVs04_f2M1iXdaZV4AkAAlObAAILZJhTUcybH1D6yJY9BA",
        "performer": "Хохол"
    },
]

# 1. ХЭНДЛЕР ДЛЯ ВЫЯСНЕНИЯ ТОЧНОГО ТИПА ФАЙЛА И ЕГО FILE_ID
@dp.message(F.audio | F.voice | F.document)
async def get_audio_file_id(message: types.Message):
    if message.audio:
        f_type = "AUDIO"
        f_id = message.audio.file_id
    elif message.voice:
        f_type = "VOICE"
        f_id = message.voice.file_id
    elif message.document:
        f_type = "DOCUMENT"
        f_id = message.document.file_id
    else:
        f_type = "UNKNOWN"
        f_id = "N/A"

    text = f"Тип файла: <b>{f_type}</b>\nfile_id:\n<code>{f_id}</code>"
    await message.reply(text, parse_mode="HTML")


# 2. ИНЛАЙН ХЭНДЛЕР С ФОЛЛБЕКОМ (пробуем отдавать файл через Document и Audio)
@dp.inline_query()
async def inline_query_handler(query: types.InlineQuery):
    text = query.query.strip().lower()
    results = []

    for item in AUDIO_DATABASE:
        if not text or text in item["title"].lower():
            # Добавляем варианты выдачи (Telegram сам выберет или выведет карточки)
            results.append(
                InlineQueryResultCachedAudio(
                    id=f"{item['id']}_audio",
                    audio_file_id=item["file_id"],
                    title=f"{item['title']} (Аудио)",
                    performer=item.get("performer", "")
                )
            )
            results.append(
                InlineQueryResultCachedDocument(
                    id=f"{item['id']}_doc",
                    title=f"{item['title']} (Файл)",
                    document_file_id=item["file_id"]
                )
            )

    await query.answer(results, cache_time=0, is_personal=True)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
