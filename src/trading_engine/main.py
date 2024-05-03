import os
import time

import bitmex
import numpy as np
from dotenv import load_dotenv
from loguru import logger

from src.trading_engine.utils.bitmex_helpers import (
    WebsocketPrice,
    calculate_order_price,
    cancel_open_orders,
    get_open_orders,
    get_open_positions,
    limit_order,
)
from src.trading_engine.utils.constants import (
    BUY_EXTRA_MARGIN,
    ORDER_QUANTITY,
    PROFIT_MARGIN,
    STABILITY,
    SYMBOL,
    TIMEOUT,
)
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
            bought_successfully, order_id = set_first_buy_order(average_price)

            if not bought_successfully:
                cancel_open_orders(BITMEX_CLIENT)
                logger.info(
                    "Buy order cancelled, 5 minutes have passed, start over again.."
                )
                continue

            # get buy price and set new buy and sell price
            sold_successfully, new_order_id = set_buy_extra_and_sell_order(order_id)

            # sold position, start trading again
            if sold_successfully:
                get_profit()
                continue
            else:
                # bought extra so new sell order
                sold_successfully = set_sell_order(order_id, new_order_id)
                get_profit()
                continue

        else:
            logger.info(f"Wait for trading, standard deviation too high: {trade_std}")
            time.sleep(60)


def set_first_buy_order(price):
    """Set first buy order"""
    buy_price = calculate_order_price(
        price=price, margin=(PROFIT_MARGIN / 2), positive=False
    )
    order_id = limit_order(BITMEX_CLIENT, SYMBOL, ORDER_QUANTITY, buy_price)
    logger.info(f"Buy order placed: {ORDER_QUANTITY} contract(s) at {buy_price}")
    while True:
        buy_price_reached, _, timeout_reached = WebsocketPrice(
            client=BITMEX_CLIENT, symbol=SYMBOL, buy_price=buy_price, timeout=TIMEOUT
        ).start_websocket()
        if buy_price_reached:
            return True, order_id
        elif timeout_reached:
            return False, order_id


def set_buy_extra_and_sell_order(order_id):
    """Set buy extra and sell order"""
    buy_order = get_open_orders(BITMEX_CLIENT, order_id)
    if buy_order["ordStatus"] == "Filled":
        bought_price = buy_order["avgPx"]
    else:
        raise Exception("Buy order not filled yet..")

    logger.info(
        f"Buy order filled, open position: {ORDER_QUANTITY} contract(s) at {bought_price}"
    )
    buy_extra_price = calculate_order_price(
        price=bought_price, margin=BUY_EXTRA_MARGIN, positive=False
    )
    sell_price = calculate_order_price(
        price=bought_price, margin=PROFIT_MARGIN, positive=True
    )
    buy_order_id = limit_order(BITMEX_CLIENT, SYMBOL, ORDER_QUANTITY, buy_extra_price)
    sell_order_id = limit_order(BITMEX_CLIENT, SYMBOL, -ORDER_QUANTITY, sell_price)
    logger.info(f"Buy order placed: {ORDER_QUANTITY} contract(s) at {buy_extra_price}")
    logger.info(f"Sell order placed: {-ORDER_QUANTITY} contract(s) at {sell_price}")

    while True:
        buy_price_reached, sell_price_reached, _ = WebsocketPrice(
            client=BITMEX_CLIENT,
            symbol=SYMBOL,
            buy_price=buy_extra_price,
            sell_price=sell_price,
        ).start_websocket()

        if sell_price_reached:
            cancel_open_orders(BITMEX_CLIENT)
            return True, sell_order_id
        elif buy_price_reached:
            cancel_open_orders(BITMEX_CLIENT)
            return False, buy_order_id


def set_sell_order(order_id, new_order_id):
    """Set first buy order"""
    first_buy_order = get_open_orders(BITMEX_CLIENT, order_id)
    second_buy_order = get_open_orders(BITMEX_CLIENT, new_order_id)

    if second_buy_order["ordStatus"] == "Filled":
        second_buy_price = second_buy_order["avgPx"]
        first_buy_price = first_buy_order["avgPx"]
    else:
        raise Exception("Buy order not filled yet..")

    average_price = np.round((first_buy_price + second_buy_price) / 2, 2)

    logger.info(
        f"Buy order filled, open position: {ORDER_QUANTITY*2} contract(s) at {average_price}"
    )

    sell_price = calculate_order_price(
        price=average_price, margin=PROFIT_MARGIN, positive=True
    )
    order_id = limit_order(BITMEX_CLIENT, SYMBOL, -2 * ORDER_QUANTITY, sell_price)
    logger.info(f"Sell order placed: {-2 * ORDER_QUANTITY} contract(s) at {sell_price}")

    while True:
        _, sell_price_reached, _ = WebsocketPrice(
            client=BITMEX_CLIENT,
            symbol=SYMBOL,
            sell_price=sell_price,
        ).start_websocket()

        if sell_price_reached:
            return True


def get_profit():
    """Get profit"""
    sold_price = None
    sold_quantity = None
    profit_made = None
    logger.info(f"Sell order filled: {sold_quantity} contract(s) at {sold_price}")
    logger.success(f"Done trading, profit made: {profit_made} BTC (... euro)")


if __name__ == "__main__":
    trading_engine()
