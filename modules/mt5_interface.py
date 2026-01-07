import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from config import Config
from modules.logger import logger

class MT5Interface:
    def __init__(self):
        self.connected = False

    def initialize(self):
        """Initializes connection to MT5 terminal."""
        if not mt5.initialize(path=Config.MT5_PATH):
            logger.error(f"MT5 initialize() failed, error code = {mt5.last_error()}")
            return False
        
        # Login (Optional if terminal is already logged in, but good practice)
        if Config.MT5_LOGIN:
            authorized = mt5.login(
                login=Config.MT5_LOGIN, 
                password=Config.MT5_PASSWORD, 
                server=Config.MT5_SERVER
            )
            if not authorized:
                logger.error(f"MT5 login failed, error code = {mt5.last_error()}")
                return False
        
        self.connected = True
        logger.info(f"Connected to MT5: {mt5.terminal_info()}")
        return True

    def shutdown(self):
        mt5.shutdown()
        self.connected = False
        logger.info("MT5 connection closed")

    def get_symbol_info(self, symbol):
        """Get symbol validation and info."""
        info = mt5.symbol_info(symbol)
        if not info:
            logger.error(f"Symbol {symbol} not found")
            return None
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                logger.error(f"Symbol {symbol} select failed")
                return None
        return info

    def get_data(self, symbol, timeframe_str, n_bars=500):
        """Fetch historical data as DataFrame."""
        tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        tf = tf_map.get(timeframe_str, mt5.TIMEFRAME_H1)
        
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, n_bars)
        if rates is None or len(rates) == 0:
            logger.error(f"Failed to get data for {symbol} (Error: {mt5.last_error()})")
            return None
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_account_info(self):
        """Get account balance, equity, margin."""
        info = mt5.account_info()
        if not info:
            logger.error("Failed to get account info")
            return None
        return info._asdict()

    def place_order(self, symbol, order_type, volume, sl=0.0, tp=0.0, deviation=20):
        """Places a market order."""
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return None

        action_type = mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL
        price = symbol_info.ask if order_type == "BUY" else symbol_info.bid
        
        # Determine correct filling mode
        # Fix for missing constants: FOK=1, IOC=2
        filling_type = mt5.ORDER_FILLING_FOK
        
        # Check flags (bitmask)
        # 1 = SYMBOL_FILLING_FOK
        # 2 = SYMBOL_FILLING_IOC
        filling_mode = symbol_info.filling_mode
        
        if filling_mode & 2:
            filling_type = mt5.ORDER_FILLING_IOC
        elif filling_mode & 1:
            filling_type = mt5.ORDER_FILLING_FOK
            
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": action_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": deviation,
            "magic": Config.MAGIC_NUMBER,
            "comment": "RazgonBot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result.comment}, retcode={result.retcode}")
            return None
            
        logger.info(f"Order placed: {order_type} {volume} {symbol} @ {price}")
        return result

    def get_positions(self):
        """Get current open positions."""
        positions = mt5.positions_get()
        if positions is None:
            return []
        
        # Return as list of dicts
        return [p._asdict() for p in positions if p.magic == Config.MAGIC_NUMBER]

    def modify_position(self, ticket, sl, tp):
        """Modify SL/TP of a position."""
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": float(sl),
            "tp": float(tp)
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
             logger.error(f"Modify failed for ticket {ticket}: {result.comment}")
             return False
        return True

mt5_interface = MT5Interface()
