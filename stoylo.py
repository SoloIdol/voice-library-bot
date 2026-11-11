import asyncio
import html
import logging
import os
import shutil
import sqlite3
import tempfile

from aiogram import Bot, Dispatcher, F, types
from aiogram.exceptions import TelegramConflictError
from aiogram.types import (
    FSInputFile,
    InlineQueryResultCachedVoice,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

API_TOKEN = os.getenv("API_TOKEN")


ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


DATABASE_PATH = "voices.db"


# ============================================================
# ПРОВЕРКА ТОКЕНА
# ============================================================

if not API_TOKEN:
    raise RuntimeError(
        "Переменная API_TOKEN не установлена. "
        "Добавь API_TOKEN в Railway Variables."
    )


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
# DATABASE
# ============================================================

def get_db():
    """
    Открывает соединение с SQLite.
    """

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database():
    """
    Создаёт таблицу голосовых, если её ещё нет.
    """

    connection = get_db()

    try:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS voices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                artist TEXT DEFAULT '',
                voice_file_id TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.commit()

        logger.info(
            "SQLite database initialized: %s",
            DATABASE_PATH,
        )

    finally:

        connection.close()


# ============================================================
# DATABASE — ADD
# ============================================================

def add_voice(
    title: str,
    artist: str,
    voice_file_id: str,
):
    """
    Добавляет голосовое в библиотеку.
    """

    connection = get_db()

    try:

        cursor = connection.execute(
            """
            INSERT INTO voices
                (title, artist, voice_file_id)
            VALUES
                (?, ?, ?)
            """,
            (
                title,
                artist,
                voice_file_id,
            ),
        )

        connection.commit()

        return cursor.lastrowid

    finally:

        connection.close()


# ============================================================
# DATABASE — GET ALL
# ============================================================

def get_all_voices():

    connection = get_db()

    try:

        cursor = connection.execute(
            """
            SELECT
                id,
                title,
                artist,
                voice_file_id
            FROM voices
            ORDER BY id ASC
            """
        )

        return cursor.fetchall()

    finally:

        connection.close()


# ============================================================
# DATABASE — GET ONE
# ============================================================

def get_voice(voice_id: int):

    connection = get_db()

    try:

        cursor = connection.execute(
            """
            SELECT
                id,
                title,
                artist,
                voice_file_id
            FROM voices
            WHERE id = ?
            """,
            (voice_id,),
        )

        return cursor.fetchone()

    finally:

        connection.close()


# ============================================================
# DATABASE — RENAME
# ============================================================

def rename_voice(
    voice_id: int,
    title: str,
):

    connection = get_db()

    try:

        cursor = connection.execute(
            """
            UPDATE voices
            SET title = ?
            WHERE id = ?
            """,
            (
                title,
                voice_id,
            ),
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:

        connection.close()


# ============================================================
# DATABASE — ARTIST
# ============================================================

def change_artist(
    voice_id: int,
    artist: str,
):

    connection = get_db()

    try:

        cursor = connection.execute(
            """
            UPDATE voices
            SET artist = ?
            WHERE id = ?
            """,
            (
                artist,
                voice_id,
            ),
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:

        connection.close()


# ============================================================
# DATABASE — DELETE
# ============================================================

def delete_voice(
    voice_id: int,
):

    connection = get_db()

    try:

        cursor = connection.execute(
            """
            DELETE FROM voices
            WHERE id = ?
            """,
            (voice_id,),
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:

        connection.close()


# ============================================================
# DATABASE — CLEAR
# ============================================================

def clear_database():

    connection = get_db()

    try:

        cursor = connection.execute(
            """
            DELETE FROM voices
            """
        )

        connection.commit()

        return cursor.rowcount

    finally:

        connection.close()


# ============================================================
# ADMIN CHECK
# ============================================================

def is_admin(message: types.Message) -> bool:

    if ADMIN_ID == 0:
        return True

    if not message.from_user:
        return False

    return (
        message.from_user.id
        == ADMIN_ID
    )


# ============================================================
# HTML ESCAPE
# ============================================================

def escape_html(text) -> str:

    return html.escape(
        str(text)
    )


# ============================================================
# FFMPEG CHECK
# ============================================================

def check_ffmpeg():

    logger.info(
        "=== ПРОВЕРКА FFMPEG ==="
    )

    ffmpeg_path = shutil.which(
        "ffmpeg"
    )

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
# START
# ============================================================

@dp.message(F.text == "/start")
async def start_handler(
    message: types.Message
):

    await message.answer(
        "🎤 <b>Библиотека голосовых</b>\n\n"

        "Отправь мне MP3/аудиофайл — "
        "я превращу его в настоящее "
        "Telegram Voice и добавлю "
        "в библиотеку.\n\n"

        "<b>Управление:</b>\n"
        "/list — список голосовых\n"
        "/rename ID новое название\n"
        "/artist ID исполнитель\n"
        "/delete ID — удалить\n"
        "/clear — очистить библиотеку\n"
        "/id — узнать свой Telegram ID\n\n"

        "<b>Пример:</b>\n"
        "<code>/rename 3 Лебединое озеро</code>\n"
        "<code>/artist 3 Чайковский</code>\n"
        "<code>/delete 3</code>",
        parse_mode="HTML",
    )


# ============================================================
# ID
# ============================================================

@dp.message(F.text == "/id")
async def id_handler(
    message: types.Message
):

    if not message.from_user:
        return

    await message.answer(
        "Твой Telegram ID:\n"
        f"<code>{message.from_user.id}</code>",
        parse_mode="HTML",
    )


# ============================================================
# AUDIO -> VOICE
# ============================================================

@dp.message(F.audio)
async def audio_handler(
    message: types.Message
):

    if not is_admin(message):

        await message.answer(
            "⛔ Нет доступа."
        )

        return

    if not message.audio:
        return

    # ========================================================
    # TITLE
    # ========================================================

    original_name = (
        message.audio.file_name
        or "Голосовое"
    )

    title = original_name

    if "." in title:

        title = title.rsplit(
            ".",
            1,
        )[0]

    title = title.strip()

    if not title:

        title = "Голосовое"

    # Исполнитель изначально пустой.
    artist = ""

    logger.info(
        "Получено аудио: %s",
        title,
    )

    status = await message.answer(
        "⏳ Конвертирую "
        f"<b>{escape_html(title)}</b> "
        "в голосовое...",
        parse_mode="HTML",
    )

    input_path = None
    output_path = None

    try:

        # ====================================================
        # FFMPEG
        # ====================================================

        if not check_ffmpeg():

            raise RuntimeError(
                "FFmpeg не найден."
            )

        # ====================================================
        # GET TELEGRAM FILE
        # ====================================================

        telegram_file = await bot.get_file(
            message.audio.file_id
        )

        if not telegram_file.file_path:

            raise RuntimeError(
                "Telegram не вернул "
                "путь к файлу."
            )

        # ====================================================
        # INPUT TEMP FILE
        # ====================================================

        input_temp = (
            tempfile.NamedTemporaryFile(
                suffix=".input",
                delete=False,
            )
        )

        input_path = input_temp.name

        input_temp.close()

        # ====================================================
        # DOWNLOAD
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
        # OUTPUT TEMP FILE
        # ====================================================

        output_temp = (
            tempfile.NamedTemporaryFile(
                suffix=".ogg",
                delete=False,
            )
        )

        output_path = output_temp.name

        output_temp.close()

        # ====================================================
        # FFMPEG CONVERSION
        # ====================================================

        logger.info(
            "Начинаем конвертацию..."
        )

        process = (
            await asyncio.create_subprocess_exec(
                "ffmpeg",

                "-y",

                "-i",
                input_path,

                # Mono
                "-ac",
                "1",

                # Opus
                "-c:a",
                "libopus",

                # Bitrate
                "-b:a",
                "48k",

                output_path,

                stdout=(
                    asyncio.subprocess.PIPE
                ),

                stderr=(
                    asyncio.subprocess.PIPE
                ),
            )
        )

        stdout, stderr = (
            await process.communicate()
        )

        if process.returncode != 0:

            ffmpeg_error = (
                stderr.decode(
                    errors="ignore"
                )
            )

            logger.error(
                "FFmpeg error:\n%s",
                ffmpeg_error,
            )

            raise RuntimeError(
                "FFmpeg не смог "
                "преобразовать файл."
            )

        logger.info(
            "Конвертация завершена: %s",
            output_path,
        )

        # ====================================================
        # CHECK FILE
        # ====================================================

        if not os.path.exists(
            output_path
        ):

            raise RuntimeError(
                "OGG-файл не создан."
            )

        output_size = os.path.getsize(
            output_path
        )

        logger.info(
            "Размер OGG: %d bytes",
            output_size,
        )

        if output_size <= 0:

            raise RuntimeError(
                "Полученный OGG-файл пуст."
            )

        # ====================================================
        # SEND AS TELEGRAM VOICE
        # ====================================================

        logger.info(
            "Отправляем как Telegram Voice..."
        )

        voice_file = FSInputFile(
            output_path
        )

        sent_message = (
            await bot.send_voice(
                chat_id=message.chat.id,
                voice=voice_file,
            )
        )

        # ====================================================
        # GET VOICE FILE ID
        # ====================================================

        if not sent_message.voice:

            raise RuntimeError(
                "Telegram не вернул "
                "объект Voice."
            )

        voice_file_id = (
            sent_message.voice.file_id
        )

        logger.info(
            "VOICE file_id: %s",
            voice_file_id,
        )

        # ====================================================
        # SAVE TO DATABASE
        # ====================================================

        database_id = add_voice(
            title=title,
            artist=artist,
            voice_file_id=voice_file_id,
        )

        logger.info(
            "Голосовое добавлено в БД. ID=%s",
            database_id,
        )

        # ====================================================
        # SUCCESS MESSAGE
        # ====================================================

        await status.edit_text(
            "✅ <b>Готово!</b>\n\n"

            f"ID: <b>{database_id}</b>\n"
            f"Название: "
            f"<b>{escape_html(title)}</b>\n"
            "Исполнитель: <i>не указан</i>\n\n"

            "Чтобы изменить название:\n"
            f"<code>/rename {database_id} "
            f"Новое название</code>\n\n"

            "Чтобы указать исполнителя:\n"
            f"<code>/artist {database_id} "
            f"Исполнитель</code>",
            parse_mode="HTML",
        )

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
                "Не удалось показать ошибку."
            )

    finally:

        # ====================================================
        # DELETE INPUT TEMP
        # ====================================================

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
                    "Не удалось удалить: %s",
                    input_path,
                )

        # ====================================================
        # DELETE OUTPUT TEMP
        # ====================================================

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
                    "Не удалось удалить: %s",
                    output_path,
                )


# ============================================================
# ALREADY EXISTING VOICE
# ============================================================

@dp.message(F.voice)
async def voice_handler(
    message: types.Message
):

    if not is_admin(message):

        await message.answer(
            "⛔ Нет доступа."
        )

        return

    if not message.voice:
        return

    voice_file_id = (
        message.voice.file_id
    )

    title = "Голосовое"

    try:

        database_id = add_voice(
            title=title,
            artist="",
            voice_file_id=voice_file_id,
        )

        await message.answer(
            "✅ Голосовое добавлено.\n\n"

            f"ID: <b>{database_id}</b>\n"
            "Название: "
            "<b>Голосовое</b>\n\n"

            "Изменить название:\n"
            f"<code>/rename {database_id} "
            "Новое название</code>",
            parse_mode="HTML",
        )

    except sqlite3.IntegrityError:

        await message.answer(
            "⚠️ Это голосовое уже есть "
            "в библиотеке."
        )


# ============================================================
# LIST
# ============================================================

@dp.message(F.text == "/list")
async def list_handler(
    message: types.Message
):

    if not is_admin(message):

        await message.answer(
            "⛔ Нет доступа."
        )

        return

    voices = get_all_voices()

    if not voices:

        await message.answer(
            "📚 Библиотека пока пустая."
        )

        return

    lines = [
        "🎤 <b>МОЯ БИБЛИОТЕКА</b>",
        "",
    ]

    for voice in voices:

        voice_id = voice["id"]

        title = escape_html(
            voice["title"]
        )

        artist = escape_html(
            voice["artist"]
        )

        if artist:

            lines.append(
                f"<b>{voice_id}.</b> "
                f"{title}\n"
                f"   👤 {artist}\n"
            )

        else:

            lines.append(
                f"<b>{voice_id}.</b> "
                f"{title}\n"
                "   👤 <i>исполнитель "
                "не указан</i>\n"
            )

    lines.append(
        "────────────────"
    )

    lines.append(
        "✏️ <code>/rename ID "
        "Новое название</code>"
    )

    lines.append(
        "👤 <code>/artist ID "
        "Исполнитель</code>"
    )

    lines.append(
        "🗑 <code>/delete ID</code>"
    )

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
    )


