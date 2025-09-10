import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from game import Game
from database import init_db, get_user_record, update_user_record, get_top_players

# 🔥 ГАРАНТИРОВАННО ЧИСТЫЙ URL — ОБРЕЗАЕМ ПРОБЕЛЫ
BOT_TOKEN = "8498252537:AAFS94y2DJEUOVjOZHx0boHiVvbMrV1T7dc"
WEBHOOK_URL = "https://testisk-zmeika.onrender.com/webhook".strip()  # ← .strip() УДАЛЯЕТ ВСЕ ПРОБЕЛЫ!
PORT = int(os.environ.get('PORT', 10000))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

init_db()
# 🔥 ФИКС: Используем словарь с блокировками для потокобезопасности
active_games = {}
game_locks = {}  # user_id -> asyncio.Lock

def get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in game_locks:
        game_locks[user_id] = asyncio.Lock()
    return game_locks[user_id]

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = [
        [InlineKeyboardButton(text="▶️ Начать игру", callback_data="start_game")],
        [InlineKeyboardButton(text="🏆 Рекорды", callback_data="show_leaderboard")],
        [InlineKeyboardButton(text="🎖️ Достижения", callback_data="show_achievements")]
    ]
    await message.answer(
        "🐍 *Snake RPG Evolution*\n\nСъедай еду, избегай препятствий, собирай бонусы и мобов!\nЧем длиннее змея — тем сильнее ты становишься.\n\nВыбери действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query(lambda c: c.data == "start_game")
async def start_game(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    logging.info(f"🎮 [USER {user_id}] Нажата кнопка 'Начать игру'")
    await callback.answer()  # Подтверждаем нажатие сразу

    username = callback.from_user.username or f"User{user_id}"
    game = Game(user_id, username)
    active_games[user_id] = game

    board = game.render_board()
    status = f"\nОчки: {game.score} 🎯 | Длина: {len(game.snake)} 🐍 | Уровень: {game.level_name}"
    msg = await callback.message.answer(
        f"```\n{board}\n```\n{status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_control_keyboard()  # ← БЕЗ await, потому что функция синхронная
    )

# 🔥 ИСПРАВЛЕНО: УБРАН async — функция теперь синхронная!
def get_control_keyboard():
    kb = [
        [InlineKeyboardButton(text="⬆️", callback_data="move_up")],
        [
            InlineKeyboardButton(text="⬅️", callback_data="move_left"),
            InlineKeyboardButton(text="⬇️", callback_data="move_down"),
            InlineKeyboardButton(text="➡️", callback_data="move_right")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.callback_query(lambda c: c.data.startswith("move_"))
@dp.callback_query(lambda c: c.data.startswith("move_"))
async def handle_move(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    logging.info(f"🐍 [USER {user_id}] Движение: {callback.data}")

    # 🔥 ФИКС: Блокируем доступ к игре, чтобы избежать race condition
    lock = get_user_lock(user_id)
    async with lock:
        if user_id not in active_games:
            await callback.answer("❗ Игра не найдена. Начни новую!", show_alert=True)
            return

        game = active_games[user_id]
        if not game.is_alive:
            await callback.answer("💀 Игра окончена! Начни заново.", show_alert=True)
            return

        direction = callback.data.split("_")[1]
        game.move(direction)

        # Обновляем сообщение
        board = game.render_board()
        status = f"\nОчки: {game.score} 🎯 | Длина: {len(game.snake)} 🐍 | Уровень: {game.level_name}"

        try:
            # 🔥 ФИКС: Обновляем и текст, И клавиатуру!
            await callback.message.edit_text(
                f"```\n{board}\n```\n{status}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_control_keyboard()  # ← ДОБАВЛЕНО!
            )
        except Exception as e:
            logging.warning(f"⚠️ Не удалось обновить сообщение: {e}")

        # Проверка на Game Over
        if not game.is_alive:
            record_updated = update_user_record(game.user_id, game.username, game.score)
            achievements = check_achievements(game)
            msg = f"💀 *GAME OVER*\n\nОчки: {game.score}\nДлина: {len(game.snake)}"
            if record_updated:
                msg += "\n\n🏆 *Новый личный рекорд!*"
            if achievements:
                msg += "\n\n🎖️ *Новые достижения:*\n" + "\n".join(achievements)

            kb = [[InlineKeyboardButton(text="🔄 Играть снова", callback_data="start_game")]]
            try:
                await callback.message.edit_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logging.error(f"❌ Ошибка при показе Game Over: {e}")
            del active_games[user_id]
            return

        # 🔥 Клавиатура ОБНОВЛЯЕТСЯ здесь (в edit_text выше) — не нужно отдельно!

@dp.callback_query(lambda c: c.data == "show_leaderboard")
async def show_leaderboard(callback: types.CallbackQuery):
    await callback.answer()
    top_players = get_top_players()
    msg = "🏆 *Топ-10 игроков:*\n\n" + "\n".join(f"{i}. @{username} — {score} очков" for i, (username, score) in enumerate(top_players, 1))
    kb = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]]
    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(lambda c: c.data == "show_achievements")
async def show_achievements(callback: types.CallbackQuery):
    await callback.answer()
    msg = "🎖️ *Достижения:*\n\n1. 🌱 *Новичок* — набрать 10 очков\n2. 🐉 *Охотник* — съесть 5 мобов\n3. 💎 *Коллекционер* — собрать 3 разных бонуса\n4. 🧗 *Альпинист* — пройти уровень 'Пещера'\n5. 🌳 *Покоритель лесов* — пройти уровень 'Лес'"
    kb = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]]
    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(lambda c: c.data == "main_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.answer()
    kb = [
        [InlineKeyboardButton(text="▶️ Начать игру", callback_data="start_game")],
        [InlineKeyboardButton(text="🏆 Рекорды", callback_data="show_leaderboard")],
        [InlineKeyboardButton(text="🎖️ Достижения", callback_data="show_achievements")]
    ]
    await callback.message.edit_text(
        "🐍 *Snake RPG Evolution*\n\nСъедай еду, избегай препятствий, собирай бонусы и мобов!\nЧем длиннее змея — тем сильнее ты становишься.\n\nВыбери действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode=ParseMode.MARKDOWN
    )

def check_achievements(game: 'Game') -> list:
    a = []
    if game.score >= 10: a.append("🌱 Новичок")
    if game.mobs_eaten >= 5: a.append("🐉 Охотник")
    if len(game.bonuses_collected) >= 3: a.append("💎 Коллекционер")
    if game.level == 2: a.append("🧗 Альпинист")
    if game.level == 3: a.append("🌳 Покоритель лесов")
    return a

@dp.message()
async def any_message(message: types.Message):
    await message.answer("Нажми /start для начала игры!")

async def on_startup():
    logging.info("🔄 [SYSTEM] Запуск бота...")
    logging.info("🗑️ [SYSTEM] Удаляем старый вебхук...")
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.sleep(1)

    webhook_info = await bot.get_webhook_info()
    logging.info(f"📡 [SYSTEM] Текущий вебхук: '{webhook_info.url}'")

    if webhook_info.url != WEBHOOK_URL:
        logging.info(f"🔗 [SYSTEM] Устанавливаем новый вебхук: {WEBHOOK_URL}")
        result = await bot.set_webhook(WEBHOOK_URL)
        if result:
            logging.info("✅ [SYSTEM] Вебхук успешно установлен!")
        else:
            logging.error("❌ [SYSTEM] Не удалось установить вебхук!")
    else:
        logging.info("✅ [SYSTEM] Вебхук уже установлен.")

async def on_shutdown():
    logging.info("👋 [SYSTEM] Завершение работы...")
    await bot.delete_webhook()
    logging.info("🗑️ [SYSTEM] Вебхук удалён.")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Настройка веб-сервера для вебхука
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    # Запускаем aiohttp сервер
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()

    logging.info(f"🚀 Бот запущен на порту {PORT} с вебхуком {WEBHOOK_URL}")

    # Бесконечное ожидание
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
