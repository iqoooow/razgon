from datetime import datetime, time
import pytz
from config import Config
from modules.logger import logger
from modules.mt5_interface import mt5_interface

class RiskManager:
    def __init__(self):
        self.daily_start_balance = 0.0
        self.trades_today = 0
        self.max_trades_per_day = 15 # Updated Limit
        
        # Define session times (UTC)
        # London: 08:00 - 17:00, NY: 13:00 - 22:00. Combined: 08:00 - 22:00
        self.session_start = time(8, 0)
        self.session_end = time(22, 0)

    def set_daily_start_balance(self, balance):
        """Must be called at start of day or bot restart."""
        self.daily_start_balance = balance
        logger.info(f"Daily start balance set to: {self.daily_start_balance}")

    def calculate_lot_size(self, symbol, sl_pips):
        """
        Calculates lot size. 
        Fixed to 0.01 as per user request (small balance).
        """
        return 0.01

    def check_daily_drawdown(self):
        """Returns False if daily drawdown limit is reached."""
        account = mt5_interface.get_account_info()
        if not account:
            return False
            
        equity = account['equity']
        current_loss_pct = ((self.daily_start_balance - equity) / self.daily_start_balance) * 100
        
        if current_loss_pct >= Config.MAX_DAILY_DD:
            logger.warning(f"Daily Drawdown hit! -{current_loss_pct:.2f}% >= {Config.MAX_DAILY_DD}%")
            return False
            
        return True

    def _is_trading_session(self):
        """Checks if current time is within allowed trading hours (London/NY)."""
        now = datetime.utcnow().time()
        if self.session_start <= now <= self.session_end:
            return True
        return False

    def can_trade(self):
        """Master check for allowing new trades."""
        if not self._is_trading_session():
            return False, "Outside Trading Session"
            
        if not self.check_daily_drawdown():
            return False, "Daily Drawdown Limit Hit"
            
        if self.trades_today >= self.max_trades_per_day:
            return False, "Max Daily Trades Reached"
            
        # TODO: Add specific news check here
        
        return True, "OK"

risk_manager = RiskManager()
