import os
import time

import bitmex
import numpy as np
from dotenv import load_dotenv
from loguru import logger

from src.trading_engine.utils.bitmex_helpers import (get_open_positions,
                                                     limit_order,
                                                     websocket_open_orders)
from src.trading_engine.utils.constants import (BUY_EXTRA_MARGIN,
                                                ORDER_QUANTITY, PROFIT_MARGIN,
                                                STABILITY, SYMBOL, TIMEOUT)
from src.trading_engine.utils.stabile_trade import price_stability

load_dotenv()

BITMEX_CLIENT = bitmex.bitmex(
    api_key=os.getenv("BITMEX_API_KEY"),
    api_secret=os.getenv("BITMEX_API_SECRET"),
    test=False,
)

if __name__ == "__main__":

    while True:
        # check if we can start trading
        trade_ind, average_price, trade_std = price_stability(
            client=BITMEX_CLIENT,
            symbol=SYMBOL,
            stability=STABILITY,
        )

        if trade_ind:
            logger.info(f"Start trading, volatility low enough: {trade_std}")

            # set buy order and start order websocket
            buy_price = np.round(
                average_price - ((PROFIT_MARGIN / 2) * average_price), 1
            )
            limit_order(BITMEX_CLIENT, SYMBOL, ORDER_QUANTITY, buy_price)
            bought_successfully = websocket_open_orders(timeout=TIMEOUT)

            if not bought_successfully:
                continue

            # get buy price and set new buy and sell price
            bought_price = get_open_positions(BITMEX_CLIENT, SYMBOL)[0]["avgEntryPrice"]
            buy_extra_price = np.round(
                bought_price - (BUY_EXTRA_MARGIN * bought_price), 1
            )
            sell_price = np.round(bought_price + (PROFIT_MARGIN * bought_price), 1)
            limit_order(BITMEX_CLIENT, SYMBOL, ORDER_QUANTITY, buy_extra_price)
            limit_order(BITMEX_CLIENT, SYMBOL, -ORDER_QUANTITY, sell_price)
            _ = websocket_open_orders()

            # check if bought extra or sold
            open_position = get_open_positions(BITMEX_CLIENT, SYMBOL)
            if len(open_position) == 0:
                print("done trading")
            else:
                open_price = open_position[0]["avgEntryPrice"]
                open_quantity = open_position[0]["currentQty"]
                sell_price = np.round(open_price + (PROFIT_MARGIN * open_price), 1)
                limit_order(BITMEX_CLIENT, SYMBOL, -ORDER_QUANTITY, sell_price)
                _ = websocket_open_orders()

        else:
            logger.info(f"Wait for trading, standard deviation too high: {trade_std}")
            time.sleep(60)
