# Voice Library Bot

A Telegram bot that turns audio files into Telegram voice messages and keeps them in a searchable library.

Send the bot an audio file: it converts it with **ffmpeg** (mono, Opus/OGG, 48 kbps), sends it back as a voice message and saves it to a **SQLite** database. Any saved voice can then be found and sent in any chat through **inline search** (`@your_bot query`).

## Features

- Audio → voice message conversion (ffmpeg, libopus)
- Voice library stored in SQLite, with titles and artists
- Inline search by title or artist
- Admin-only library management
- Asynchronous bot built with **aiogram 3**
- Ready to run with **Docker**

## Commands

| Command | Description |
|---|---|
| `/start` | Help and list of commands |
| `/id` | Shows your Telegram user ID |
| `/list` | Shows the library (ID, title, artist) |
| `/rename ID title` | Renames a voice |
| `/artist ID name` | Sets the artist of a voice |
| `/delete ID` | Removes a voice from the library |
| `/clear` | Empties the library |

Library management commands are restricted to the admin. The bot interface is in Russian.

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and get its token.
2. Enable inline mode in BotFather with `/setinline`.
3. Find your Telegram ID (send `/id` to the bot) and set it as `ADMIN_ID`.

### Run with Docker

```bash
docker build -t voice-library-bot .
docker run -d -e API_TOKEN=your_token -e ADMIN_ID=your_id voice-library-bot
```

### Run locally

Requires Python 3.12+ and ffmpeg installed.

```bash
pip install -r requirements.txt
export API_TOKEN=your_token
export ADMIN_ID=your_id
python stoylo.py
```

## Tech stack

Python · aiogram 3 · asyncio · SQLite · ffmpeg · Docker
