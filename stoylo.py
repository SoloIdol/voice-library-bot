import asyncio
import logging
import os
import shutil
import tempfile

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    InlineQueryResultCachedVoice,
    FSInputFile,
)
from aiogram.exceptions import TelegramConflictError


# ============================================================
# НАСТРОЙКИ
# ============================================================

# Лучше хранить токен в Railway Variables.
# Railway -> Service -> Variables -> API_TOKEN
API_TOKEN = os.getenv("API_TOKEN")

# Пока 0 = разрешить обработку файлов всем.
# После теста впиши сюда свой Telegram ID.
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
# ПРОВЕРКА ТОКЕНА
# ============================================================

if not API_TOKEN:
    raise RuntimeError(
        "Переменная API_TOKEN не установлена. "
        "Добавь API_TOKEN в Railway Variables."
    )


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
# ПРОВЕРКА FFMPEG
# ============================================================

def check_ffmpeg():

    logger.info("=== ПРОВЕРКА FFMPEG ===")

    ffmpeg_path = shutil.which("ffmpeg")

    if ffmpeg_path is None:

        logger.error(
            "❌ FFMPEG НЕ НАЙДЕН В PATH"
        )

        return False

    logger.info(
        "✅ FFMPEG НАЙДЕН: %s",
        ffmpeg_path,
    )

    return True


# ============================================================
# ЭКРАНИРОВАНИЕ HTML
# ============================================================

def escape_html(text: str) -> str:

    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


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

        await message.answer(
            "Нет доступа."
        )

        return

    if not message.audio:
        return

    # ========================================================
    # НАЗВАНИЕ
    # ========================================================

    original_name = (
        message.audio.file_name
        or "Голосовое"
    )

    title = original_name

    if "." in title:

        title = title.rsplit(
            ".",
            1
        )[0]

    title = title.strip()

    if not title:
        title = "Голосовое"

    logger.info(
        "Получено аудио: %s",
        title,
    )

    status = await message.answer(
        f"⏳ Конвертирую "
        f"<b>{escape_html(title)}</b> "
        f"в голосовое...",
        parse_mode="HTML",
    )

    input_path = None
    output_path = None

    try:

        # ====================================================
        # ПРОВЕРЯЕМ FFMPEG
        # ====================================================

        if not check_ffmpeg():

            raise RuntimeError(
                "FFmpeg не найден в системе Railway."
            )

        # ====================================================
        # ПОЛУЧАЕМ TELEGRAM FILE
        # ====================================================

        telegram_file = await bot.get_file(
            message.audio.file_id
        )

        if not telegram_file.file_path:

            raise RuntimeError(
                "Telegram не вернул путь к файлу."
            )

        # ====================================================
        # СОЗДАЁМ ВРЕМЕННЫЙ INPUT
        # ====================================================

        input_temp = tempfile.NamedTemporaryFile(
            suffix=".input",
            delete=False,
        )

        input_path = input_temp.name

        input_temp.close()

        # ====================================================
        # СКАЧИВАЕМ AUDIO
        # ====================================================

        await bot.download_file(
            telegram_file.file_path,
            input_path,
        )

        logger.info(
            "Файл скачан: %s",
            input_path,
        )

        # ====================================================
        # СОЗДАЁМ ВЫХОДНОЙ OGG
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

        logger.info(
            "Начинаем конвертацию: %s -> %s",
            input_path,
            output_path,
        )

        process = await asyncio.create_subprocess_exec(

            "ffmpeg",

            "-y",

            "-i",
            input_path,

            # Telegram Voice — mono
            "-ac",
            "1",

            # Opus
            "-c:a",
            "libopus",

            # Битрейт
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
                "FFmpeg завершился с ошибкой:\n%s",
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
        # ПРОВЕРЯЕМ ЧТО ФАЙЛ СОЗДАН
        # ====================================================

        if not os.path.exists(output_path):

            raise RuntimeError(
                "FFmpeg завершился, "
                "но выходной файл не создан."
            )

        output_size = os.path.getsize(
            output_path
        )

        logger.info(
            "Размер OGG: %d bytes",
            output_size,
        )

        if output_size == 0:

            raise RuntimeError(
                "Полученный OGG-файл пустой."
            )

        # ====================================================
        # ОТПРАВЛЯЕМ КАК НАСТОЯЩИЙ TELEGRAM VOICE
        # ====================================================

        logger.info(
            "Отправляем OGG как Telegram Voice..."
        )

        # В aiogram 3.x нельзя передавать
        # обычный BufferedReader напрямую.
        #
        # Используем FSInputFile.

        voice_file = FSInputFile(
            output_path
        )

        sent_message = await bot.send_voice(

            chat_id=message.chat.id,

            voice=voice_file,

            caption=(
                f"🎤 {title}"
            ),
        )

        # ====================================================
        # ПОЛУЧАЕМ VOICE FILE_ID
        # ====================================================

        if not sent_message.voice:

            raise RuntimeError(
                "Telegram не вернул объект voice."
            )

        voice_file_id = (
            sent_message.voice.file_id
        )

        logger.info(
            "✅ VOICE file_id получен: %s",
            voice_file_id,
        )

        # ====================================================
        # СОХРАНЯЕМ В БАЗУ
        # ====================================================

        global VOICE_DATABASE

        # Удаляем старую запись с таким названием.

        VOICE_DATABASE = [
            item
            for item in VOICE_DATABASE
            if item["title"].lower()
            != title.lower()
        ]

        # Создаём новую запись.

        new_id = str(
            len(VOICE_DATABASE) + 1
        )

        VOICE_DATABASE.append(
            {
                "id": new_id,
                "title": title,
                "voice_file_id": voice_file_id,
            }
        )

        logger.info(
            "Добавлено голосовое: %s | %s",
            title,
            voice_file_id,
        )

        # ====================================================
        # ОБНОВЛЯЕМ STATUS
        # ====================================================

        safe_title = escape_html(
            title
        )

        await status.edit_text(
            "✅ <b>Готово!</b>\n\n"
            f"Название: <b>{safe_title}</b>\n\n"
            "Теперь попробуй inline-поиск:\n"
            f"<code>@твой_бот {safe_title}</code>",
            parse_mode="HTML",
        )

        # ====================================================
        # ПОКАЗЫВАЕМ FILE_ID
        # ====================================================

        safe_file_id = escape_html(
            voice_file_id
        )

        await message.answer(
            "VOICE file_id:\n"
            f"<code>{safe_file_id}</code>",
            parse_mode="HTML",
        )

    # ========================================================
    # ОШИБКА
    # ========================================================

    except Exception as error:

        logger.exception(
            "Ошибка обработки аудио"
        )

        safe_error = escape_html(
            str(error)
        )

        try:

            await status.edit_text(
                "❌ <b>Ошибка</b>\n\n"
                f"<code>{safe_error}</code>",
                parse_mode="HTML",
            )

        except Exception:

            logger.exception(
                "Не удалось отправить сообщение "
                "об ошибке пользователю."
            )

    # ========================================================
    # УДАЛЕНИЕ TEMP ФАЙЛОВ
    # ========================================================

    finally:

        if input_path:

            try:

                if os.path.exists(
                    input_path
                ):

                    os.remove(
                        input_path
                    )

            except Exception:

                logger.warning(
                    "Не удалось удалить input: %s",
                    input_path,
                )

        if output_path:

            try:

                if os.path.exists(
                    output_path
                ):

                    os.remove(
                        output_path
                    )

            except Exception:

                logger.warning(
                    "Не удалось удалить output: %s",
                    output_path,
                )


# ============================================================
# ЕСЛИ ПРИСЛАЛИ УЖЕ ГОТОВОЕ VOICE
# ============================================================

@dp.message(F.voice)
async def voice_handler(
    message: types.Message
):

    if not is_admin(message):

        await message.answer(
            "Нет доступа."
        )

        return

    if not message.voice:
        return

    voice_file_id = (
        message.voice.file_id
    )

    title = "Голосовое"

    global VOICE_DATABASE

    VOICE_DATABASE.append(
        {
            "id": str(
                len(VOICE_DATABASE) + 1
            ),
            "title": title,
            "voice_file_id": voice_file_id,
        }
    )

    await message.answer(
        "✅ Это уже настоящее "
        "Telegram Voice.\n\n"
        "VOICE file_id:\n"
        f"<code>{escape_html(voice_file_id)}</code>",
        parse_mode="HTML",
    )


# ============================================================
# LIST
# ============================================================

@dp.message(F.text == "/list")
async def list_handler(
    message: types.Message
):

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
            f"{index}. "
            f"{escape_html(item['title'])}"
        )

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
    )


