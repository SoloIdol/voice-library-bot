import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineQueryResultCachedAudio

API_TOKEN = "8712123008:AAHiO9cEOT_Qkghgb7JpsnzReKXVa1oFNGg"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ВСТАВЛЕН ТВОЙ САМЫЙ СВЕЖИЙ FILE_ID С ПОСЛЕДНЕГО СКРИНШОТА ---
AUDIO_DATABASE = [
    {
        "id": "1",
        "title": "Семья",
        "file_id": "CQACAgQAAxkBAAMLanMxIZ_GTCJ0Z-cP7tk3oLM1HyoAA1wbAAILZJhTRz-4AnVzF9A9BA",
        "performer": "Хохол"
    },
]

# 1. Хэндлер для получения file_id и типа
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


# 2. Чистый инлайн-хэндлер
@dp.inline_query()
async def inline_query_handler(query: types.InlineQuery):
    text = query.query.strip().lower()
    results = []

    for item in AUDIO_DATABASE:
        if not text or text in item["title"].lower():
            # Гарантируем, что title не будет пустым!
            title_text = item.get("title") or "Аудиозапись"
            
            results.append(
                InlineQueryResultCachedAudio(
                    id=str(item["id"]),
                    audio_file_id=item["file_id"],
                    title=title_text,
                    performer=item.get("performer", "Бот")
                )
            )

    await query.answer(results, cache_time=0, is_personal=True)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
