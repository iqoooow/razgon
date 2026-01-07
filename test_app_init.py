import asyncio
from telegram.ext import ApplicationBuilder
from config import Config

async def test_init():
    print("Testing Application initialization...")
    app = ApplicationBuilder().token(Config.TELEGRAM_TOKEN).read_timeout(30).connect_timeout(30).build()
    try:
        await app.initialize()
        print("Initialization successful!")
        me = await app.bot.get_me()
        print(f"Bot: @{me.username}")
        await app.shutdown()
    except Exception as e:
        print(f"Initialization failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_init())
