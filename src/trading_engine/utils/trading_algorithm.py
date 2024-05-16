import time

import numpy as np
from dotenv import load_dotenv
from loguru import logger

from src.trading_engine.utils.bitmex_helpers import (WebsocketPrice,
                                                     calculate_order_price,
                                                     cancel_open_orders,
                                                     get_filled_price,
                                                     limit_order)
from src.trading_engine.utils.price_stability import price_stability

load_dotenv()


class TradingAlgorthm:
    """
    Defines the trading algorithm which contains the following steps..
    """

    def __init__(
        self,
        client,
        symbol,
        stability,
        profit_margin,
        buy_extra_margin,
        order_size,
        timeout,
    ):
        self.client = client
        self.symbol = symbol
        self.stability = stability
        self.profit_margin = profit_margin
        self.buy_extra_margin = buy_extra_margin
        self.order_size = order_size
        self.timeout = timeout

    def run(self):
        """
        Runs the trading algorithm
        """
        while True:
            # get price stability
            trade_ind, average_price, trade_std = price_stability(
                client=self.client,
                symbol=self.symbol,
                stability=self.stability,
            )

            # check if price stable enough
            if trade_ind:
                logger.info(f"Start trading, volatility low enough: {trade_std}")

            # if not stable enough, wait a minute and start over
            else:
                logger.info(
                    f"Wait for trading, standard deviation too high: {trade_std}"
                )
                time.sleep(60)
                continue

            # set buy order and start order websocket
            bought_successfully, bought_price = self.set_first_buy_order(average_price)

            # if not bought successfully, start over
            if not bought_successfully:
                cancel_open_orders(self.client)
                logger.info(
                    "Buy order cancelled, 5 minutes have passed, start over again.."
                )
                continue

            # get buy price and set new buy and sell price
            sold_successfully, price = self.set_buy_extra_and_sell_order(bought_price)

            # sold position, start trading again
            if sold_successfully:
                self.get_profit()
                continue
            else:
                # bought extra so new sell order
                sold_successfully = self.set_sell_order(bought_price, price)
                self.get_profit()
                continue

    def set_first_buy_order(self, average_price):
        """
        Set first buy order.

        Returns True if buy price is reached within the timeout time,
        otherwise False.
        """
        # calculate the buy price based on the average price
        buy_price = calculate_order_price(
            price=average_price, margin=(self.profit_margin / 2), positive=False
        )
        # place buy order
        order_id = limit_order(self.client, self.symbol, self.order_size, buy_price)
        logger.info(f"Buy order placed: {self.order_size} contract(s) at {buy_price}")

        # while loop for if connection drops with websocket
        while True:
            buy_price_reached, _, timeout_reached = WebsocketPrice(
                client=self.client,
                symbol=self.symbol,
                buy_price=buy_price,
                timeout=self.timeout,
            ).start_websocket()

            if buy_price_reached:
                # check if buy order filled
                bought_price = get_filled_price(self.client, order_id)

                # TODO: LOG TO DATABASE
                logger.info(
                    f"Buy order filled, open position: {self.order_size} contract(s) at {bought_price}"
                )
                return True, bought_price

            elif timeout_reached:
                return False, None

    def set_buy_extra_and_sell_order(self, bought_price):
        """Set buy extra and sell order"""
        # Calculate buy extra and sell price
        buy_extra_price = self.calculate_order_price(
            price=bought_price, margin=self.buy_extra_margin, positive=False
        )
        sell_price = self.calculate_order_price(
            price=bought_price, margin=self.profit_margin, positive=True
        )

        # Place buy and sell order
        buy_order_id = limit_order(
            self.client, self.symbol, self.order_size, buy_extra_price
        )
        sell_order_id = limit_order(
            self.client, self.symbol, -self.order_size, sell_price
        )
        logger.info(
            f"Buy order placed: {self.order_size} contract(s) at {buy_extra_price}"
        )
        logger.info(
            f"Sell order placed: {-self.order_size} contract(s) at {sell_price}"
        )

        # while loop for if connection drops with websocket
        while True:
            buy_price_reached, sell_price_reached, _ = WebsocketPrice(
                client=self.client,
                symbol=self.symbol,
                buy_price=buy_extra_price,
                sell_price=sell_price,
            ).start_websocket()

            # TODO: LOG BOTH TO DATABASE
            if sell_price_reached:
                cancel_open_orders(self.client)
                sell_price = get_filled_price(self.client, sell_order_id)
                return True, sell_price

            elif buy_price_reached:
                cancel_open_orders(self.client)
                second_buy_price = get_filled_price(self.client, buy_order_id)
                return False, second_buy_price

    def set_sell_order(self, first_buy_price, second_buy_price):
        """Set final sell order"""
        average_price = np.round((first_buy_price + second_buy_price) / 2, 2)

        logger.info(
            f"Buy order filled, open position: {self.order_size*2} contract(s) at {average_price}"
        )

        sell_price = self.calculate_order_price(
            price=average_price, margin=self.profit_margin, positive=True
        )
        order_id = limit_order(
            self.client, self.symbol, -2 * self.order_size, sell_price
        )
        logger.info(
            f"Sell order placed: {-2 * self.order_size} contract(s) at {sell_price}"
        )

        while True:
            _, sell_price_reached, _ = WebsocketPrice(
                client=self.client,
                symbol=self.symbol,
                sell_price=sell_price,
            ).start_websocket()

            # LOG TO DATABASE
            if sell_price_reached:
                sell_price = get_filled_price(self.client, order_id)
                return sell_price

    def calculate_order_price(self, price, margin, positive):
        """Calculate price based on positive or negative margin"""
        if positive:
            return np.round(price + (margin * price), 1)
        else:
            return np.round(price - (margin * price), 1)

    def get_profit(self):
        """Get profit"""
        sold_price = None
        sold_quantity = None
        profit_made = None
        logger.info(f"Sell order filled: {sold_quantity} contract(s) at {sold_price}")
        logger.success(f"Done trading, profit made: {profit_made} BTC (... euro)")
