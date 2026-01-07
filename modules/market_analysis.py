import pandas as pd
import numpy as np
from config import Config
from modules.logger import logger
from modules.mt5_interface import mt5_interface

class MarketAnalyzer:
    def __init__(self):
        pass

    def identify_trend(self, df):
        """
        Determines trend based on EMA alignment and slope.
        Returns: 'UPTREND', 'DOWNTREND', 'RANGING'
        """
        if df is None or len(df) < 50:
            return "UNKNOWN"
        
        current = df.iloc[-1]
        
        # EMA Alignment
        ema_fast = current['EMA_Fast']
        ema_slow = current['EMA_Slow']
        
        # Simple Slope Check (comparing current with 5 bars ago)
        past = df.iloc[-5]
        slope_fast = ema_fast - past['EMA_Fast']
        slope_slow = ema_slow - past['EMA_Slow']
        
        if ema_fast > ema_slow and slope_slow > 0:
            return "UPTREND 🟢"
        elif ema_fast < ema_slow and slope_slow < 0:
            return "DOWNTREND 🔴"
        else:
            return "RANGING 🟡"

    def find_levels(self, df, lookback=20):
        """
        Identifies key Support and Resistance levels using simple local min/max.
        Returns: list of prices
        """
        levels = []
        if df is None or len(df) < lookback:
            return levels

        # Minimal implementation of fractals/swings
        for i in range(lookback, len(df) - lookback):
            # Pivot High
            if all(df['high'].iloc[i] > df['high'].iloc[i-k] for k in range(1, lookback)) and \
               all(df['high'].iloc[i] > df['high'].iloc[i+k] for k in range(1, lookback)):
                levels.append({'type': 'RESISTANCE', 'price': df['high'].iloc[i]})
            
            # Pivot Low
            if all(df['low'].iloc[i] < df['low'].iloc[i-k] for k in range(1, lookback)) and \
               all(df['low'].iloc[i] < df['low'].iloc[i+k] for k in range(1, lookback)):
                levels.append({'type': 'SUPPORT', 'price': df['low'].iloc[i]})
        
        # Filter levels close to each other? (Optional optimization)
        return levels

    def get_market_report(self, symbol):
        """
        Generates a comprehensive market status report string (Uzbek).
        """
        try:
            # We use HTF for broad context analysis
            df = mt5_interface.get_data(symbol, Config.TIMEFRAME_HTF, n_bars=200)
            if df is None:
                return None
            
            # Re-calculate indicators
            df['EMA_Fast'] = df['close'].ewm(span=Config.EMA_FAST, adjust=False).mean()
            df['EMA_Slow'] = df['close'].ewm(span=Config.EMA_SLOW, adjust=False).mean()

            trend = self.identify_trend(df)
            levels = self.find_levels(df)
            
            current_price = df['close'].iloc[-1]
            
            # Translate Trend
            trend_map = {
                "UPTREND 🟢": "Tepaga (O'sish) 🟢",
                "DOWNTREND 🔴": "Pastga (Tushish) 🔴",
                "RANGING 🟡": "Yonlama (Flat) 🟡"
            }
            trend_uz = trend_map.get(trend, trend)

            # Check proximity
            nearby_msg = "✅ Hozircha zona yo'q, yo'l ochiq."
            advice = ""
            
            closest_dist = float('inf')
            closest_level = None
            
            for lvl in levels:
                dist = abs(current_price - lvl['price'])
                if dist < closest_dist:
                    closest_dist = dist
                    closest_level = lvl
            
            # Define "Nearby" as roughly 10-15 pips (0.00100 for forex pairs roughly) or purely relative
            # For simplicity let's assume if it is logically 'close' contextually
            # We will just report the nearest one found
            
            if closest_level:
                lvl_type = "Tepada Kuchli Zona (Qarshilik)" if closest_level['type'] == 'RESISTANCE' else "Pastda Kuchli Zona (Podderjka)"
                nearby_msg = f"⚠️ {lvl_type}: {closest_level['price']:.5f}"
                
                # Context Logic
                if "UPTREND" in trend and closest_level['type'] == 'RESISTANCE' and closest_dist < 0.0020:
                    advice = "💡 Maslahat: Narx o'smoqda lekin kuchli zonaga yaqin. Sotib olish xavfli bo'lishi mumkin."
                elif "DOWNTREND" in trend and closest_level['type'] == 'SUPPORT' and closest_dist < 0.0020:
                    advice = "💡 Maslahat: Narx tushmoqda lekin pastdagi zonaga yaqin. Sotishga shoshilmang."
                elif "UPTREND" in trend:
                    advice = "💡 Maslahat: Trend tepaga. Qulay vaziyatda sotib olish (BUY) izlash mumkin."
                elif "DOWNTREND" in trend:
                    advice = "💡 Maslahat: Trend pastga. Qulay vaziyatda sotish (SELL) izlash mumkin."
                else:
                    advice = "💡 Maslahat: Bozor aniq yo'nalishsiz. Ehtiyot bo'lib, kichik masofalarda savdo qilgan ma'qul."

            report = (
                f"🇺🇿 *Bozor Tahlili: {symbol}*\n"
                f"-----------------------------\n"
                f"📈 *Trend*: {trend_uz}\n"
                f"💰 *Joriy Narx*: {current_price:.5f}\n"
                f"-----------------------------\n"
                f"{nearby_msg}\n\n"
                f"{advice}"
            )
            return report

        except Exception as e:
            logger.error(f"Market Analysis Error {symbol}: {e}")
            return None

market_analyzer = MarketAnalyzer()
