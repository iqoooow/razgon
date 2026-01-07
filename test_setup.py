import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from config import Config
from modules.risk_manager import risk_manager
from modules.strategy import strategy

class TestRazgonBot(unittest.TestCase):
    
    def test_config(self):
        print("\nTesting Config...")
        self.assertTrue(len(Config.SYMBOL_LIST) > 0)
        self.assertEqual(Config.MAGIC_NUMBER, 234987)
        print("Config OK")

    @patch('modules.mt5_interface.mt5_interface.get_account_info')
    @patch('modules.mt5_interface.mt5_interface.get_symbol_info')
    def test_risk_manager(self, mock_symbol, mock_account):
        print("\nTesting Risk Manager...")
        
        # Mock Account: $10,000 Balance
        mock_account.return_value = {'balance': 10000.0, 'equity': 10000.0}
        
        # Mock Symbol: EURUSD, Min Vol 0.01, Step 0.01
        mock_sym_obj = MagicMock()
        mock_sym_obj.volume_min = 0.01
        mock_sym_obj.volume_max = 100.0
        mock_sym_obj.volume_step = 0.01
        mock_symbol.return_value = mock_sym_obj

        # Risk 2% = $200
        # SL 10 pips. 
        # Approx Formula in code: lot = risk / (pips * 10) = 200 / 100 = 2.0 lots
        
        lot = risk_manager.calculate_lot_size("EURUSD", 10)
        print(f"Calculated Lot for $10k, 2% Risk, 10 Pips SL: {lot}")
        self.assertTrue(lot > 0)
        
        # Test Drawdown
        risk_manager.set_daily_start_balance(10000.0)
        self.assertTrue(risk_manager.check_daily_drawdown())
        
        # Simulate loss
        mock_account.return_value = {'balance': 9000.0, 'equity': 9000.0} # -10%
        # Config MAX_DAILY_DD is 5.0
        self.assertFalse(risk_manager.check_daily_drawdown())
        print("Risk Manager OK")

    def test_strategy_indicators(self):
        print("\nTesting Strategy Indicators...")
        # Create dummy DF
        data = {
            'close': [1.1000 + (i*0.0001) for i in range(300)],
            'high': [1.1000 + (i*0.0001) + 0.0005 for i in range(300)],
            'low': [1.1000 + (i*0.0001) - 0.0005 for i in range(300)],
        }
        df = pd.DataFrame(data)
        
        df = strategy.calculate_indicators(df)
        self.assertIn('EMA_Fast', df.columns)
        self.assertIn('EMA_Slow', df.columns)
        self.assertIn('RSI', df.columns)
        self.assertIn('ATR', df.columns)
        print(f"RSI Last: {df['RSI'].iloc[-1]}")
        print("Strategy Indicators OK")

if __name__ == '__main__':
    unittest.main()