# ============================================================
# CLEAR
# ============================================================

@dp.message(F.text == "/clear")
async def clear_handler(
    message: types.Message
):

    if not is_admin(message):

        await message.answer(
            "Нет доступа."
        )

        return

    global VOICE_DATABASE

    VOICE_DATABASE.clear()

    await message.answer(
        "🗑 База голосовых очищена."
    )


# ============================================================
# INLINE SEARCH
# ============================================================

@dp.inline_query()
async def inline_query_handler(
    query: types.InlineQuery
):

    search_text = (
        query.query.strip().lower()
    )

    results = []

    for item in VOICE_DATABASE:

        title = str(
            item.get("title", "")
        ).strip()

        voice_file_id = str(
            item.get("voice_file_id", "")
        ).strip()

        # Пропускаем битые записи.

        if not title:
            continue

        if not voice_file_id:
            continue

        # Поиск по названию.

        if search_text:

            if search_text not in title.lower():
                continue

        # ====================================================
        # НАСТОЯЩИЙ TELEGRAM VOICE
        # ====================================================

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

    # ========================================================
    # FFMPEG
    # ========================================================

    check_ffmpeg()

    # ========================================================
    # WEBHOOK
    # ========================================================

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    logger.info(
        "Polling запущен."
    )

    try:

        await dp.start_polling(
            bot,
            allowed_updates=(
                dp.resolve_used_update_types()
            ),
        )

    except TelegramConflictError:

        logger.error(
            "TelegramConflictError: "
            "запущен другой экземпляр бота."
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

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.info(
            "Бот остановлен вручную."
        )
