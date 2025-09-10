import asyncio
import logging
import os
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Импорты из ваших модулей
try:
    from game import Game
    from database import init_db, get_user_record, update_user_record, get_top_players
except ImportError:
    # Заглушки для тестирования
    class Game:
        def __init__(self, *args): pass
    def init_db(): pass
    def get_user_record(*args): return 0
    def update_user_record(*args): return False
    def get_top_players(): return []

# Настройки
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8498252537:AAFS94y2DJEUOVjOZHx0boHiVvbMrV1T7dc")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://testisk-zmeika.onrender.com").strip()
PORT = int(os.environ.get('PORT', 10000))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальные переменные
active_games = {}
game_locks = {}

def get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in game_locks:
        game_locks[user_id] = asyncio.Lock()
    return game_locks[user_id]

# Health check endpoint
async def health_check(request):
    """Enhanced health check для UptimeRobot и Render"""
    logger.info("🔍 Health check запрос")
    return web.Response(
        text="🐍 Snake RPG Bot is alive and well!",
        status=200,
        headers={'Content-Type': 'text/plain'}
    )

async def home_page(request):
    """Главная страница"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Snake RPG Bot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .status { color: green; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🐍 Snake RPG Bot</h1>
        <p class="status">✅ Бот активен и работает</p>
        <p>Мониторинг через UptimeRobot</p>
        <p>Telegram: <a href="https://t.me/teeeeeeeeeeeeeeeeestttttt_bot">@teeeeeeeeeeeeeeeeestttttt_bot</a></p>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

# Обработчики бота (упрощённые версии)
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = [
        [InlineKeyboardButton(text="▶️ Начать игру", callback_data="start_game")],
        [InlineKeyboardButton(text="🏆 Рекорды", callback_data="show_leaderboard")],
    ]
    await message.answer(
        "🐍 *Snake RPG Evolution*\n\nВыбери действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query(lambda c: c.data == "start_game")
async def start_game(callback: types.CallbackQuery):
    await callback.answer("Игра начинается!")
    await callback.message.answer("🎮 Игра запущена!")

@dp.message()
async def any_message(message: types.Message):
    await message.answer("Нажми /start для начала игры!")

async def on_startup():
    """Запуск приложения"""
    logger.info("🔄 Запуск Snake RPG Bot...")
    
    try:
        # Инициализация базы данных
        init_db()
        
        # Настройка вебхука
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(1)
        
        webhook_url = f"{WEBHOOK_URL}/webhook"
        await bot.set_webhook(webhook_url)
        logger.info(f"✅ Вебхук установлен: {webhook_url}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске: {e}")

async def on_shutdown():
    """Завершение работы"""
    logger.info("👋 Завершение работы...")
    await bot.delete_webhook()

async def create_app():
    """Создание и настройка приложения"""
    app = web.Application()
    
    # Health check endpoints
    app.router.add_get('/', home_page)
    app.router.add_get('/health', health_check)
    app.router.add_get('/ping', health_check)
    app.router.add_get('/status', health_check)
    
    # Webhook для Telegram
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    
    return app

async def main():
    """Основная функция"""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    app = await create_app()
    runner = web.AppRunner(app)
    
    try:
        await runner.setup()
        site = web.TCPSite(runner, host='0.0.0.0', port=PORT)
        await site.start()
        
        logger.info(f"🚀 Сервер запущен на порту {PORT}")
        logger.info(f"🌐 Health check: http://0.0.0.0:{PORT}/health")
        logger.info(f"🤖 Webhook: {WEBHOOK_URL}/webhook")
        
        # Бесконечный цикл с периодическим логированием
        while True:
            await asyncio.sleep(300)  # 5 минут
            logger.info("✅ Бот активен, мониторинг работает")
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Приложение завершено")
    except Exception as e:
        logger.error(f"💥 Неожиданная ошибка: {e}")
