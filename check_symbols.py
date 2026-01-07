
import asyncio
from modules.mt5_interface import mt5_interface

async def check_symbols():
    symbols = ["EURUSD", "GBPUSD", "XAUUSD"]
    if not mt5_interface.initialize():
        print("MT5 Not connected")
        return
        
    for sym in symbols:
        info = mt5_interface.get_symbol_info(sym)
        if info:
            print(f"\n--- {sym} ---")
            print(f"Spread: {info.spread}")
            print(f"Stops Level: {info.trade_stops_level}")
            print(f"Point: {info.point}")
            print(f"Min Volume: {info.volume_min}")
        else:
            print(f"Could not get info for {sym}")

if __name__ == "__main__":
    asyncio.run(check_symbols())
