import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from game import Game
from database import init_db, get_user_record, update_user_record, get_top_players

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Замени перед деплоем!
WEBHOOK_URL = "https://your-subdomain.onrender.com/webhook"  # Замени в Render

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация БД
init_db()

# Хранилище игр: user_id -> Game
active_games = {}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = [
        [InlineKeyboardButton(text="▶️ Начать игру", callback_data="start_game")],
        [InlineKeyboardButton(text="🏆 Рекорды", callback_data="show_leaderboard")],
        [InlineKeyboardButton(text="🎖️ Достижения", callback_data="show_achievements")]
    ]
    await message.answer(
        "🐍 *Snake RPG Evolution*\n\n"
        "Съедай еду, избегай препятствий, собирай бонусы и мобов!\n"
        "Чем длиннее змея — тем сильнее ты становишься.\n\n"
        "Выбери действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query(lambda c: c.data == "start_game")
async def start_game(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or f"User{user_id}"

    # Создаём новую игру
    game = Game(user_id, username)
    active_games[user_id] = game

    # Отправляем игровое поле
    await update_game_message(callback.message, game)

    # Кнопки управления
    await send_control_buttons(callback.message, game)

@dp.callback_query(lambda c: c.data.startswith("move_"))
async def handle_move(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in active_games:
        await callback.answer("Игра не найдена. Начни новую!", show_alert=True)
        return

    game = active_games[user_id]
    direction = callback.data.split("_")[1]

    if not game.is_alive:
        await callback.answer("Игра окончена! Начни заново.", show_alert=True)
        return

    # Двигаем змею
    game.move(direction)

    # Обновляем сообщение
    await update_game_message(callback.message, game)

    # Если игра окончена — показываем Game Over
    if not game.is_alive:
        record_updated = update_user_record(game.user_id, game.username, game.score)
        achievements = check_achievements(game)

        msg = f"💀 *GAME OVER*\n\nОчки: {game.score}\nДлина: {len(game.snake)}"
        if record_updated:
            msg += "\n\n🏆 *Новый личный рекорд!*"
        if achievements:
            msg += "\n\n🎖️ *Новые достижения:*\n" + "\n".join(achievements)

        kb = [[InlineKeyboardButton(text="🔄 Играть снова", callback_data="start_game")]]
        await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode=ParseMode.MARKDOWN)
        del active_games[user_id]
        return

    # Обновляем кнопки управления
    await send_control_buttons(callback.message, game)

@dp.callback_query(lambda c: c.data == "show_leaderboard")
async def show_leaderboard(callback: types.CallbackQuery):
    top_players = get_top_players()
    msg = "🏆 *Топ-10 игроков:*\n\n"
    for i, (username, score) in enumerate(top_players, 1):
        msg += f"{i}. @{username} — {score} очков\n"
    kb = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="start_game")]]
    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(lambda c: c.data == "show_achievements")
async def show_achievements(callback: types.CallbackQuery):
    # Здесь можно хранить достижения в БД, но для MVP — просто описание
    msg = "🎖️ *Достижения:*\n\n" \
          "1. 🌱 *Новичок* — набрать 10 очков\n" \
          "2. 🐉 *Охотник* — съесть 5 мобов\n" \
          "3. 💎 *Коллекционер* — собрать 3 разных бонуса\n" \
          "4. 🧗 *Альпинист* — пройти уровень 'Пещера'\n" \
          "5. 🌳 *Покоритель лесов* — пройти уровень 'Лес'"
    kb = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="start_game")]]
    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode=ParseMode.MARKDOWN)

async def update_game_message(message: types.Message, game: 'Game'):
    board = game.render_board()
    status = f"\nОчки: {game.score} 🎯 | Длина: {len(game.snake)} 🐍 | Уровень: {game.level_name}"
    try:
        await message.edit_text(f"```\n{board}\n```\n{status}", parse_mode=ParseMode.MARKDOWN)
    except:
        pass  # Игнорируем, если сообщение не изменилось

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
    achievements = []
    if game.score >= 10:
        achievements.append("🌱 Новичок")
    if game.mobs_eaten >= 5:
        achievements.append("🐉 Охотник")
    if len(game.bonuses_collected) >= 3:
        achievements.append("💎 Коллекционер")
    if game.level == 2:
        achievements.append("🧗 Альпинист")
    if game.level == 3:
        achievements.append("🌳 Покоритель лесов")
    return achievements

@d
