import os
import time

import bitmex
import numpy as np
from dotenv import load_dotenv
from loguru import logger

from src.trading_engine.utils.bitmex_helpers import (calculate_order_price,
                                                     get_open_positions,
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


def trading_engine():
    """Trading algorithm running forever"""
    while True:
        # get price stability
        trade_ind, average_price, trade_std = price_stability(
            client=BITMEX_CLIENT,
            symbol=SYMBOL,
            stability=STABILITY,
        )

        # check if price stable enough, otherwise wait one minute
        if trade_ind:
            logger.info(f"Start trading, volatility low enough: {trade_std}")

            # set buy order and start order websocket
            bought_successfully = set_first_buy_order(average_price)

            if not bought_successfully:
                logger.info(
                    f"Buy order cancelled, 5 minutes have passed, start over again.."
                )
                continue

            # get buy price and set new buy and sell price
            set_buy_extra_and_sell_order()

            # check if bought extra or sold
            open_position = get_open_positions(BITMEX_CLIENT, SYMBOL)
            # sold position, start trading again
            if len(open_position) == 0:
                get_profit()
                continue
            else:
                # bought extra so new sell order
                set_second_buy_order(open_position)

                # wait for selling
                _ = websocket_open_orders()
                get_profit()

        else:
            logger.info(f"Wait for trading, standard deviation too high: {trade_std}")
            time.sleep(60)


def set_first_buy_order(price):
    """Set first buy order"""
    buy_price = calculate_order_price(
        price=price, margin=(PROFIT_MARGIN / 2), positive=False
    )
    limit_order(BITMEX_CLIENT, SYMBOL, ORDER_QUANTITY, buy_price)
    logger.info(f"Buy order placed: {ORDER_QUANTITY} contract(s) at {buy_price}")
    bought_successfully = websocket_open_orders(timeout=TIMEOUT)
    return bought_successfully


def set_buy_extra_and_sell_order():
    """Set buy extra and sell order"""
    bought_price = get_open_positions(BITMEX_CLIENT, SYMBOL)[0]["avgEntryPrice"]
    logger.info(
        f"Buy order filled, open position: {ORDER_QUANTITY} contract(s) at {bought_price}"
    )
    buy_extra_price = calculate_order_price(
        price=bought_price, margin=BUY_EXTRA_MARGIN, positive=False
    )
    sell_price = calculate_order_price(
        price=bought_price, margin=PROFIT_MARGIN, positive=True
    )
    limit_order(BITMEX_CLIENT, SYMBOL, ORDER_QUANTITY, buy_extra_price)
    limit_order(BITMEX_CLIENT, SYMBOL, -ORDER_QUANTITY, sell_price)
    logger.info(f"Buy order placed: {ORDER_QUANTITY} contract(s) at {buy_extra_price}")
    logger.info(f"Sell order placed: {-ORDER_QUANTITY} contract(s) at {sell_price}")
    _ = websocket_open_orders()


def set_second_buy_order(open_position):
    """Set first buy order"""
    open_price = open_position[0]["avgEntryPrice"]
    open_quantity = open_position[0]["currentQty"]
    logger.info(
        f"Buy order filled, open position: {open_quantity} contract(s) at {open_price}"
    )
    sell_price = calculate_order_price(
        price=open_price, margin=PROFIT_MARGIN, positive=True
    )
    limit_order(BITMEX_CLIENT, SYMBOL, -open_quantity, sell_price)
    logger.info(f"Sell order placed: {-open_quantity} contract(s) at {sell_price}")


def get_profit():
    """Get profit"""
    sold_price = None
    sold_quantity = None
    profit_made = None
    logger.info(f"Sell order filled: {sold_quantity} contract(s) at {sold_price}")
    logger.success(f"Done trading, profit made: {profit_made} BTC (... euro)")


if __name__ == "__main__":
    trading_engine()
