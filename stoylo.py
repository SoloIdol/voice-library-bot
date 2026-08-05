import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineQueryResultCachedAudio
from aiogram.exceptions import TelegramConflictError


# ============================================================
# НАСТРОЙКИ
# ============================================================

API_TOKEN = "8712123008:AAHiO9cEOT_Qkghgb7JpsnzReKXVa1oFNGg"


# ============================================================
# БАЗА АУДИО
# ============================================================

AUDIO_DATABASE = [
    {
        "id": "1",
        "title": "Семья",
        "file_id": "CQACAgQAAxkBAAMLanMxIZ_GTCJ0Z-cP7tk3oLM1HyoAAlwbAAILZJhTRZ-4AnVzF9A9BA",
        "performer": "Хохол",
    },
]


# ============================================================
# ЛОГИРОВАНИЕ
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# BOT / DISPATCHER
# ============================================================

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# ============================================================
# ПОЛУЧЕНИЕ FILE_ID
# ============================================================

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

    text = (
        f"Тип файла: <b>{f_type}</b>\n"
        f"file_id:\n"
        f"<code>{f_id}</code>"
    )

    await message.reply(
        text,
        parse_mode="HTML"
    )


# ============================================================
# INLINE SEARCH
# ============================================================

@dp.inline_query()
async def inline_query_handler(query: types.InlineQuery):

    search_text = query.query.strip().lower()

    results = []

    for item in AUDIO_DATABASE:

        title = item.get("title", "").strip()

        if not title:
            continue

        # Если пользователь ничего не ввёл —
        # показываем все аудио.
        #
        # Если ввёл текст —
        # ищем по названию.
        if search_text and search_text not in title.lower():
            continue

        file_id = item.get("file_id", "").strip()

        if not file_id:
            continue

        performer = item.get("performer", "").strip()

        # ВАЖНО:
        # Используем только CachedAudio.
        #
        # Не отправляем этот file_id одновременно
        # как Document.
        results.append(
            InlineQueryResultCachedAudio(
                id=f"{item['id']}_audio",
                audio_file_id=file_id,
                title=title,
                performer=performer or "Хохол",
            )
        )

    try:
        await query.answer(
            results=results,
            cache_time=0,
            is_personal=True,
        )

    except Exception as e:
        logger.exception(
            "Ошибка при ответе на inline query: %s",
            e
        )


# ============================================================
# ЗАПУСК
# ============================================================

async def main():

    logger.info("Запуск бота...")

    # Удаляем старые webhook/update queue.
    # Это важно, если раньше бот запускался другим способом.
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Polling запущен.")

    try:

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )

    except TelegramConflictError:

        logger.error(
            "TELEGRAM CONFLICT: "
            "уже запущен другой экземпляр этого бота. "
            "Остановите старый контейнер/процесс."
        )

        raise

    finally:

        await bot.session.close()

        logger.info("Бот остановлен.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную.")
