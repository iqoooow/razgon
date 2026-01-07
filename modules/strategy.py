import pandas as pd
import numpy as np
from config import Config
from modules.logger import logger
from modules.mt5_interface import mt5_interface

class Strategy:
    def __init__(self):
        pass

    def calculate_indicators(self, df):
        """Adds technical indicators to the DataFrame using pure pandas."""
        close = df['close']
        high = df['high']
        low = df['low']
        
        # 1. EMA
        df['EMA_Fast'] = close.ewm(span=Config.EMA_FAST, adjust=False).mean()
        df['EMA_Slow'] = close.ewm(span=Config.EMA_SLOW, adjust=False).mean()
        
        # 2. RSI (Wilder's Smoothing)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0))
        loss = (-delta.where(delta < 0, 0))
        
        # First regular SMA for initial values (optional but standard usually uses ewm directly or simple sma first)
        # Using EWM with alpha=1/14 for Wilder's
        # pandas ewm(com=period-1, adjust=False) is equivalent to Wilder's
        period = Config.RSI_PERIOD
        avg_gain = gain.ewm(com=period-1, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(com=period-1, min_periods=period, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 3. ATR (Wilder's Smoothing)
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        df['ATR'] = tr.ewm(com=Config.ATR_PERIOD-1, min_periods=Config.ATR_PERIOD, adjust=False).mean()
        
        return df

    def get_signal(self, symbol):
        """
        Analyzes the market and returns a signal with MTF filtering.
        """
        try:
            # 1. Fetch HTF Data (H1) for trend confirmation
            df_h1 = mt5_interface.get_data(symbol, "H1", n_bars=100)
            if df_h1 is None or len(df_h1) < 50:
                return None
            
            ema_h1_fast = df_h1['close'].ewm(span=Config.EMA_FAST, adjust=False).mean()
            ema_h1_slow = df_h1['close'].ewm(span=Config.EMA_SLOW, adjust=False).mean()
            h1_uptrend = ema_h1_fast.iloc[-1] > ema_h1_slow.iloc[-1]
            h1_downtrend = ema_h1_fast.iloc[-1] < ema_h1_slow.iloc[-1]

            # 2. Fetch LTF Data (M1)
            df = mt5_interface.get_data(symbol, Config.TIMEFRAME_LTF, n_bars=300)
            if df is None:
                return None

            df = self.calculate_indicators(df)
            if df['EMA_Slow'].isnull().iloc[-1] or df['RSI'].isnull().iloc[-1]:
                return None

            current = df.iloc[-1]
            prev = df.iloc[-2]
            
            signal = None
            sl_price = 0.0
            tp_price = 0.0
            
            # --- STRATEGY LOGIC ---
            # LTF Alignment
            ltf_uptrend = current['close'] > current['EMA_Slow']
            ltf_downtrend = current['close'] < current['EMA_Slow']
            
            # Cross Logic (Fast > Slow)
            fast_cross_up = (prev['EMA_Fast'] <= prev['EMA_Slow']) and (current['EMA_Fast'] > current['EMA_Slow'])
            fast_cross_down = (prev['EMA_Fast'] >= prev['EMA_Slow']) and (current['EMA_Fast'] < current['EMA_Slow'])
            
            # Trend Strength Filter: EMA gap should be widening or at least significant
            curr_gap = abs(current['EMA_Fast'] - current['EMA_Slow'])
            prev_gap = abs(prev['EMA_Fast'] - prev['EMA_Slow'])
            is_trending_strong = curr_gap > prev_gap # Gap is widening

            # Overextension Filter: Don't buy/sell if price is too far from EMA_Slow
            atr = current['ATR']
            dist_from_ema = abs(current['close'] - current['EMA_Slow'])
            is_overextended = dist_from_ema > (2.0 * atr)

            # Candle Confirmation
            is_bullish_candle = current['close'] > current['open']
            is_bearish_candle = current['close'] < current['open']
            
            # Symbol-Specific SL Multiplier
            # GBPUSD needs more room due to volatility
            sl_mult = 3.5 if symbol == "GBPUSD" else 2.0
            
            # BUY SIGNAL
            if (h1_uptrend and ltf_uptrend and fast_cross_up and is_trending_strong and
                not is_overextended and is_bullish_candle and 
                current['RSI'] > 50 and current['RSI'] < 75):
                signal = 'BUY'
                sl_price = current['low'] - (sl_mult * atr) 
                risk_dist = current['close'] - sl_price
                tp_price = current['close'] + (risk_dist * 0.7) # Faster TP for GBPUSD

            # SELL SIGNAL
            elif (h1_downtrend and ltf_downtrend and fast_cross_down and is_trending_strong and
                  not is_overextended and is_bearish_candle and 
                  current['RSI'] < 50 and current['RSI'] > 25):
                signal = 'SELL'
                sl_price = current['high'] + (sl_mult * atr)
                risk_dist = sl_price - current['close']
                tp_price = current['close'] - (risk_dist * 0.7) # Faster TP for GBPUSD

            if signal:
                sl_dist = abs(current['close'] - sl_price)
                sym_info = mt5_interface.get_symbol_info(symbol)
                point = sym_info.point if sym_info else 0.0001
                sl_pips = sl_dist / (point * 10) 

                logger.info(f"SIGNAL {signal} for {symbol} confirmed. Dist: {dist_from_ema:.5f}, ATR: {atr:.5f}, SL_Mult: {sl_mult}")
                return {
                    'signal': signal,
                    'sl': sl_price,
                    'tp': tp_price,
                    'sl_pips': sl_pips,
                    'price': current['close'],
                    'time': current['time']
                }

            return None

        except Exception as e:
            logger.error(f"Strategy Error for {symbol}: {e}")
            return None

strategy = Strategy()
