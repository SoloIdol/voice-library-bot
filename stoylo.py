import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineQueryResultCachedAudio, InlineQueryResultCachedVoice

API_TOKEN = "8712123008:AAHiO9cEOT_Qkghgb7JpsnzReKXVa1oFNGg"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

AUDIO_DATABASE = [
    {
        "id": "1",
        "title": "Семья",
        "file_id": "CQACAgQAAxkBAAMGanMpdRHhf8vhQcCtKLiJ4Vv6v08AAIibAAILZhTu3qt711LShI9BA",
        "performer": "Хохол"
    },
]

# Хэндлер ловит и audio, и voice, и document (mp3)
@dp.message(F.audio | F.voice | F.document)
async def get_audio_file_id(message: types.Message):
    file_id = None
    if message.audio:
        file_id = message.audio.file_id
    elif message.voice:
        file_id = message.voice.file_id
    elif message.document:
        file_id = message.document.file_id

    # Используем MarkdownV2 или HTML корректно
    await message.reply(f"Ваш file_id:\n<code>{file_id}</code>", parse_mode="HTML")


@dp.inline_query()
async def inline_query_handler(query: types.InlineQuery):
    text = query.query.strip().lower()
    results = []

    for item in AUDIO_DATABASE:
        # Если запрос пустой или совпадает с названием
        if not text or text in item["title"].lower():
            results.append(
                InlineQueryResultCachedAudio(
                    id=item["id"],
                    audio_file_id=item["file_id"],
                    title=item["title"],
                    performer=item.get("performer", "")
                )
            )

    # answer должен вызываться всегда, даже если results пустой
    await query.answer(results, cache_time=1, is_personal=True)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
