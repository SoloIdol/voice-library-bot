import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineQueryResultCachedAudio

API_TOKEN = "8712123008:AAHiO9cEOT_Qkghgb7JpsnzReKXVa1oFNGg"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ АУДИО (СЮДА ВСТАВЛЯЙТЕ ПОЛУЧЕННЫЕ FILE_ID) ---
AUDIO_DATABASE = [
    {
        "id": "1",
        "title": "Семья",
        "file_id": "CQACAgQAAxkBAAMGanMpdRHhf8vhQcCtKLiJ4Vv6v08AAIibAAILZhTu3qt711LShI9BA",,
        "performer": "Хохол"
    },
    # Добавляйте новые аудио по аналогии:
    # {
    #     "id": "2",
    #     "title": "Вторая фразка",
    #     "file_id": "ДРУГОЙ_FILE_ID",
    #     "performer": "Хохол"
    # },
]

# --- 1. ХЭНДЛЕР ДЛЯ ПОЛУЧЕНИЯ FILE_ID ОТ БОТА ---
# Просто отправьте файл .mp3 боту в ЛС, и он пришлёт вам file_id
@dp.message(F.audio)
async def get_audio_file_id(message: types.Message):
    file_id = message.audio.file_id
    await message.reply(f"Ваш file_id:\n`{file_id}`", parse_mode="HTML")


# --- 2. ИНЛАЙН-РЕЖИМ (ПОИСК И ВЫДАЧА ЗВУКОВ) ---
@dp.inline_query()
async def inline_query_handler(query: types.InlineQuery):
    text = query.query.lower()
    results = []

    for item in AUDIO_DATABASE:
        # Фильтрация по поисковому запросу
        if text in item["title"].lower():
            results.append(
                InlineQueryResultCachedAudio(
                    id=item["id"],
                    audio_file_id=item["file_id"],
                    title=item["title"],
                    performer=item.get("performer", "")
                )
            )

    await query.answer(results, cache_time=1, is_personal=True)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