# ============================================================
# RENAME
# ============================================================

@dp.message(
    F.text.startswith("/rename")
)
async def rename_handler(
    message: types.Message
):

    if not is_admin(message):

        await message.answer(
            "⛔ Нет доступа."
        )

        return

    text = (
        message.text
        or ""
    ).strip()

    parts = text.split(
        maxsplit=2
    )

    if len(parts) < 3:

        await message.answer(
            "❌ Неверный формат.\n\n"

            "Используй:\n"
            "<code>/rename ID "
            "Новое название</code>\n\n"

            "Например:\n"
            "<code>/rename 3 "
            "Лебединое озеро</code>",
            parse_mode="HTML",
        )

        return

    try:

        voice_id = int(
            parts[1]
        )

    except ValueError:

        await message.answer(
            "❌ ID должен быть числом."
        )

        return

    new_title = parts[2].strip()

    if not new_title:

        await message.answer(
            "❌ Название не может быть пустым."
        )

        return

    voice = get_voice(
        voice_id
    )

    if not voice:

        await message.answer(
            f"❌ Голосовое с ID "
            f"<b>{voice_id}</b> не найдено.",
            parse_mode="HTML",
        )

        return

    rename_voice(
        voice_id,
        new_title,
    )

    await message.answer(
        "✅ Название изменено.\n\n"

        f"ID: <b>{voice_id}</b>\n"
        f"Новое название: "
        f"<b>{escape_html(new_title)}</b>",
        parse_mode="HTML",
    )


