import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Telegram
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # MT5
    MT5_LOGIN = int(os.getenv("MT5_LOGIN")) if os.getenv("MT5_LOGIN") else 0
    MT5_PASSWORD = os.getenv("MT5_PASSWORD")
    MT5_SERVER = os.getenv("MT5_SERVER")
    MT5_PATH = os.getenv("MT5_PATH")

    # Trading Defaults
    SYMBOL_LIST = ["EURUSD", "GBPUSD", "XAUUSD"]  # Default list
    TIMEFRAME_HTF = "H1"
    TIMEFRAME_LTF = "M1"
    
    # Risk Management
    RISK_PER_TRADE = float(os.getenv("RISK_PERCENT", 2.0))
    MAX_DAILY_DD = float(os.getenv("MAX_DAILY_DRAWDOWN", 5.0))
    MAGIC_NUMBER = 234987
    
    # Strategy
    RSI_PERIOD = 14
    EMA_FAST = 9  # Razgon Mode: Fast Scalping
    EMA_SLOW = 21 # Razgon Mode: Fast Trend
    ATR_PERIOD = 14
    
    # Directories
    LOG_DIR = os.path.join(os.getcwd(), "logs")
    DATA_DIR = os.path.join(os.getcwd(), "data")

    @staticmethod
    def validate():
        if not Config.TELEGRAM_TOKEN:
            print("WARNING: TELEGRAM_BOT_TOKEN is missing in .env")
        if not Config.MT5_LOGIN:
            print("WARNING: MT5_LOGIN is missing in .env")
