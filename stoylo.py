import asyncio
import logging
import os
import tempfile

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineQueryResultCachedVoice
from aiogram.exceptions import TelegramConflictError


# ============================================================
# НАСТРОЙКИ
# ============================================================

API_TOKEN = "8712123008:AAHiO9cEOT_Qkghgb7JpsnzReKXVa1oFNGg"

# Пока 0 = разрешить обработку файлов всем.
# После теста лучше вписать сюда свой Telegram ID.
ADMIN_ID = 0


# ============================================================
# БАЗА ГОЛОСОВЫХ
# ============================================================

VOICE_DATABASE = []


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
# ПРОВЕРКА АДМИНА
# ============================================================

def is_admin(message: types.Message) -> bool:
    if ADMIN_ID == 0:
        return True

    return message.from_user.id == ADMIN_ID


# ============================================================
# START
# ============================================================

@dp.message(F.text == "/start")
async def start_handler(message: types.Message):

    await message.answer(
        "🎤 <b>Бот голосовых сообщений</b>\n\n"
        "Отправь мне аудиофайл.\n"
        "Я преобразую его в настоящее Telegram-голосовое "
        "сообщение и сохраню его для inline-поиска.\n\n"
        "<b>Команды:</b>\n"
        "/id — узнать свой Telegram ID\n"
        "/list — список голосовых\n"
        "/clear — очистить базу",
        parse_mode="HTML",
    )


# ============================================================
# ID
# ============================================================

@dp.message(F.text == "/id")
async def id_handler(message: types.Message):

    await message.answer(
        f"Твой Telegram ID:\n"
        f"<code>{message.from_user.id}</code>",
        parse_mode="HTML",
    )


# ============================================================
# ОБРАБОТКА AUDIO
# ============================================================

@dp.message(F.audio)
async def audio_handler(message: types.Message):

    if not is_admin(message):
        await message.answer("Нет доступа.")
        return

    if not message.audio:
        return

    original_name = message.audio.file_name or "Голосовое"

    title = original_name

    if "." in title:
        title = title.rsplit(".", 1)[0]

    title = title.strip()

    if not title:
        title = "Голосовое"

    status = await message.answer(
        f"⏳ Конвертирую "
        f"<b>{title}</b> в голосовое...",
        parse_mode="HTML",
    )

    input_path = None
    output_path = None

    try:

        # ====================================================
        # СКАЧИВАЕМ ФАЙЛ ИЗ TELEGRAM
        # ====================================================

        telegram_file = await bot.get_file(
            message.audio.file_id
        )

        input_temp = tempfile.NamedTemporaryFile(
            suffix=".input",
            delete=False,
        )

        input_path = input_temp.name
        input_temp.close()

        await bot.download_file(
            telegram_file.file_path,
            input_path,
        )

        logger.info(
            "Файл скачан: %s",
            input_path,
        )

        # ====================================================
        # ВЫХОДНОЙ OGG
        # ====================================================

        output_temp = tempfile.NamedTemporaryFile(
            suffix=".ogg",
            delete=False,
        )

        output_path = output_temp.name
        output_temp.close()

        # ====================================================
        # FFMPEG
        # ====================================================

        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            input_path,

            # Mono
            "-ac",
            "1",

            # Telegram Voice обычно использует Opus
            "-c:a",
            "libopus",

            # Хорошее качество при небольшом размере
            "-b:a",
            "48k",

            output_path,

            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:

            ffmpeg_error = stderr.decode(
                errors="ignore"
            )

            logger.error(
                "FFmpeg error:\n%s",
                ffmpeg_error,
            )

            raise RuntimeError(
                "FFmpeg не смог преобразовать файл."
            )

        logger.info(
            "Конвертация завершена: %s",
            output_path,
        )

        # ====================================================
        # ОТПРАВЛЯЕМ КАК TELEGRAM VOICE
        # ====================================================

        with open(output_path, "rb") as voice_file:

            sent_message = await bot.send_voice(
                chat_id=message.chat.id,
                voice=voice_file,
                caption=f"🎤 {title}",
            )

        # ====================================================
        # ПОЛУЧАЕМ НАСТОЯЩИЙ VOICE FILE_ID
        # ====================================================

        if not sent_message.voice:

            raise RuntimeError(
                "Telegram не вернул объект voice."
            )

        voice_file_id = sent_message.voice.file_id

        logger.info(
            "VOICE file_id получен: %s",
            voice_file_id,
        )

        # ====================================================
        # СОХРАНЯЕМ
        # ====================================================

        global VOICE_DATABASE

        # Если такое название уже есть —
        # заменяем старую запись.

        VOICE_DATABASE = [
            item
            for item in VOICE_DATABASE
            if item["title"].lower()
            != title.lower()
        ]

        VOICE_DATABASE.append(
            {
                "id": str(len(VOICE_DATABASE) + 1),
                "title": title,
                "voice_file_id": voice_file_id,
            }
        )

        # ====================================================
        # ОТВЕТ
        # ====================================================

        await status.edit_text(
            "✅ <b>Готово!</b>\n\n"
            f"Название: <b>{title}</b>\n\n"
            "Теперь попробуй:\n"
            f"<code>@твой_бот {title}</code>",
            parse_mode="HTML",
        )

        await message.answer(
            "VOICE file_id:\n"
            f"<code>{voice_file_id}</code>",
            parse_mode="HTML",
        )

    except Exception as error:

        logger.exception(
            "Ошибка обработки аудио"
        )

        await status.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            f"<code>{str(error)}</code>",
            parse_mode="HTML",
        )

    finally:

        # ====================================================
        # УДАЛЯЕМ ВРЕМЕННЫЕ ФАЙЛЫ
        # ====================================================

        if input_path:
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
            except Exception:
                pass

        if output_path:
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception:
                pass


