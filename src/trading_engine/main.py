import os

import bitmex
from dotenv import load_dotenv

from src.trading_engine.utils.constants import (BUY_EXTRA_MARGIN,
                                                ORDER_QUANTITY, PROFIT_MARGIN,
                                                STABILITY, SYMBOL, TIMEOUT)
from src.trading_engine.utils.trading_algorithm import TradingAlgorthm

load_dotenv()

BITMEX_CLIENT = bitmex.bitmex(
    api_key=os.getenv("BITMEX_API_KEY"),
    api_secret=os.getenv("BITMEX_API_SECRET"),
    test=False,
)

if __name__ == "__main__":
    TradingAlgorthm(
        client=BITMEX_CLIENT,
        symbol=SYMBOL,
        stability=STABILITY,
        profit_margin=PROFIT_MARGIN,
        buy_extra_margin=BUY_EXTRA_MARGIN,
        order_size=ORDER_QUANTITY,
        timeout=TIMEOUT,
    ).run()
