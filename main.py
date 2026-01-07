import asyncio
import time
import sys
from config import Config
from modules.logger import logger
from modules.mt5_interface import mt5_interface
from modules.risk_manager import risk_manager
from modules.strategy import strategy
from modules.telegram_bot import telegram_bot
from modules.market_analysis import market_analyzer

async def trading_loop():
    """Core Trading Logic Loop."""
    logger.info("Trading Loop Started")
    
    # Initial Setup
    if not mt5_interface.initialize():
        logger.critical("MT5 Initialization Failed. Exiting.")
        return

    account = mt5_interface.get_account_info()
    if account:
        risk_manager.set_daily_start_balance(account['balance'])
    
    last_analysis_time = 0
    ANALYSIS_INTERVAL = 1800 # 30 minutes in seconds

    while True:
        try:
            # maintain connection
            if not mt5_interface.connected:
                 if not mt5_interface.initialize():
                     logger.error("MT5 Reconnection failed")
                     await asyncio.sleep(60)
                     continue

            # Check if trading allowed (Global Switch)
            if not telegram_bot.trading_enabled:
                await asyncio.sleep(5)
                continue

            # Check Risk Limits
            can_trade, reason = risk_manager.can_trade()
            if not can_trade:
                # Log once per hour or change status?
                # logger.debug(f"Risk Check: {reason}") 
                await asyncio.sleep(60) 
                continue

            # --- MARKET ANALYSIS REPORTING ---
            current_time = time.time()
            if current_time - last_analysis_time > ANALYSIS_INTERVAL:
                for symbol in Config.SYMBOL_LIST:
                    report = market_analyzer.get_market_report(symbol)
                    if report:
                        await telegram_bot.send_message(report)
                        logger.info(f"Sent market report for {symbol}")
                last_analysis_time = current_time
            # ---------------------------------

            for symbol in Config.SYMBOL_LIST:
                # Check for existing positions?
                positions = mt5_interface.get_positions()
                symbol_positions = [p for p in positions if p['symbol'] == symbol]
                
                # Simple rule: Only 1 trade per symbol at a time
                if len(symbol_positions) > 0:
                    continue

                # Run Strategy
                signal_data = strategy.get_signal(symbol)
                
                if signal_data and signal_data['signal']:
                    logger.info(f"SIGNAL FOUND: {symbol} {signal_data['signal']}")
                    
                    # Calculate position size
                    volume = risk_manager.calculate_lot_size(symbol, signal_data['sl_pips'])
                    if volume <= 0:
                        logger.warning(f"Calculated volume 0 for {symbol}. Skipped.")
                        continue
                        
                    # Execute 3 times as requested ("3 ta lot")
                    trades_opened = 0
                    for i in range(3):
                        result = mt5_interface.place_order(
                            symbol, 
                            signal_data['signal'], 
                            volume, 
                            signal_data['sl'], 
                            signal_data['tp']
                        )
                        if result:
                            trades_opened += 1
                            risk_manager.trades_today += 1
                    
                    if trades_opened > 0:
                        msg = (
                            f"🚀 *New Trade Executed (x{trades_opened})*\n"
                            f"Symbol: {symbol}\n"
                            f"Type: {signal_data['signal']}\n"
                            f"Volume: {volume} x {trades_opened}\n"
                            f"Price: {signal_data['price']}\n"
                            f"SL: {signal_data['sl']}\n"
                            f"TP: {signal_data['tp']}"
                        )
                        await telegram_bot.send_message(msg)

            # Sleep: Check every candle close? Or every 10 seconds?
            # M5 strategy -> check frequently enough to catch entry.
            await asyncio.sleep(10)
            
            # Simple heartbeat every ~1 minute
            if int(time.time()) % 60 < 10:
                logger.info("Scanning markets for signals...")

        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            await asyncio.sleep(10)

async def main():
    # Start Telegram in background
    tg_task = asyncio.create_task(telegram_bot.run())
    
    # Start Trading Loop
    await trading_loop()
    
    # Wait?
    await tg_task

if __name__ == "__main__":

        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        mt5_interface.shutdown()
        print("Bot Stopped.")
