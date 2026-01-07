
import asyncio
import pandas as pd
from modules.strategy import strategy
from modules.mt5_interface import mt5_interface
from unittest.mock import MagicMock, patch

async def simulate_strategy():
    print("Testing Strategy with Simulated Data...")
    symbol = "EURUSD"
    
    # Mock MT5 Data HTF (H1) - UPTREND
    h1_data = {
        'time': range(100),
        'open': [1.1000] * 100,
        'high': [1.1100] * 100,
        'low': [1.0900] * 100,
        'close': [1.1000 + (i * 0.0001) for i in range(100)], # Rising
        'tick_volume': [100] * 100
    }
    df_h1 = pd.DataFrame(h1_data)

    # Mock MT5 Data LTF (M1) - BUY SIGNAL setup
    m1_data = {
        'time': range(300),
        'open': [1.1050] * 300,
        'high': [1.1060] * 300,
        'low': [1.1040] * 300,
        'close': [1.1050] * 300,
        'tick_volume': [10] * 300
    }
    # Modify last few bars to create a cross and bullish candle
    # EMA Fast (9), EMA Slow (21)
    df_m1 = pd.DataFrame(m1_data)
    
    # Force a cross up
    # prev: Fast <= Slow -> 1.1040, 1.1050
    # curr: Fast > Slow -> 1.1080, 1.1060
    
    with patch('modules.mt5_interface.mt5_interface.get_data') as mock_get_data:
        # First call for H1, second for M1
        mock_get_data.side_effect = [df_h1, df_m1]
        mock_sym_info = MagicMock()
        mock_sym_info.point = 0.00001
        with patch('modules.mt5_interface.mt5_interface.get_symbol_info', return_value=mock_sym_info):
            # We need to manually inject technical indicators or rely on real calculation
            # Since calculate_indicators is pure, it will run.
            # We just need to ensure the logic triggers.
            
            # Manually set the last rows to trigger the logic
            # Fast cross up: prev['EMA_Fast'] <= prev['EMA_Slow'] and current['EMA_Fast'] > current['EMA_Slow']
            # indicators are calculated within get_signal
            
            # To make it easier, let's just check if it runs without errors first
            signal = strategy.get_signal(symbol)
            print(f"Signal Result: {signal}")

if __name__ == "__main__":
    asyncio.run(simulate_strategy())
