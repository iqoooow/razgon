import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config import Config
from modules.logger import logger
from modules.risk_manager import risk_manager
from modules.mt5_interface import mt5_interface

class TelegramBot:
    def __init__(self):
        self.application = None
        self.bot_running = False
        self.trading_enabled = False # Controlled via /on /off
        self.chat_id = Config.TELEGRAM_CHAT_ID

    async def get_main_menu(self):
        keyboard = [
            [
                InlineKeyboardButton("🟢 Yoqish (Start)", callback_data='cmd_on'),
                InlineKeyboardButton("🔴 O'chirish (Stop)", callback_data='cmd_off')
            ],
            [
                InlineKeyboardButton("📊 Status", callback_data='cmd_status'),
                InlineKeyboardButton("💰 Balans", callback_data='cmd_balance')
            ],
            [
                InlineKeyboardButton("🇺🇿 Bozor Tahlili", callback_data='cmd_report')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_markup = await self.get_main_menu()
        await update.message.reply_text(
            "🚀 *Razgon Bot v1.1 - Boshqaruv Paneli*\n"
            "Kerakli buyruqni tanlang:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query
        
        # Vital to stop the loading animation. We can show a toast here if we want.
        # await query.answer() 

        data = query.data
        text = ""
        
        if data == 'cmd_on':
            self.trading_enabled = True
            logger.info("User enabled trading via UI")
            text = "✅ Bot Ishga tushdi (Trading Enabled)"
            
        elif data == 'cmd_off':
            self.trading_enabled = False
            logger.info("User disabled trading via UI")
            text = "⛔ Bot To'xtatildi (Trading Disabled)"

        elif data == 'cmd_status':
            status = "🟢 Faol" if self.trading_enabled else "🔴 To'xtatilgan"
            trades = f"{risk_manager.trades_today}/{risk_manager.max_trades_per_day}"
            text = f"📊 *Status*: {status}\n🎲 *Bugungi Savdolar*: {trades}"

        elif data == 'cmd_balance':
            acct = mt5_interface.get_account_info()
            bal = f"{acct['balance']:.2f}" if acct else "N/A"
            eq = f"{acct['equity']:.2f}" if acct else "N/A"
            text = f"💰 *Balans*: {bal}\n📉 *Equity*: {eq}"

        elif data == 'cmd_report':
            # Run report logic
            from modules.market_analysis import market_analyzer
            symbol = Config.SYMBOL_LIST[0]
            report = market_analyzer.get_market_report(symbol)
            if not report:
                report = "❌ Ma'lumot topilmadi."
            
            await context.bot.send_message(chat_id=query.message.chat_id, text=report, parse_mode='Markdown')
            await query.answer() # Close loading
            return # Don't edit message for report

        # Attempt to edit the message
        try:
            if text:
                await query.edit_message_text(text=text, parse_mode='Markdown', reply_markup=await self.get_main_menu())
                await query.answer("Yangilandi")
        except Exception as e:
            # Ignore "Message is not modified" error
            if "Message is not modified" in str(e):
                await query.answer("O'zgarish yo'q")
            else:
                logger.error(f"Button Callback Error: {e}")
                await query.answer("Xatolik bo'ldi")

    async def on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.trading_enabled = True
        await update.message.reply_text("✅ Trading ENABLED")

    async def off_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.trading_enabled = False
        await update.message.reply_text("⛔ Trading DISABLED")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        status = "🟢 Active" if self.trading_enabled else "🔴 Pause"
        acct = mt5_interface.get_account_info()
        bal = acct['balance'] if acct else "N/A"
        eq = acct['equity'] if acct else "N/A"
        
        await update.message.reply_text(
            f"📊 *Status*: {status}\n"
            f"💰 *Balance*: {bal}\n"
            f"📉 *Equity*: {eq}\n"
            f"🎲 *Trades Today*: {risk_manager.trades_today}/{risk_manager.max_trades_per_day}",
            parse_mode='Markdown'
        )

    async def _manual_trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_type: str):
        if not self.trading_enabled:
             await update.message.reply_text("⚠️ Trading is DISABLED. Use /on first.")
             return

        try:
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(f"Usage: /{order_type.lower()} SYMBOL VOLUME [SL] [TP]")
                return
            
            symbol = args[0].upper()
            volume = float(args[1].strip('[]'))
            sl = float(args[2].strip('[]')) if len(args) > 2 else 0.0
            tp = float(args[3].strip('[]')) if len(args) > 3 else 0.0
            
            await update.message.reply_text(f"⏳ Placing {order_type} {symbol} {volume}...")
            
            result = mt5_interface.place_order(symbol, order_type, volume, sl, tp)
            
            if result:
                 await update.message.reply_text(f"✅ Order Placed: {order_type} {symbol} {volume}\nTicket: {result.order}")
            else:
                 await update.message.reply_text(f"❌ Order Failed. Check logs.")

        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._manual_trade(update, context, "BUY")

    async def sell_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._manual_trade(update, context, "SELL")

    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually trigger market report."""
        from modules.market_analysis import market_analyzer 
        
        args = context.args
        symbol = args[0].upper() if args else Config.SYMBOL_LIST[0]
        
        await update.message.reply_text(f"🔍 Analyzing {symbol}...")
        report = market_analyzer.get_market_report(symbol)
        if report:
            await update.message.reply_text(report, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Analysis failed or no data.")

    async def send_message(self, text):
        """Sends a message to the configured chat ID."""
        if not self.application:
            return
        
        target_id = self.chat_id
        if not target_id:
             logger.warning("Cannot send proactive message: TELEGRAM_CHAT_ID not set.")
             return

        try:
            await self.application.bot.send_message(chat_id=target_id, text=text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send Telegram msg: {e}")

    async def run(self):
        """Starts the bot polling."""
        if not Config.TELEGRAM_TOKEN:
            logger.error("No Telegram Token provided")
            return

        self.application = ApplicationBuilder().token(Config.TELEGRAM_TOKEN).read_timeout(30).write_timeout(30).connect_timeout(30).build()
        
        # Commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("on", self.on_command))
        self.application.add_handler(CommandHandler("off", self.off_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("balance", self.status_command))
        self.application.add_handler(CommandHandler("buy", self.buy_command))
        self.application.add_handler(CommandHandler("sell", self.sell_command))
        self.application.add_handler(CommandHandler("report", self.report_command))
        
        # Callbacks (Buttons)
        self.application.add_handler(CallbackQueryHandler(self.button_callback))

        logger.info("Telegram Bot Polling Started...")
        
        # We use clean=True to ignore updates while offline if needed, but not standard in v20
        # This will block unless we run it in a task. 
        # Since we want to run this ALONGSIDE the trading loop,
        # we generally should use `initialize`, `start`, `updater.start_polling` if we want manual control,
        # or use run_polling() if it's the main entry point.
        # Since we have a main loop for trading, we should probably run this as a background task.
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep the task alive
        while True:
            await asyncio.sleep(3600)

    async def stop(self):
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

telegram_bot = TelegramBot()
