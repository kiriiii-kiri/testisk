import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from game import Game
from database import init_db, get_user_record, update_user_record, get_top_players

# 🔥 ИСПРАВЛЕНО: УБРАЛ ЛИШНИЕ ПРОБЕЛЫ!
BOT_TOKEN = "8498252537:AAFS94y2DJEUOVjOZHx0boHiVvbMrV1T7dc"
WEBHOOK_URL = "https://testisk-zmeika.onrender.com/webhook"  # ← БЕЗ ПРОБЕЛОВ!

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

init_db()
active_games = {}

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
    username = callback.from_user.username or f"User{user_id}"
    game = Game(user_id, username)
    active_games[user_id] = game
    await update_game_message(callback.message, game)
    await send_control_buttons(callback.message, game)

@dp.callback_query(lambda c: c.data.startswith("move_"))
async def handle_move(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in active_games:
        await callback.answer("Игра не найдена. Начни новую!", show_alert=True)
        return
    game = active_games[user_id]
    if not game.is_alive:
        await callback.answer("Игра окончена! Начни заново.", show_alert=True)
        return
    direction = callback.data.split("_")[1]
    game.move(direction)
    await update_game_message(callback.message, game)
    if not game.is_alive:
        record_updated = update_user_record(game.user_id, game.username, game.score)
        achievements = check_achievements(game)
        msg = f"💀 *GAME OVER*\n\nОчки: {game.score}\nДлина: {len(game.snake)}"
        if record_updated: msg += "\n\n🏆 *Новый личный рекорд!*"
        if achievements: msg += "\n\n🎖️ *Новые достижения:*\n" + "\n".join(achievements)
        kb = [[InlineKeyboardButton(text="🔄 Играть снова", callback_data="start_game")]]
        await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode=ParseMode.MARKDOWN)
        del active_games[user_id]
        return
    await send_control_buttons(callback.message, game)

@dp.callback_query(lambda c: c.data == "show_leaderboard")
async def show_leaderboard(callback: types.CallbackQuery):
    top_players = get_top_players()
    msg = "🏆 *Топ-10 игроков:*\n\n" + "\n".join(f"{i}. @{username} — {score} очков" for i, (username, score) in enumerate(top_players, 1))
    kb = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="start_game")]]
    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(lambda c: c.data == "show_achievements")
async def show_achievements(callback: types.CallbackQuery):
    msg = "🎖️ *Достижения:*\n\n1. 🌱 *Новичок* — набрать 10 очков\n2. 🐉 *Охотник* — съесть 5 мобов\n3. 💎 *Коллекционер* — собрать 3 разных бонуса\n4. 🧗 *Альпинист* — пройти уровень 'Пещера'\n5. 🌳 *Покоритель лесов* — пройти уровень 'Лес'"
    kb = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="start_game")]]
    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode=ParseMode.MARKDOWN)

async def update_game_message(message: types.Message, game: 'Game'):
    board = game.render_board()
    status = f"\nОчки: {game.score} 🎯 | Длина: {len(game.snake)} 🐍 | Уровень: {game.level_name}"
    try:
        await message.edit_text(f"```\n{board}\n```\n{status}", parse_mode=ParseMode.MARKDOWN)
    except:
        pass

async def send_control_buttons(message: types.Message, game: 'Game'):
    kb = [
        [InlineKeyboardButton(text="⬆️", callback_data="move_up")],
        [
            InlineKeyboardButton(text="⬅️", callback_data="move_left"),
            InlineKeyboardButton(text="⬇️", callback_data="move_down"),
            InlineKeyboardButton(text="➡️", callback_data="move_right")
        ]
    ]
    try:
        await message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except:
        pass

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

# ✅ ИСПРАВЛЕНО: ДОБАВЛЕНА ПРОВЕРКА УСПЕШНОСТИ УСТАНОВКИ ВЕБХУКА
async def on_startup(bot: Bot):
    # Удаляем старый вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    # Устанавливаем новый и ЖДЁМ ответа
    result = await bot.set_webhook(WEBHOOK_URL)
    if result:
        logging.info(f"✅ Webhook установлен: {WEBHOOK_URL}")
    else:
        logging.error("❌ Не удалось установить вебхук!")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    logging.info("👋 Webhook удалён при выключении")

async def main():
    # Регистрируем хуки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запускаем вебхук-сервер
    await dp.start_webhook(
        webhook_path="/webhook",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        bot=bot
    )

if __name__ == "__main__":
    asyncio.run(main())
