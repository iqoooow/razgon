import asyncio
from telegram import Bot
from config import Config

async def check_bot():
    bot = Bot(token=Config.TELEGRAM_TOKEN)
    try:
        me = await bot.get_me()
        print(f"Bot Name: {me.first_name}")
        print(f"Bot Username: @{me.username}")
        
        webhook_info = await bot.get_webhook_info()
        print(f"Webhook URL: {webhook_info.url}")
        
        if webhook_info.url:
            print("Deleting webhook...")
            await bot.delete_webhook()
            print("Webhook deleted.")
        else:
            print("No webhook set.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_bot())
