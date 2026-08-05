import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineQueryResultCachedDocument


# ============================================================
# НАСТРОЙКИ
# ============================================================

API_TOKEN = "ВСТАВЬ_СЮДА_СВОЙ_ТОКЕН"


# ============================================================
# БАЗА ФАЙЛОВ
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
# BOT
# ============================================================

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# ============================================================
# ПОЛУЧЕНИЕ FILE_ID
# ============================================================

@dp.message(F.audio | F.voice | F.document)
async def get_audio_file_id(message: types.Message):

    if message.audio:
        file_type = "AUDIO"
        file_id = message.audio.file_id

    elif message.voice:
        file_type = "VOICE"
        file_id = message.voice.file_id

    elif message.document:
        file_type = "DOCUMENT"
        file_id = message.document.file_id

    else:
        file_type = "UNKNOWN"
        file_id = "N/A"

    text = (
        f"Тип файла: <b>{file_type}</b>\n"
        f"file_id:\n"
        f"<code>{file_id}</code>"
    )

    await message.reply(
        text,
        parse_mode="HTML",
    )


# ============================================================
# INLINE QUERY
# ============================================================

@dp.inline_query()
async def inline_query_handler(query: types.InlineQuery):

    search_text = query.query.strip().lower()

    results = []

    for item in AUDIO_DATABASE:

        # Получаем данные
        item_id = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        file_id = str(item.get("file_id", "")).strip()

        # Не добавляем битые записи
        if not item_id:
            continue

        if not title:
            continue

        if not file_id:
            continue

        # Поиск по названию
        if search_text:
            if search_text not in title.lower():
                continue

        # ====================================================
        # ВАЖНО:
        # Используем CachedDocument вместо CachedAudio.
        #
        # Это позволяет избежать AUDIO_TITLE_EMPTY.
        # ====================================================

        results.append(
            InlineQueryResultCachedDocument(
                id=f"{item_id}_file",
                title=title,
                document_file_id=file_id,
            )
        )

    try:

        await query.answer(
            results=results,
            cache_time=0,
            is_personal=True,
        )

        logger.info(
            "Inline query обработан: '%s', результатов: %d",
            query.query,
            len(results),
        )

    except Exception as error:

        logger.exception(
            "Ошибка при ответе на inline query: %s",
            error,
        )


# ============================================================
# ЗАПУСК
# ============================================================

async def main():

    logger.info("Запуск бота...")

    # Удаляем webhook, если он когда-либо использовался.
    # Старые ожидающие обновления удаляем.
    await bot.delete_webhook(
        drop_pending_updates=True
    )

    logger.info("Polling запущен.")

    try:

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )

    finally:

        await bot.session.close()

        logger.info("Бот остановлен.")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        logger.info(
            "Бот остановлен пользователем."
        )
