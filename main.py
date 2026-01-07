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
    if mt5_interface.initialize():
        account = mt5_interface.get_account_info()
        if account:
            risk_manager.set_daily_start_balance(account['balance'])
    else:
        logger.error("MT5 Initialization Failed. Trading loop will wait for connection.")
    
    last_analysis_time = 0
    ANALYSIS_INTERVAL = 1800 # 30 minutes in seconds

    while True:
        try:
            # Heartbeat every ~1 minute
            if int(time.time()) % 60 < 11:
                status = "Trading Active" if telegram_bot.trading_enabled else "Trading Paused (Waiting for /on)"
                logger.info(f"Heartbeat: {status}")

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

            # --- POSITION MANAGEMENT (Break-Even) ---
            positions = mt5_interface.get_positions()
            for pos in positions:
                symbol = pos['symbol']
                ticket = pos['ticket']
                open_price = pos['price_open']
                current_price = pos['price_current']
                current_sl = pos['sl']
                tp = pos['tp']
                
                # Calculate current profit in pips/points
                # For long: profit = current - open
                # For short: profit = open - current
                if pos['type'] == 0: # BUY
                    profit_points = current_price - open_price
                    # Move to BE if profit > 40% of TP distance
                    tp_dist = abs(tp - open_price) if tp > 0 else 0
                    if tp_dist > 0 and current_sl < open_price and profit_points > (tp_dist * 0.4):
                        new_sl = open_price + (mt5_interface.get_symbol_info(symbol).point * 10) # BE + 1 pip
                        mt5_interface.modify_position(ticket, new_sl, tp)
                        logger.info(f"Moved BUY {symbol} to Break-Even")
                        
                elif pos['type'] == 1: # SELL
                    profit_points = open_price - current_price
                    tp_dist = abs(tp - open_price) if tp > 0 else 0
                    if tp_dist > 0 and current_sl > open_price and profit_points > (tp_dist * 0.4):
                        new_sl = open_price - (mt5_interface.get_symbol_info(symbol).point * 10) # BE + 1 pip
                        mt5_interface.modify_position(ticket, new_sl, tp)
                        logger.info(f"Moved SELL {symbol} to Break-Even")
            # ----------------------------------------

            for symbol in Config.SYMBOL_LIST:
                # Check for existing positions?
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
            

        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            await asyncio.sleep(10)

async def main():
    # Start Telegram in background
    tg_task = asyncio.create_task(telegram_bot.run())
    
    # Start Trading Loop
    try:
        await trading_loop()
    except Exception as e:
        logger.error(f"Trading loop crashed: {e}")
    
    # Keep the task alive indefinitely for Telegram
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":

        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        mt5_interface.shutdown()
        print("Bot Stopped.")