# ============================================================
# ЕСЛИ ПРИСЛАЛИ УЖЕ ГОТОВОЕ VOICE
# ============================================================

@dp.message(F.voice)
async def voice_handler(message: types.Message):

    if not is_admin(message):
        await message.answer("Нет доступа.")
        return

    if not message.voice:
        return

    voice_file_id = message.voice.file_id

    title = "Голосовое"

    global VOICE_DATABASE

    VOICE_DATABASE.append(
        {
            "id": str(len(VOICE_DATABASE) + 1),
            "title": title,
            "voice_file_id": voice_file_id,
        }
    )

    await message.answer(
        "✅ Это уже настоящее Telegram Voice.\n\n"
        "VOICE file_id:\n"
        f"<code>{voice_file_id}</code>",
        parse_mode="HTML",
    )


# ============================================================
# LIST
# ============================================================

@dp.message(F.text == "/list")
async def list_handler(message: types.Message):

    if not VOICE_DATABASE:
        await message.answer(
            "База голосовых пока пустая."
        )
        return

    lines = [
        "🎤 <b>Голосовые:</b>",
        "",
    ]

    for index, item in enumerate(
        VOICE_DATABASE,
        start=1,
    ):

        lines.append(
            f"{index}. {item['title']}"
        )

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
    )


# ============================================================
# CLEAR
# ============================================================

@dp.message(F.text == "/clear")
async def clear_handler(message: types.Message):

    if not is_admin(message):
        await message.answer("Нет доступа.")
        return

    global VOICE_DATABASE

    VOICE_DATABASE.clear()

    await message.answer(
        "🗑 База голосовых очищена."
    )


# ============================================================
# INLINE
# ============================================================

@dp.inline_query()
async def inline_query_handler(
    query: types.InlineQuery
):

    search_text = query.query.strip().lower()

    results = []

    for item in VOICE_DATABASE:

        title = str(
            item.get("title", "")
        ).strip()

        voice_file_id = str(
            item.get("voice_file_id", "")
        ).strip()

        if not title:
            continue

        if not voice_file_id:
            continue

        if search_text:
            if search_text not in title.lower():
                continue

        results.append(
            InlineQueryResultCachedVoice(
                id=f"{item['id']}_voice",
                voice_file_id=voice_file_id,
                title=title,
            )
        )

    try:

        await query.answer(
            results=results,
            cache_time=0,
            is_personal=True,
        )

        logger.info(
            "Inline query '%s': %d результатов",
            query.query,
            len(results),
        )

    except Exception as error:

        logger.exception(
            "Ошибка inline query: %s",
            error,
        )


# ============================================================
# MAIN
# ============================================================

async def main():

    logger.info(
        "Запуск бота..."
    )

    # Убираем webhook и старые ожидающие updates.
    await bot.delete_webhook(
        drop_pending_updates=True
    )

    logger.info(
        "Polling запущен."
    )

    try:

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )

    except TelegramConflictError:

        logger.error(
            "Запущен другой экземпляр бота."
        )

        raise

    finally:

        await bot.session.close()

        logger.info(
            "Бот остановлен."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        logger.info(
            "Бот остановлен вручную."
        )
