import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineQueryResultCachedAudio

API_TOKEN = "8712123008:AAHiO9cEOT_Qkghgb7JpsnzReKXVa1oFNGg"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# База данных с актуальным file_id
AUDIO_DATABASE = [
    {
        "id": "1",
        "title": "Семья",
        "file_id": "CQACAgQAAxkBAAMJanMtE5MeIVs04_f2M1iXdaZV4AkAAlObAAILZJhTUcybH1D6yJY9BA",
        "performer": "Хохол"
    },
]

# 1. Хэндлер получения file_id при отправке файла боту в ЛС
@dp.message(F.audio | F.voice | F.document)
async def get_audio_file_id(message: types.Message):
    file_id = None
    if message.audio:
        file_id = message.audio.file_id
    elif message.voice:
        file_id = message.voice.file_id
    elif message.document:
        file_id = message.document.file_id

    await message.reply(f"Ваш file_id:\n<code>{file_id}</code>", parse_mode="HTML")


# 2. Инлайн хэндлер с использованием CachedAudio
@dp.inline_query()
async def inline_query_handler(query: types.InlineQuery):
    text = query.query.strip().lower()
    results = []

    for item in AUDIO_DATABASE:
        if not text or text in item["title"].lower():
            results.append(
                InlineQueryResultCachedAudio(
                    id=item["id"],
                    audio_file_id=item["file_id"],
                    title=item["title"],
                    performer=item.get("performer", "")
                )
            )

    await query.answer(results, cache_time=0, is_personal=True)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