# ============================================================
# ARTIST
# ============================================================

@dp.message(
    F.text.startswith("/artist")
)
async def artist_handler(
    message: types.Message
):

    if not is_admin(message):

        await message.answer(
            "⛔ Нет доступа."
        )

        return

    text = (
        message.text
        or ""
    ).strip()

    parts = text.split(
        maxsplit=2
    )

    if len(parts) < 3:

        await message.answer(
            "❌ Неверный формат.\n\n"

            "Используй:\n"
            "<code>/artist ID "
            "Исполнитель</code>\n\n"

            "Например:\n"
            "<code>/artist 3 "
            "Чайковский</code>",
            parse_mode="HTML",
        )

        return

    try:

        voice_id = int(
            parts[1]
        )

    except ValueError:

        await message.answer(
            "❌ ID должен быть числом."
        )

        return

    new_artist = parts[2].strip()

    if not new_artist:

        await message.answer(
            "❌ Исполнитель не может "
            "быть пустым."
        )

        return

    voice = get_voice(
        voice_id
    )

    if not voice:

        await message.answer(
            f"❌ Голосовое с ID "
            f"<b>{voice_id}</b> не найдено.",
            parse_mode="HTML",
        )

        return

    change_artist(
        voice_id,
        new_artist,
    )

    await message.answer(
        "✅ Исполнитель изменён.\n\n"

        f"ID: <b>{voice_id}</b>\n"
        f"Исполнитель: "
        f"<b>{escape_html(new_artist)}</b>",
        parse_mode="HTML",
    )


# ============================================================
# DELETE
# ============================================================

@dp.message(
    F.text.startswith("/delete")
)
async def delete_handler(
    message: types.Message
):

    if not is_admin(message):

        await message.answer(
            "⛔ Нет доступа."
        )

        return

    text = (
        message.text
        or ""
    ).strip()

    parts = text.split(
        maxsplit=1
    )

    if len(parts) < 2:

        await message.answer(
            "❌ Укажи ID.\n\n"

            "Например:\n"
            "<code>/delete 3</code>",
            parse_mode="HTML",
        )

        return

    try:

        voice_id = int(
            parts[1]
        )

    except ValueError:

        await message.answer(
            "❌ ID должен быть числом."
        )

        return

    voice = get_voice(
        voice_id
    )

    if not voice:

        await message.answer(
            f"❌ Голосовое с ID "
            f"<b>{voice_id}</b> не найдено.",
            parse_mode="HTML",
        )

        return

    title = voice["title"]

    deleted = delete_voice(
        voice_id
    )

    if deleted:

        await message.answer(
            "🗑 <b>Удалено из библиотеки.</b>\n\n"
            f"ID: <b>{voice_id}</b>\n"
            f"Название: "
            f"<b>{escape_html(title)}</b>\n\n"
            "Само старое сообщение "
            "в Telegram не удаляется.",
            parse_mode="HTML",
        )

    else:

        await message.answer(
            "❌ Не удалось удалить запись."
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
            "⛔ Нет доступа."
        )

        return

    count = clear_database()

    await message.answer(
        "🗑 <b>Библиотека очищена.</b>\n\n"
        f"Удалено записей: <b>{count}</b>\n\n"
        "Сами ранее отправленные "
        "голосовые сообщения Telegram "
        "не удаляются.",
        parse_mode="HTML",
    )


# ============================================================
# INLINE SEARCH
# ============================================================

@dp.inline_query()
async def inline_query_handler(
    query: types.InlineQuery
):

    search_text = (
        query.query
        .strip()
        .lower()
    )

    voices = get_all_voices()

    results = []

    for voice in voices:

        voice_id = voice["id"]

        title = (
            voice["title"]
            or ""
        ).strip()

        artist = (
            voice["artist"]
            or ""
        ).strip()

        voice_file_id = (
            voice["voice_file_id"]
            or ""
        ).strip()

        if not voice_file_id:
            continue

        # ====================================================
        # ПОИСК
        # ====================================================

        searchable_text = (
            f"{title} {artist}"
        ).lower()

        if search_text:

            if search_text not in searchable_text:
                continue

        # ====================================================
        # ОТОБРАЖАЕМОЕ НАЗВАНИЕ
        # ====================================================

        if artist:

            display_title = (
                f"{title} — {artist}"
            )

        else:

            display_title = title

        # ====================================================
        # TELEGRAM VOICE
        # ====================================================

        results.append(
            InlineQueryResultCachedVoice(
                id=f"voice_{voice_id}",
                voice_file_id=voice_file_id,
                title=display_title,
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
    # DATABASE
    # ========================================================

    init_database()

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
